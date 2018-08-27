# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:

# Copyright (c) 2017, Battelle Memorial Institute
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
from pnnl.models.grayboxzone import GrayBoxZone
import numpy as np
from gevent import sleep
import os

_log = logging.getLogger(__name__)
utils.setup_logging()
__version__ = "0.1"


def vav_agent(config_path, **kwargs):
    """Parses the Electric Meter Agent configuration and returns an instance of
    the agent created using that configuation.

    :param config_path: Path to a configuation file.

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

    market_name = config.get('market_name')
#    x0 = config.get('x0', 0)
#    x1 = config.get('x1', 0)
#    x2 = config.get('x2', 0)
#    x3 = config.get('x3', 0)
#    x4 = config.get('x4', 0)
#    c0 = config.get('c0', 0)
#    c1 = config.get('c1', 0)
#    c2 = config.get('c2', 0)
#    c3 = config.get('c3', 0)
#    c4 = config.get('c4', 0)
    c = config.get('c', 4000000)
    r = config.get('r', 0.002)
    shgc = config.get('shgc', 0.5)

    tMinAdj = config.get('tMin', 0)
    tMaxAdj = config.get('tMax', 0)
    mDotMin = config.get('mDotMin', 0)
    mDotMax = config.get('mDotMax', 0)
    p_min = config.get('minimum_price', 5.0)
    p_max = config.get('maximum_price', 50.0)

    sim_flag = config.get('sim_flag', False)
    tIn = config.get('tIn', 0)
    nonResponsive = config.get('nonResponsive', False)
    agent_name = config.get('agent_name')
    actuator = config.get('actuator', 'platform.actuator')
    mode = config.get('mode')
    device_points = config.get("device_points")
    parent_device_points = config.get("parent_device_points")
    setpoint = config.get('setpoint')
    activate_topic = "/".join([config.get("building", agent_name), "actuate"])

    setpoint_mode = config.get("setpoint_mode", 0)
    modelName= config.get("modelName")
    parent_device_topic = topics.DEVICES_VALUE(campus=config.get("campus", ""),
                                               building=config.get("building", ""),
                                               unit=config.get("parent_device", ""),
                                               path="",
                                               point="all")

    device_topic = topics.DEVICES_VALUE(campus=config.get("campus", ""),
                                        building=config.get("building", ""),
                                        unit=config.get("parent_device", ""),
                                        path=config.get("device", ""),
                                        point="all")

    base_rpc_path = topics.RPC_DEVICE_PATH(campus=config.get("campus", ""),
                                           building=config.get("building", ""),
                                           unit=config.get("parent_device", ""),
                                           path=config.get("device", ""),
                                           point=setpoint)

    verbose_logging = config.get('verbose_logging', True)
    return VAVAgent(market_name, agent_name, tMinAdj, tMaxAdj, mDotMin, mDotMax,
                    tIn, nonResponsive, verbose_logging, device_topic,
                    device_points, parent_device_topic, parent_device_points,
                    base_rpc_path, activate_topic, actuator, mode, setpoint_mode,
                    sim_flag, modelName, c, r, shgc, p_min, p_max, **kwargs)


def temp_f2c(rawtemp):
    return (rawtemp - 32) / 9 * 5


def temp_c2f(rawtemp):
    return 1.8 * rawtemp + 32.0


def flow_cfm2cms(rawflowrate):
    return rawflowrate * 0.00043 * 1.2


def clamp(value, x1, x2):
    min_value = min(x1, x2)
    max_value = max(x1, x2)
    return min(max(value, min_value), max_value)


def ease(target, current, limit):
    return current - np.sign(current - target) * min(abs(current - target), abs(limit))


class VAVAgent(MarketAgent, GrayBoxZone):
    """
    The SampleElectricMeterAgent serves as a sample of an electric meter that
    sells electricity for a single building at a fixed price.
    """

    def __init__(self, market_name, agent_name,
                 tMinAdj, tMaxAdj, mDotMin, mDotMax, tIn, nonResponsive, verbose_logging,
                 device_topic, device_points, parent_device_topic, parent_device_points,
                 base_rpc_path, activate_topic, actuator, mode, setpoint_mode, sim_flag, modelName, c, r, shgc,
                 p_min, p_max, **kwargs):
        super(VAVAgent, self).__init__(verbose_logging, **kwargs)
        self.market_name = market_name
        self.agent_name = agent_name
        self.hvac_avail = 0
        self.tOut = 32
        self.zone_airflow = 10
        self.zone_datemp = 12.78
        self.tDel = 0.25
        self.t_ease = 0.25
        self.tNomAdj = tIn
        self.temp_stpt = self.tNomAdj
        self.tIn = self.tNomAdj
        self.p_clear = None
        self.q_clear = None
        self.demand_curve = None
        self.tMinAdj = tMinAdj
        self.tMaxAdj = tMaxAdj
        self.mDotMin = mDotMin
        self.mDotMax = mDotMax
        self.qHvacSens = self.zone_airflow * 1006. * (self.zone_datemp - self.tIn)
        self.qMin = min(0, self.mDotMin * 1006. * (self.zone_datemp - self.tIn))
        self.qMax = min(0, self.mDotMax * 1006. * (self.zone_datemp - self.tIn))
        self.model = None

        self.default = None
        self.actuator = actuator
        self.mode = mode
        self.nonResponsive = nonResponsive
        self.sim_flag = sim_flag
        self.c = c
        self.r = r
        self.shgc = shgc
        self.modelName = os.path.expanduser(modelName)
        
        if self.sim_flag:
            self.actuate_enabled = 1
        else:
            self.actuate_enabled = 0

        self.setpoint_offset = 0.0

        if isinstance(setpoint_mode, dict):
            self.mode_status = True
            self.status_point = setpoint_mode["point"]
            self.setpoint_mode_true_offset = setpoint_mode["true_value"]
            self.setpoint_mode_false_offset = setpoint_mode["false_value"]
        else:
            self.mode_status = False

        self.device_topic = device_topic
        self.parent_device_topic = parent_device_topic
        self.actuator_topic = base_rpc_path
        self.activate_topic = activate_topic
        # Parent device point mapping (AHU level points)
        self.supply_fan_status = parent_device_points.get("supply_fan_status", "SupplyFanStatus")
        self.outdoor_air_temperature = parent_device_points.get("outdoor_air_temperature", "OutdoorAirTemperature")

        # Device point mapping (VAV level points)
        self.zone_datemp_name = device_points.get("zone_dat", "ZoneDischargeAirTemperature")
        self.zone_airflow_name = device_points.get("zone_airflow", "ZoneAirFlow")
        self.zone_temp_name = device_points.get("zone_temperature", "ZoneTemperature")
        self.p_min = p_min
        self.p_max = p_max
        self.join_market(self.market_name, BUYER, None, self.offer_callback, None, self.price_callback, self.error_callback)

    @Core.receiver('onstart')
    def setup(self, sender, **kwargs):
        _log.debug('Subscribing to device' + self.device_topic)
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=self.device_topic,
                                  callback=self.update_zone_state,
                                  all_platforms=True)
        _log.debug('Subscribing to parent' + self.parent_device_topic)
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=self.parent_device_topic,
                                  callback=self.update_state,
                                  all_platforms=True)
        _log.debug('Subscribing to ' + self.activate_topic)
        self.vip.pubsub.subscribe(peer='pubsub',
                                  prefix=self.activate_topic,
                                  callback=self.update_actuation_state,
                                  all_platforms=True)

    @Core.receiver("onstop")
    def shutdown(self, sender, **kwargs):
        if self.actuate_enabled:
            if self.mode == 1:
                self.vip.rpc.call(self.actuator, 'set_point', self.agent_name, self.actuator_topic, None, external_platform='3820A').get(timeout=10)
            else:
                self.vip.rpc.call(self.actuator, 'set_point', self.agent_name, self.actuator_topic, self.default, external_platform='3820A').get(timeout=10)

    def offer_callback(self, timestamp, market_name, buyer_seller):
        result, message = self.make_offer(market_name, buyer_seller, self.create_demand_curve())
        _log.debug("{}: demand max {} and min {} at {}".format(self.agent_name,
                                                               -self.demand_curve.x(10),
                                                               -self.demand_curve.x(100),
                                                               timestamp))
        _log.debug("{}: result of the make offer {} at {}".format(self.agent_name,
                                                                  result,
                                                                  timestamp))
        if not result:
            _log.debug("{}: maintain old set point {}".format(self.agent_name,
                                                              self.temp_stpt))
            if self.sim_flag:
                self.actuate_setpoint()

    def create_demand_curve(self):
        self.demand_curve = PolyLine()
        qMin = abs(self.get_q_min())
        sleep(1)
        qMax = abs(self.get_q_max())
        if self.hvac_avail:
            self.demand_curve.add(Point(price=max(self.p_min, self.p_max), quantity=min(qMin, qMax)))
            self.demand_curve.add(Point(price=min(self.p_min, self.p_max), quantity=max(qMin, qMax)))
        else:
            self.demand_curve.add(Point(price=max(self.p_min, self.p_max), quantity=0.1))
            self.demand_curve.add(Point(price=min(self.p_min, self.p_max), quantity=0.1))
        if self.hvac_avail:
            _log.debug("{} - Tout {} - Tin {} - q {}".format(self.agent_name, self.tOut, self.tIn, self.qHvacSens))
        return self.demand_curve

    def update_zone_state(self, peer, sender, bus, topic, headers, message):
        """
        Subscribe to device data from message bus
        :param peer:
        :param sender:
        :param bus:
        :param topic:
        :param headers:
        :param message:
        :return:
        """
        _log.debug('{} received zone info'.format(self.agent_name))
        info = message[0]

        if not self.sim_flag:
            self.zone_datemp = temp_f2c(info[self.zone_datemp_name])
            self.zone_airflow = flow_cfm2cms(info[self.zone_airflow_name])
            self.tIn = temp_f2c(info[self.zone_temp_name])
        else:
            self.zone_datemp = info[self.zone_datemp_name]
            self.zone_airflow = info[self.zone_airflow_name]
            self.tIn = info[self.zone_temp_name]

        if self.mode_status:
            if info[self.status_point]:
                self.setpoint_offset = self.setpoint_mode_true_offset
                _log.debug("Setpoint offset: {}".format(self.setpoint_offset))
            else:
                self.setpoint_offset = self.setpoint_mode_false_offset
                _log.debug("Setpoint offset: {}".format(self.setpoint_offset))

        self.qHvacSens = self.zone_airflow * 1006. * (self.zone_datemp - self.tIn)
        self.qMin = min(0, self.mDotMin * 1006. * (self.zone_datemp - self.tIn))
        self.qMax = min(0, self.mDotMax * 1006. * (self.zone_datemp - self.tIn))

    def update_state(self, peer, sender, bus, topic, headers, message):
        """
        Subscribe to device data from message bus.
        :param peer:
        :param sender:
        :param bus:
        :param topic:
        :param headers:
        :param message:
        :return:
        """
        _log.debug('{} received one parent_device '
                   'information on: {}'.format(self.agent_name, topic))
        info = message[0]
        if not self.sim_flag:
            self.tOut = temp_f2c(info[self.outdoor_air_temperature])
        else:
            self.tOut = info[self.outdoor_air_temperature]
        self.hvac_avail = info[self.supply_fan_status]

    def update_actuation_state(self, peer, sender, bus, topic, headers, message):
        """
        Subscribe to device data from message bus.
        :param peer:
        :param sender:
        :param bus:
        :param topic:
        :param headers:
        :param message:
        :return:
        """
        _log.debug('{} received update actuation.'.format(self.agent_name))
        _log.debug("Current actuation state: {} - '"
                   "update actuation state: {}".format(self.actuate_enabled, message))
        if not self.actuate_enabled and message:
            self.default = self.vip.rpc.call(self.actuator, 'get_point', self.actuator_topic, external_platform='3820A').get(timeout=10)
        self.actuate_enabled = message
        if not self.actuate_enabled:
            if self.mode == 1:
                self.vip.rpc.call(self.actuator, 'set_point', self.agent_name, self.actuator_topic, None, external_platform='3820A').get(timeout=10)
            else:
                if self.default is not None:
                    self.vip.rpc.call(self.actuator, 'set_point', self.agent_name, self.actuator_topic, self.default, external_platform='3820A').get(timeout=10)

    def update_setpoint(self):
        if self.p_clear is not None and not self.nonResponsive and self.hvac_avail:
            self.q_clear = clamp(-self.demand_curve.x(self.p_clear), self.qMax, self.qMin)
            self.temp_stpt = clamp(self.getT(self.q_clear), self.tMinAdj, self.tMaxAdj)
        else:
            self.temp_stpt = clamp(ease(self.tNomAdj, self.temp_stpt, self.t_ease), self.tMinAdj, self.tMaxAdj)
            self.q_clear = clamp(self.getQ(self.temp_stpt), self.qMax, self.qMin)
        if self.q_clear is None:
            self.q_clear = 0.

    def get_q_min(self):
        t = self.tMaxAdj
        q = clamp(self.getQ(t), self.qMax, self.qMin)
        return q

    def get_q_max(self):
        t = self.tMinAdj
        q = clamp(self.getQ(t), self.qMax, self.qMin)
        return q

    def price_callback(self, timestamp, market_name, buyer_seller, price, quantity):
        _log.debug("{} - price of {} for market: {}".format(self.agent_name, price, market_name))
        self.p_clear = price
        if not self.qMax and not self.qMin and not self.sim_flag:
            self.update_actuation_state(None, None, None, None, None, 0)
            return
        if self.p_clear is not None:
            self.update_setpoint()
            _log.debug("New set point is {}".format(self.temp_stpt))
            self.actuate_setpoint()

    def error_callback(self, timestamp, market_name, buyer_seller, error_code, error_message, aux):
        _log.debug("{} - error for Market: {} {}, Message: {}".format(self.agent_name,
                                                                      market_name,
                                                                      buyer_seller, aux))
        if self.actuate_enabled:
            if market_name == "electric":
                if aux.get('SQx, DQn', 0) == -1 or aux.get('SPn, DPx', 0) == 1:
                    self.temp_stpt = self.tMaxAdj
                    self.actuate_setpoint()
                    return
                if aux.get('SPx, DPn', 0) == -1:
                    self.temp_stpt = self.tMinAdj
                    self.actuate_setpoint()
                    return
            if self.sim_flag:
                self.temp_stpt = self.tNomAdj
                self.actuate_setpoint()

    def actuate_setpoint(self):
        if not self.sim_flag:
             temp_stpt = temp_c2f(self.temp_stpt) - self.setpoint_offset
        else:
            temp_stpt = self.temp_stpt - self.setpoint_offset
        if self.actuate_enabled:
            _log.debug("{} - setting {} with value {}".format(self.agent_name, self.actuator_topic, temp_stpt))
            self.vip.rpc.call(self.actuator, 'set_point', self.agent_name, self.actuator_topic, temp_stpt, external_platform='3820A').get(timeout=10)


def main():
    """Main method called to start the agent."""
    utils.vip_main(vav_agent, version=__version__)


if __name__ == '__main__':
    # Entry point for script
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
