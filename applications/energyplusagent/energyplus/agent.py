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

from __future__ import absolute_import

import logging
import os
import socket
import subprocess
import sys
from datetime import datetime
from gevent import monkey, sleep


monkey.patch_socket()
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Core, RPC
from volttron.platform.pubsub.agent import SynchronizingPubSubAgent

utils.setup_logging()
log = logging.getLogger(__name__)
SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'


class EnergyPlusAgent(SynchronizingPubSubAgent):
    def __init__(self, config_path, **kwargs):
        super(EnergyPlusAgent, self).__init__(config_path, **kwargs)
        self.version = 8.4
        self.bcvtb_home = '.'
        self.model = None
        self.weather = None
        self.socketFile = None
        self.variableFile = None
        self.time = 0
        self.vers = 2
        self.flag = 0
        self.sent = None
        self.rcvd = None
        self.socket_server = None
        self.simulation = None
        self.step = None
        self.eplus_inputs = 0
        self.eplus_outputs = 0
        self.cosim_sync_counter = 0
        if not self.config:
            self.exit('No configuration found.')
        self.cwd = os.getcwd()

    @Core.receiver('onsetup')
    def setup(self, sender, **kwargs):
        super(EnergyPlusAgent, self).setup(sender, **kwargs)

    @Core.receiver('onstart')
    def start(self, sender, **kwargs):
        self.subscribe()
        self.clear_last_update()
        self.start_socket_server()
        self.start_simulation()

    def start_socket_server(self):
        self.socket_server = self.SocketServer()
        self.socket_server.size = self.size
        self.socket_server.on_recv = self.recv_eplus_msg
        self.socket_server.connect()
        self.core.spawn(self.socket_server.start)

    def start_simulation(self):
        if not self.model:
            self.exit('No model specified.')
        if not self.weather:
            self.exit('No weather specified.')
        model_path = self.model
        if model_path[0] == '~':
            model_path = os.path.expanduser(model_path)
        if model_path[0] != '/':
            model_path = os.path.join(self.cwd, model_path)
        weather_path = self.weather
        if weather_path[0] == '~':
            weather_path = os.path.expanduser(weather_path)
        if weather_path[0] != '/':
            weather_path = os.path.join(self.cwd, weather_path)
        model_dir = os.path.dirname(model_path)
        bcvtb_dir = self.bcvtb_home
        if bcvtb_dir[0] == '~':
            bcvtb_dir = os.path.expanduser(bcvtb_dir)
        if bcvtb_dir[0] != '/':
            bcvtb_dir = os.path.join(self.cwd, bcvtb_dir)
        log.debug('Working in %r', model_dir)
        self.write_port_file(os.path.join(model_dir, 'socket.cfg'))
        self.write_variable_file(os.path.join(model_dir, 'variables.cfg'))
        if self.version >= 8.4:
            cmd_str = "cd %s; export BCVTB_HOME=%s; energyplus -w %s -r %s" % (
            model_dir, bcvtb_dir, weather_path, model_path)
        else:
            cmd_str = "export BCVTB_HOME=%s; runenergyplus %s %s" % (bcvtb_dir, model_path, weather_path)
        log.debug('Running: %s', cmd_str)
        f = open(model_path, 'r')
        lines = f.readlines()
        f.close()
        for i in range(len(lines)):
            if lines[i].lower().find('runperiod,') != -1:
                lines[i + 2] = '    ' + str(self.startmonth) + ',                       !- Begin Month' + '\n'
                lines[i + 3] = '    ' + str(self.startday) + ',                       !- Begin Day of Month' + '\n'
                lines[i + 4] = '    ' + str(self.endmonth) + ',                      !- End Month' + '\n'
                lines[i + 5] = '    ' + str(self.endday) + ',                      !- End Day of Month' + '\n'

        for i in range(len(lines)):
            if lines[i].lower().find('timestep,') != -1 and lines[i].lower().find('update frequency') == -1:
                if lines[i].lower().find(';') != -1:
                    lines[i] = '  Timestep,' + str(self.timestep) + ';' + '\n'
                else:
                    lines[i + 1] = '  ' + str(self.timestep) + ';' + '\n'
        f = open(model_path, 'w')

        for i in range(len(lines)):
            f.writelines(lines[i])
        f.close()
        self.simulation = subprocess.Popen(cmd_str, shell=True)

    def send_eplus_msg(self):
        if self.socket_server:
            args = self.input()
            msg = '%r %r %r 0 0 %r' % (self.vers, self.flag, self.eplus_inputs, self.time)
            for obj in args.itervalues():
                if obj.get('name', None) and obj.get('type', None):
                    msg = msg + ' ' + str(obj.get('value'))
            self.sent = msg + '\n'
            log.info('Sending message to EnergyPlus: ' + msg)
            self.socket_server.send(self.sent)

    def recv_eplus_msg(self, msg):
        self.rcvd = msg
        self.parse_eplus_msg(msg)
        if self.sim_flag != '1':
            self.publish_all_outputs()
        if self.cosimulation_sync:
            self.check_advance()

    def check_advance(self):
        timestep = int(60/self.timestep)
        self.cosim_sync_counter += timestep
        if self.cosim_sync_counter < self.co_sim_timestep:
            self.advance_simulation(None, None, None, None, None, None)
        else:
            self.cosim_sync_counter = 0
        return

    def parse_eplus_msg(self, msg):
        msg = msg.rstrip()
        log.info('Received message from EnergyPlus: ' + msg)
        arry = msg.split()
        slot = 6
        self.sim_flag = arry[1]
        output = self.output()
        input = self.input()
        if self.sim_flag != '0':
            if self.sim_flag == '1':
                self.exit('Simulation reached end: ' + self.sim_flag)
            elif self.sim_flag == '-1':
                self.exit('Simulation stopped with unspecified error: ' + self.sim_flag)
            elif self.sim_flag == '-10':
                self.exit('Simulation stopped with error during initialization: ' + self.sim_flag)
            elif self.sim_flag == '-20':
                self.exit('Simulation stopped with error during time integration: ' + self.sim_flag)
                #            else:
                #                self.exit('Simulation stopped with error code ' + flag)
        elif ((arry[2] < self.eplus_outputs) and (len(arry) < self.eplus_outputs + 6)):
            self.exit('Got message with ' + arry[2] + ' inputs. Expecting ' + str(self.eplus_outputs) + '.')
        else:
            if float(arry[5]):
                self.time = float(arry[5])
            for key in input:
                if self.input(key, 'name') and self.input(key, 'dynamic_default'):
                    slot = 6
                    for key2 in output:
                        if self.output(key2, 'default'):
                            if self.output(key2, 'default').lower().find(self.input(key, 'name').lower()) != -1:
                                self.input(key, 'default', float(arry[slot]))
                                log.info('Reset')
                        slot += 1
            slot = 6
            for key in output:
                if self.output(key, 'name') and self.output(key, 'type'):
                    try:
                        self.output(key, 'value', float(arry[slot]))
                    except:
                        print slot
                        self.exit('Unable to convert received value to double.')
                    if self.output(key, 'type').lower().find('currentmonthv') != -1:
                        self.month = float(arry[slot])
                        print 'month ' + str(self.month)
                    elif self.output(key, 'type').lower().find('currentdayofmonthv') != -1:
                        self.day = float(arry[slot])
                        print 'day ' + str(self.day)
                    elif self.output(key, 'type').lower().find('currenthourv') != -1:
                        self.hour = float(arry[slot])
                        print 'hour ' + str(self.hour)
                    elif self.output(key, 'type').lower().find('currentminutev') != -1:
                        self.minute = float(arry[slot])
                        print 'minute ' + str(self.minute)
                    slot += 1

    def exit(self, msg):
        self.stop()
        log.error(msg)

    def stop(self):
        if self.socket_server:
            self.socket_server.stop()
            self.socket_server = None

    def write_port_file(self, path):
        fh = open(path, "w+")
        fh.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        fh.write('<BCVTB-client>\n')
        fh.write('  <ipc>\n')
        fh.write('    <socket port="%r" hostname="%s"/>\n' % (self.socket_server.port, self.socket_server.host))
        fh.write('  </ipc>\n')
        fh.write('</BCVTB-client>')
        fh.close()

    def write_variable_file(self, path):
        fh = open(path, "w+")
        fh.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        fh.write('<!DOCTYPE BCVTB-variables SYSTEM "variables.dtd">\n')
        fh.write('<BCVTB-variables>\n')
        for obj in self.output().itervalues():
            if obj.has_key('name') and obj.has_key('type'):
                self.eplus_outputs = self.eplus_outputs + 1
                fh.write('  <variable source="EnergyPlus">\n')
                fh.write('    <EnergyPlus name="%s" type="%s"/>\n' % (obj.get('name'), obj.get('type')))
                fh.write('  </variable>\n')
        for obj in self.input().itervalues():
            if obj.has_key('name') and obj.has_key('type'):
                self.eplus_inputs = self.eplus_inputs + 1
                fh.write('  <variable source="Ptolemy">\n')
                fh.write('    <EnergyPlus %s="%s"/>\n' % (obj.get('type'), obj.get('name')))
                fh.write('  </variable>\n')
        fh.write('</BCVTB-variables>\n')
        fh.close()

    @RPC.export
    def request_new_schedule(self, requester_id, task_id, priority, requests):
        """RPC method

        Requests one or more blocks on time on one or more device.
        In this agent, this does nothing!

        :param requester_id: Requester name.
        :param task_id: Task name.
        :param priority: Priority of the task. Must be either HIGH, LOW, or LOW_PREEMPT
        :param requests: A list of time slot requests

        :type requester_id: str
        :type task_id: str
        :type priority: str
        :type request: list
        :returns: Request result
        :rtype: dict

        """
        log.debug(requester_id + " requests new schedule " + task_id + " " + str(requests))
        result = {'result': SUCCESS,
                  'data': {},
                  'info': ''}
        return result

    @RPC.export
    def request_cancel_schedule(self, requester_id, task_id):
        """RPC method

        Requests the cancelation of the specified task id.
        In this agent, this does nothing!

        :param requester_id: Requester name.
        :param task_id: Task name.

        :type requester_id: str
        :type task_id: str
        :returns: Request result
        :rtype: dict

        """
        log.debug(requester_id + " canceled " + task_id)
        result = {'result': SUCCESS,
                  'data': {},
                  'info': ''}
        return result

    @RPC.export
    def get_point(self, topic, **kwargs):
        """RPC method

        Gets the value of a specific point on a device_name.
        Does not require the device_name be scheduled.

        :param topic: The topic of the point to grab in the
                      format <device_name topic>/<point name>
        :param **kwargs: These get dropped on the floor
        :type topic: str
        :returns: point value
        :rtype: any base python type

        """
        obj = self.find_best_match(topic)
        if obj is not None:  # we have an exact match to the  <device_name topic>/<point name>, so return the first value
            value = obj.get('value', None)
            if value is None:
                value = obj.get('default', None)
            return value
        return None

    @RPC.export
    def set_point(self, requester_id, topic, value, **kwargs):
        """RPC method

        Sets the value of a specific point on a device.
        Does not require the device be scheduled.

        :param requester_id: Identifier given when requesting schedule.
        :param topic: The topic of the point to set in the
                      format <device topic>/<point name>
        :param value: Value to set point to.
        :param **kwargs: These get dropped on the floor
        :type topic: str
        :type requester_id: str
        :type value: any basic python type
        :returns: value point was actually set to.
        :rtype: any base python type

        """
        topic = topic.strip('/')
        log.debug("Attempting to write " + topic + " with value: " + str(value))
        external = True
        result = self.update_topic_rpc(requester_id, topic, value, external)
        log.debug("Writing: {topic} : {value} {result}".format(topic=topic, value=value, result=result))
        if result == SUCCESS:
            return value;
        else:
            raise RuntimeError("Failed to set value: " + result)

    @RPC.export
    def revert_point(self, requester_id, topic, **kwargs):
        """RPC method

        Reverts the value of a specific point on a device to a default state.
        Does not require the device be scheduled.

        :param requester_id: Identifier given when requesting schedule.
        :param topic: The topic of the point to revert in the
                      format <device topic>/<point name>
        :param **kwargs: These get dropped on the floor
        :type topic: str
        :type requester_id: str

        """
        obj = self.find_best_match(topic)
        if obj and obj.has_key('default'):
            value = obj.get('default')
            log.debug("Reverting topic " + topic + " to " + str(value))
            external = False
            self.update_topic_rpc(requester_id, topic, value, external)
        else:
            log.warning("Unable to revert topic. No topic match or default defined!")

    @RPC.export
    def revert_device(self, requester_id, device_name, **kwargs):
        """RPC method

        Reverts all points on a device to a default state.
        Does not require the device be scheduled.

        :param requester_id: Identifier given when requesting schedule.
        :param topic: The topic of the device to revert (without a point!)
        :param **kwargs: These get dropped on the floor
        :type topic: str
        :type requester_id: str

        """
        device_name = device_name.strip('/')
        objs = self.get_inputs_from_topic(
            device_name)  # we will assume that the topic is only the <device topic> and revert all matches at this level!
        if objs is not None:
            for obj in objs:
                point_name = obj.get('field', None)
                topic = device_name + "/" + point_name if point_name else device_name
                external = False
                if obj.has_key('default'):
                    value = obj.get('default')
                    log.debug("Reverting " + topic + " to " + str(value))
                    self.update_topic_rpc(requester_id, topic, value, external)
                else:
                    log.warning("Unable to revert " + topic + ". No default defined!")

    def update_topic_rpc(self, requester_id, topic, value, external):
        obj = self.find_best_match(topic)
        if obj is not None:
            obj['value'] = value
            obj['external'] = external
            obj['last_update'] = datetime.utcnow().isoformat(' ') + 'Z'
            self.on_update_topic_rpc(requester_id, topic, value)
            return SUCCESS
        return FAILURE

    def advance_simulation(self, peer, sender, bus, topic, headers, message):
        log.info('Advancing simulation.')
        for obj in self.input().itervalues():
            log.info('ADVANCE: {}'.format(obj))
            if (obj.has_key('blocking') and obj.get('blocking')) or not obj.has_key('blocking'):
                if obj.has_key('last_update'):
                    if obj.get('last_update') is None:
                        set_topic = obj['topic'] + '/' + obj['field']
                        if obj.has_key('external') and obj['external'] == True:
                            external = True
                            value = obj['value'] if obj.has_key('value') else obj['default']
                        else:
                            external = False
                            value = obj['default']
                        self.update_topic_rpc(sender, set_topic, value, external)
        return

    def on_update_topic_rpc(self, requester_id, topic, value):
        self.update_complete()

    def on_update_complete(self):
        self.send_eplus_msg()

    class SocketServer():

        def __init__(self, **kwargs):
            self.sock = None
            self.size = 4096
            self.client = None
            self.sent = None
            self.rcvd = None
            self.host = None
            self.port = None

        def on_recv(self, msg):
            log.debug('Received %s' % msg)

        def run(self):
            self.listen()

        def connect(self):
            if self.host is None:
                self.host = socket.gethostname()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.port is None:
                self.sock.bind((self.host, 0))
                self.port = self.sock.getsockname()[1]
            else:
                self.sock.bind((self.host, self.port))
            log.debug('Bound to %r on %r' % (self.port, self.host))

        def send(self, msg):
            self.sent = msg
            if self.client is not None and self.sock is not None:
                try:
                    self.client.send(self.sent)
                except Exception:
                    log.error('We got an error trying to send a message.')

        def recv(self):
            if self.client is not None and self.sock is not None:
                try:
                    msg = self.client.recv(self.size)
                except Exception:
                    log.error('We got an error trying to read a message')
                return msg

        def start(self):
            log.debug('Starting socket server')
            self.run()

        def stop(self):
            if self.sock != None:
                self.sock.close()

        def listen(self):
            self.sock.listen(10)
            log.debug('server now listening')
            self.client, addr = self.sock.accept()
            log.debug('Connected with ' + addr[0] + ':' + str(addr[1]))
            while True:
                msg = self.recv()
                if msg:
                    self.rcvd = msg
                    self.on_recv(msg)


def main(argv=sys.argv):
    '''Main method called by the eggsecutable.'''
    try:
        utils.vip_main(EnergyPlusAgent)
    except Exception as e:
        log.exception(e)


if __name__ == '__main__':
    # Entry point for script
    sys.exit(main())
