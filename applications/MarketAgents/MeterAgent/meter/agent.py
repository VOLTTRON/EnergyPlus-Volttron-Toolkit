# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2016, Battelle Memorial Institute
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
# official policies, either expressed or implied, of the FreeBSD
# Project.
#
# This material was prepared as an account of work sponsored by an
# agency of the United States Government.  Neither the United States
# Government nor the United States Department of Energy, nor Battelle,
# nor any of their employees, nor any jurisdiction or organization that
# has cooperated in the development of these materials, makes any
# warranty, express or implied, or assumes any legal liability or
# responsibility for the accuracy, completeness, or usefulness or any
# information, apparatus, product, software, or process disclosed, or
# represents that its use would not infringe privately owned rights.
#
# Reference herein to any specific commercial product, process, or
# service by trade name, trademark, manufacturer, or otherwise does not
# necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors
# expressed herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY
# operated by BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830

# }}}

import sys
import logging
from collections import defaultdict
from sympy import symbols
from sympy.parsing.sympy_parser import parse_expr
from volttron.platform.vip.agent import Agent, Core
from volttron.platform.agent import utils
from volttron.platform.agent.math_utils import mean
from volttron.platform.messaging import topics
from volttron.platform.agent.base_market_agent import MarketAgent
from volttron.platform.agent.base_market_agent.poly_line import PolyLine
from volttron.platform.agent.base_market_agent.point import Point
from volttron.platform.agent.base_market_agent.buy_sell import SELLER
from volttron.platform.agent.base_market_agent.buy_sell import BUYER

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def meter_agent(config_path, **kwargs):
    """Parses the Electric Meter Agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: Market Service Agent
    :rtype: MarketServiceAgent
    """
    _log.debug("Starting MeterAgent")
    try:
        config = utils.load_config(config_path)
    except StandardError:
        config = {}

    if not config:
        _log.info("Using defaults for starting configuration.")
    agent_name = config.get("agent_name", "meter")
    market_name = config.get('market_name', 'electric')
    price = config.get('price', 55)
    price_file = config.get('price_file', None)
    if price_file is not None:
        f=open(price_file,'r')
        prices = f.readlines()
        f.close()
    else:
        prices = None
 
    demand_limit = config.get('demand_limit', False)
    demand_limit_threshold = config.get("demand_limit_threshold", None)
    verbose_logging = config.get('verbose_logging', True)
    building_topic = topics.DEVICES_VALUE(campus=config.get("campus", ""),
                                          building=config.get("building", ""),
                                          unit=None,
                                          path="",
                                          point="all")
    devices = config.get("devices")
    return MeterAgent(agent_name, market_name, price, prices,verbose_logging, demand_limit, demand_limit_threshold, building_topic, devices, **kwargs)


class MeterAgent(MarketAgent):
    """
    The SampleElectricMeterAgent serves as a sample of an electric meter that
    sells electricity for a single building at a fixed price.
    """

    def __init__(self, agent_name, market_name, price, prices,verbose_logging, demand_limit, demand_limit_threshold, building_topic, devices, **kwargs):
        super(MeterAgent, self).__init__(verbose_logging, **kwargs)
        self.market_name = market_name
        self.price = price
        self.prices = prices
        self.price_index=0
        self.price_min = 10.
        self.price_max = 100.
        self.infinity = 1000000
        self.num = 0
        self.power_aggregation = []
        self.current_power = None
        self.demand_limit = demand_limit
        self.demand_limit_threshold = demand_limit_threshold
        self.want_reservation = False
        self.demand_aggregation_o = {}
        self.demand_aggregation_master = {}
        self.demand_aggregation_working = {}
        self.agent_name = agent_name
        self.join_market(self.market_name, SELLER, self.reservation_callback, None,
                         self.aggregate_callback, self.price_callback, self.error_callback)
        self.building_topic = building_topic
        self.devices = devices
        self.file='/home/vuser/volttron/eplus/tccpower.csv'
        f=open(self.file,'w')
        f.close()

    @Core.receiver('onstart')
    def setup(self, sender, **kwargs):
        """
        Set up subscriptions for demand limiting case.
        :param sender:
        :param kwargs:
        :return:
        """
        if 1:
            for device, points in self.devices.items():
                device_topic = self.building_topic(unit=device)
                _log.debug('Subscribing to {}'.format(device_topic))
                self.demand_aggregation_master[device_topic] = points
                self.vip.pubsub.subscribe(peer='pubsub',
                                          prefix=device_topic,
                                          callback=self.aggregate_power)
            self.demand_aggregation_working = self.demand_aggregation_master.copy()
            _log.debug('Points are  {}'.format(self.demand_aggregation_working))

    def aggregate_callback(self, timestamp, market_name, buyer_seller, aggregate_demand):
        if buyer_seller == BUYER and market_name == self.market_name:
            _log.debug("{}: at ts {} min of aggregate curve : {}".format(self.agent_name,
                                                                         timestamp,
                                                                         aggregate_demand.points[0]))
            _log.debug("{}: at ts {} max of aggregate curve : {}".format(self.agent_name,
                                                                         timestamp,
                                                                         aggregate_demand.points[len(aggregate_demand.points) - 1]))
            if self.want_reservation:
                curve = self.create_supply_curve()
                _log.debug("{}: offer for {} as {} at {} - Curve: {}".format(self.agent_name,
                                                                             market_name,
                                                                             SELLER,
                                                                             timestamp,
                                                                             curve.points[0]))
                success, message = self.make_offer(market_name, SELLER, curve)
                _log.debug("{}: offer has {} - Message: {}".format(self.agent_name, success, message))
            else:
                _log.debug("{}: reservation not wanted for {} as {} at {}".format(self.agent_name,
                                                                                  market_name,
                                                                                  buyer_seller,
                                                                                  timestamp))

    def conversion_handler(self, conversion, point, data):
        expr = parse_expr(conversion)
        sym = symbols(point)
        point_list = [(point, data[point])]
        return float(expr.subs(point_list))

    def aggregate_power(self, peer, sender, bus, topic, headers, message):
        """
        Power measurements for devices are aggregated.
        :param peer:
        :param sender:
        :param bus:
        :param topic:
        :param headers:
        :param message:
        :return:
        """
        _log.debug("{}: received topic for power aggregation: {}".format(self.agent_name,
                                                                         topic))
        data = message[0]
        try:
            #_log.debug("Power check 2: {}".format(self.demand_aggregation_working))
            #_log.debug("Power check 4: {}".format(self.demand_aggregation_master))
            current_points = self.demand_aggregation_working.pop(topic)
        except KeyError:
            #_log.debug("Received duplicate topic for aggregation: {}".format(topic))
            if self.power_aggregation:
                self.current_power = sum(self.power_aggregation)
            else:
                self.current_power = 0.
            self.demand_aggregation_working = self.demand_aggregation_master.copy()
         
        conversion = current_points.get("conversion")
        for point in current_points.get("points", []):
            if conversion is not None:
                value = float(self.conversion_handler(conversion, point, data))
            else:
                value = float(data[point])
            self.power_aggregation.append(value)
        #_log.debug("Power aggregation: {}".format( self.power_aggregation))
        #_log.debug("Power check: {}".format(self.demand_aggregation_working))
        if not self.demand_aggregation_working:
            if self.power_aggregation:
                self.current_power = sum(self.power_aggregation)

            else:
                self.current_power = 0.
            self.power_aggregation = []
            self.demand_aggregation_working = self.demand_aggregation_master.copy()
            _log.debug("Power check: {}".format(self.demand_aggregation_working))
            f=open(self.file,'a')
            f.writelines(str(self.current_power)+'\n')
            f.close()

        _log.debug("{}: updating power aggregation: {}".format(self.agent_name,
                                                           self.current_power))
  

    def reservation_callback(self, timestamp, market_name, buyer_seller):
        if self.demand_limit and self.current_power is not None:
            if self.current_power > self.demand_limit_threshold:
            #if self.current_power > 600:
                _log.debug("current power".format())
                self.want_reservation = True

            else:
                self.want_reservation = False
        else:
            self.want_reservation = True
        _log.debug("{}: wants reservation is {} for {} as {} at {}".format(self.agent_name,
                                                                           self.want_reservation,
                                                                           market_name,
                                                                           buyer_seller,
                                                                           timestamp))
        return self.want_reservation

    def create_supply_curve(self):
        supply_curve = PolyLine()

        if self.demand_limit:
            min_price = self.price_min
            max_price = self.price_max
            supply_curve.add(Point(price=min_price, quantity=self.demand_limit_threshold))
            supply_curve.add(Point(price=max_price, quantity=self.demand_limit_threshold))
        else:
            if self.prices is None:
                price = self.price
            elif self.price_index < len(self.prices) - 1:
                price = float(self.prices[self.price_index])
                self.price_index = self.price_index + 1
            else:
                self.price_index = 0
                price = float(self.prices[self.price_index])

            supply_curve.add(Point(price=price, quantity=self.infinity))
            supply_curve.add(Point(price=price, quantity=0.0))
       
        return supply_curve

    def price_callback(self, timestamp, market_name, buyer_seller, price, quantity):
        _log.debug("{}: cleared price ({}, {}) for {} as {} at {}".format(self.agent_name,
                                                                          price,
                                                                          quantity,
                                                                          market_name,
                                                                          buyer_seller,
                                                                          timestamp))

    def error_callback(self, timestamp, market_name, buyer_seller, error_code, error_message, aux):
        _log.debug("{}: error for {} as {} at {} - Message: {}".format(self.agent_name,
                                                                       market_name,
                                                                       buyer_seller,
                                                                       timestamp,
                                                                       error_message))


def main():
    """Main method called to start the agent."""
    utils.vip_main(meter_agent, version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass