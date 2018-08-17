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
from volttron.platform.vip.agent import Agent, Core
from volttron.platform.agent import utils

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
    price = config.get('price')
    building_name = config.get("building", "")
    incoming_price_topic = config.get("price_topic")
    base_demand_topic = "/".join([building_name, "demand"])

    verbose_logging = config.get('verbose_logging', True)
    return MeterAgent(agent_name, market_name, price, verbose_logging, incoming_price_topic, base_demand_topic,
                      **kwargs)


class MeterAgent(MarketAgent):
    """
    The SampleElectricMeterAgent serves as a sample of an electric meter that
    sells electricity for a single building at a fixed price.
    """

    def __init__(self, agent_name, market_name, price, verbose_logging, incoming_price_topic, base_demand_topic,
                 **kwargs):
        super(MeterAgent, self).__init__(verbose_logging, **kwargs)
        self.market_name = market_name
        self.price = price
        self.price_min = 10.
        self.price_max = 100.
        self.infinity = 1000000
        self.num = 0
        self.incoming_price_topic = incoming_price_topic
        self.base_demand_topic = base_demand_topic
        self.agent_name = agent_name
        if price is not None:
            self.join_market(self.market_name, SELLER, None, None,
                             self.aggregate_callback, self.price_callback, self.error_callback)
        else:
            self.join_market(self.market_name, SELLER, None, self.offer_callback,
                             None, self.price_callback, self.error_callback)

    @Core.receiver('onstart')
    def setup(self, sender, **kwargs):
        """
        Set up subscriptions for demand limiting case.
        :param sender:
        :param kwargs:
        :return:
        """
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=self.incoming_price_topic,
                                  callback=self.update_price)

    def update_price(self, peer, sender, bus, topic, headers, message):
        _log.debug("{} - received new price for next control period.  price: {}".format(message))
        self.price = message
        curve = self.create_supply_curve()
        success, message = self.make_offer(self.market_name, SELLER, curve)
        _log.debug("{} - result of make offer: {} - message: {}".format(self.agent_name, success, message))

    def aggregate_callback(self, timestamp, market_name, buyer_seller, aggregate_demand):
        if buyer_seller == BUYER and market_name == self.market_name:
            _log.debug(
                "{} - received aggregate electric demand.  curve: {}".format(self.agent_name, aggregate_demand.points))
            electric_demand = aggregate_demand.points
            for i in xrange(len(electric_demand)):
                demand_topic = self.base_demand_topic + str(i)
                message = electric_demand[i].tuppleize()
                headers = {}
                self.vip.pubsub.publish(peer='pubsub', topic=demand_topic, message=message, headers=headers)

    def reservation_callback(self, timestamp, market_name, buyer_seller):
        pass

    def offer_callback(self, timestamp, market_name, buyer_seller):
        curve = self.create_supply_curve()
        success, message = self.make_offer(self.market_name, SELLER, curve)

    def create_supply_curve(self):
        supply_curve = PolyLine()
        price = self.price if self.price is not None else 0.0
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