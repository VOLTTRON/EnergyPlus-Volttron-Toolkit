# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2018, Battelle Memorial Institute
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
from volttron.platform.agent import utils
from volttron.platform.messaging import topics
from volttron.platform.vip.agent import Agent, Core
from volttron.platform.agent.base_market_agent import MarketAgent
from volttron.platform.agent.base_market_agent.poly_line import PolyLine
from volttron.platform.agent.base_market_agent.point import Point
from volttron.platform.agent.base_market_agent.buy_sell import BUYER
from volttron.platform.agent.base_market_agent.buy_sell import SELLER
from pnnl.models.ahuchiller import AhuChiller

# from pnnl.models.firstorderzone import FirstOrderZone

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def ahu_agent(config_path, **kwargs):
    """Parses the ahu_agent configuration and returns an instance of
    the agent created using that configuration.

    :param config_path: Path to a configuration file.

    :type config_path: str
    :returns: Market Service Agent
    :rtype: MarketServiceAgent
    """
    try:
        config = utils.load_config(config_path)
    except StandardError:
        config = {}

    if not config:
        _log.info("Using defaults for starting configuration.")
    air_market_name = config.get('air_market_name', 'air')
    electric_market_name = config.get('electric_market_name', 'electric')
    agent_name = config.get('agent_name')
    c0 = config.get('c0')
    c1 = config.get('c1')
    c2 = config.get('c2')
    c3 = config.get('c3')
    COP = config.get('COP')
    sim_flag = config.get('sim_flag', False)
    device_points = config.get("device_points")
    device_topic = topics.DEVICES_VALUE(campus=config.get("campus", ""),
                                        building=config.get("building", ""),
                                        unit=config.get("device", ""),
                                        path="",
                                        point="all")
    verbose_logging = config.get('verbose_logging', True)
    return AHUAgent(air_market_name, electric_market_name, agent_name,
                    device_topic, c0, c1, c2, c3, COP, verbose_logging,
                    device_points, sim_flag, **kwargs)


def temp_f2c(temp):
    return (temp - 32) / 9 * 5


def flow_cfm2cms(flowrate):
    return flowrate * 0.00043 * 1.2



class AHUAgent(MarketAgent, AhuChiller):
    """
    The SampleElectricMeterAgent serves as a sample of an electric meter that
    sells electricity for a single building at a fixed price.
    """

    def __init__(self, air_market_name, electric_market_name, agent_name, device_topic, c0, c1, c2, c3, COP,
                 verbose_logging, device_points, sim_flag, **kwargs):
        super(AHUAgent, self).__init__(verbose_logging, **kwargs)

        self.air_market_name = air_market_name
        self.electric_market_name = electric_market_name
        self.agent_name = agent_name
        self.device_topic = device_topic

        # Model parameters
        self.c0 = c0
        self.c1 = c1
        self.c2 = c2
        self.c3 = c3
        self.COP = COP
        self.hvacAvail = 0
        self.cpAir = 1006.
        self.c4 = 0.
        self.c5 = 0.

        self.load = None
        self.sim_flag = sim_flag
        self.join_market(self.air_market_name, SELLER, None, None,
                         self.air_aggregate_callback, self.air_price_callback, self.error_callback)

        self.join_market(self.electric_market_name, BUYER, None, None,
                         None, self.electric_price_callback, self.el_error_callback)

        # Point names
        self.rat_name = device_points.get("return_air_temperature")
        self.mat_name = device_points.get("mixed_air_temperature")
        self.sat_name = device_points.get("supply_air_temperature")
        self.saf_name = device_points.get("supply_air_flow")
        self.staticPressure = 0.
        # Initial value of measurement data
        self.tAirReturn = 20.
        self.tAirSupply = 10.
        self.tAirMixed = 20.
        self.mDotAir = 0.
        self.pClear = None

        self.p_clear = None
        self.buy_bid_curve = None
        self.old_price = None
        self.old_quantity = None

    @Core.receiver("onstart")
    def setup(self, sender, **kwargs):
        _log.debug("Subscribing topic: {}".format(self.device_topic))
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=self.device_topic,
                                  callback=self.update_state,
                                  all_platforms=True)

    def air_aggregate_callback(self, timestamp, market_name, buyer_seller, aggregate_air_demand):
        if buyer_seller == BUYER:
            _log.debug("{} - Received aggregated {} curve".format(self.agent_name, market_name))
            electric_demand = self.create_electric_demand_curve(aggregate_air_demand)
            success, message = self.make_offer(self.electric_market_name, BUYER, electric_demand)
            if success:
                _log.debug("{}: make a offer for {}".format(self.agent_name, market_name))
            else:
                _log.debug("{}: offer for the {} was rejected".format(self.agent_name, market_name))
                supply_curve = PolyLine()
                supply_curve.add(Point(price=10, quantity=0.001))
                supply_curve.add(Point(price=10, quantity=0.001))
                success, message = self.make_offer(self.air_market_name, SELLER, supply_curve)
                _log.debug("{}: offer for {} was accepted: {}".format(self.agent_name,
                                                                      self.air_market_name,
                                                                      success))

    def electric_price_callback(self, timestamp, market_name, buyer_seller, price, quantity):
        _log.debug("{}: cleared price {} for {} at timestep {}".format(self.agent_name, price,
                                                                       market_name, timestamp))
        self.report_cleared_price(buyer_seller, market_name, price, quantity, timestamp)
        if price is not None:
            self.make_air_market_offer(price)
            _log.debug("{}: agent making offer on air market".format(self.agent_name))
        else:
            supply_curve = PolyLine()
            supply_curve.add(Point(price=10, quantity=0.1))
            supply_curve.add(Point(price=10, quantity=0.1))
            success, message = self.make_offer(self.air_market_name, SELLER, supply_curve)
            if success:
                _log.debug("price_check: just use the place holder")

    def air_price_callback(self, timestamp, market_name, buyer_seller, price, quantity):
        self.report_cleared_price(buyer_seller, market_name, price, quantity, timestamp)

    def make_air_market_offer(self, price):
        air_supply_curve = self.create_air_supply_curve(price)
        success, message = self.make_offer(self.air_market_name, SELLER, air_supply_curve)
        if success:
            _log.debug("{}: make offer for Market: {} {} Curve: {}".format(self.agent_name,
                                                                           self.air_market_name,
                                                                           SELLER,
                                                                           air_supply_curve.points))

    def report_cleared_price(self, buyer_seller, market_name, price, quantity, timestamp):
        _log.debug("{}: ts - {}, Market - {} as {}, Price - {} Quantity - {}".format(self.agent_name,
                                                                                     timestamp,
                                                                                     market_name,
                                                                                     buyer_seller,
                                                                                     price,
                                                                                     quantity))

    def error_callback(self, timestamp, market_name, buyer_seller, error_code, error_message, aux):
        _log.debug("{}: error for market {} as {} at {}, message: {}".format(self.agent_name,
                                                                             market_name,
                                                                             buyer_seller,
                                                                             timestamp,
                                                                             error_message))

    def el_error_callback(self, timestamp, market_name, buyer_seller, error_code, error_message, aux):
        _log.debug("{}: error for market {} as {} at {}, message: {}".format(self.agent_name,
                                                                             market_name,
                                                                             buyer_seller,
                                                                             timestamp,
                                                                             error_message))

    def create_air_supply_curve(self, electric_price):
        _log.debug("{}: clear air price {}".format(self.agent_name, electric_price))
        air_supply_curve = PolyLine()
        price = electric_price
        min_quantity = self.load[0]
        max_quantity = self.load[-1]
        air_supply_curve.add(Point(price=price, quantity=min_quantity))
        air_supply_curve.add(Point(price=price, quantity=max_quantity))

        return air_supply_curve

    def create_electric_demand_curve(self, aggregate_air_demand):
        electric_demand_curve = PolyLine()
        self.load = []
        for point in aggregate_air_demand.points:
            electric_demand_curve.add(Point(price=point.y, quantity=self.calcTotalLoad(point.x)))
            self.load.append(point.x)
        _log.debug("{}: aggregated curve : {}".format(self.agent_name, electric_demand_curve.points))

        return electric_demand_curve

    def update_state(self, peer, sender, bus, topic, headers, message):
        """
        Device data to update load calculation.
        :param peer:
        :param sender:
        :param bus:
        :param topic:
        :param headers:
        :param message:
        :return:
        """
        _log.debug("{}: Received device data set".format(self.agent_name))
        info = message[0]
        if self.sim_flag:
            self.tAirMixed = temp_f2c(info[self.mat_name])
            self.tAirReturn = temp_f2c(info[self.rat_name])
            self.tAirSupply = temp_f2c(info[self.sat_name])
            self.mDotAir = flow_cfm2cms(info[self.saf_name])
        else:
            self.tAirMixed = info[self.mat_name]
            self.tAirReturn = info[self.rat_name]
            self.tAirSupply = info[self.sat_name]
            self.mDotAir = info[self.saf_name]


def main():
    """Main method called to start the agent."""
    utils.vip_main(ahu_agent, version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
