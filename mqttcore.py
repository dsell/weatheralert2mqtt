#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# mqtt-core
#
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"


import sys
import os
import mosquitto
import socket
import time
import subprocess
import logging
import signal
from config import Config


class MQTTClientCore:
    """
    A generic MQTT client framework class

    """
    def __init__(self, appname, clienttype):
        self.running = True
        self.mqtt_connected = False
        self.clienttype = clienttype
        self.clientversion = "unknown"
        homedir = os.path.expanduser("~")
        self.configfile = homedir + "/." + appname + '.conf'
        self.clientbase = "/clients/" + appname + "/"
        self.mqtttimeout = 60    # seconds

        if ('type1' == self.clienttype):
            self.clientname = appname
        elif ('type2' == self.clienttype):
            self.clientname = appname + "[" + socket.gethostname() + "]"
        elif ('type3' == self.clienttype):
            self.clientname = appname + "[" + socket.gethostname() + "_" +\
                              str(os.getpid()) + "]"
        else: # catchall
            self.clientname = appname

        LOGFORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        #TODO  need to deal with no config file existing!!!
        #read in configuration file
        f = file(self.configfile)
        try:
            self.cfg = Config(f)
        except:
            try:
                self.cfg = Config('/etc/mqttclients/.' + appname + '.conf')
            except:
                try:
                    self.cfg = Config('/etc/mqttclients/mqtt.conf')
                except:
                    print "Config file not found."
# could add another try and exit if no config found  TODO
        self.mqtthost = self.cfg.MQTT_HOST
        self.mqttport = self.cfg.MQTT_PORT
        self.mqtttimeout = 60  # get from config file  TODO
        self.logfile = self.cfg.LOGFILE
        self.loglevel = self.cfg.LOGLEVEL

        logging.basicConfig(filename=self.logfile, level=self.loglevel,
                            format=LOGFORMAT)

        #create an mqtt client
        self.mqttc = mosquitto.Mosquitto(self.clientname, clean_session=False)

        #trap kill signals including control-c
        signal.signal(signal.SIGTERM, self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)

    #define what happens after connection
    def on_connect(self, mself, obj, rc):
        self.mqtt_connected = True
        print "MQTT Connected"
        logging.info("MQTT connected")
        self.mqttc.publish(self.clientbase + "version",
                            self.clientversion, qos=1, retain=True)
        p = subprocess.Popen("curl ifconfig.me/forwarded", shell=True,
                              stdout=subprocess.PIPE)
        ip = p.stdout.readline()
        self.mqttc.publish(self.clientbase + "locip", ip.strip('\n'), qos=1, retain=True)
        p = subprocess.Popen("curl ifconfig.me/ip", shell=True,
                             stdout=subprocess.PIPE)
        extip = p.stdout.readline()
        self.mqttc.publish(self.clientbase + "extip", extip.strip('\n'), qos=1, retain=True)
        self.mqttc.publish(self.clientbase + "pid", os.getpid(), qos=1, retain=True)
        self.mqttc.subscribe(self.clientbase + "ping", qos=2)
        self.mqttc.publish(self.clientbase + "status", "online", qos=1, retain=True)

    def on_disconnect( self, mself, obj, rc ):
        pass

    #On recipt of a message create a pynotification and show it
    def on_message( self, mself, obj, msg):
        if (( msg.topic == self.clientbase + "ping" ) and
            ( msg.payload == "request" )):
            self.mqttc.publish(self.clientbase + "ping", "response", qos=1,
                               retain=0)

    def mqtt_connect(self):
        rc = 1
        while ( rc ):
            print "Attempting connection..."
            self.mqttc.will_set(self.clientbase, "disconnected", qos=1, retain=True)
            
            #define the mqtt callbacks
            self.mqttc.on_message = self.on_message
            self.mqttc.on_connect = self.on_connect
            self.mqttc.on_disconnect = self.on_disconnect

            #connect
            rc = self.mqttc.connect(self.mqtthost, self.mqttport,
                                    self.mqtttimeout)
            if rc != 0:
                logging.info("Connection failed with error code %s, Retrying",
                             rc)
                print ("Connection failed with error code %s, Retrying in 30 seconds.", rc)
                time.sleep(30)
            else:
                print "Connect initiated OK"


    def mqtt_disconnect(self):
        if ( self.mqtt_connected ):
            self.mqtt_connected = False
            logging.info("MQTT disconnected")
            print "MQTT Disconnected"
            self.mqttc.publish ( self.clientbase + "status" , "offline", qos=1, retain=True )
        self.mqttc.disconnect()


    def cleanup(self, signum, frame):
        self.running = False
        self.mqtt_disconnect()
        sys.exit(signum)


    def main_loop(self):
        self.mqtt_connect()
        self.mqttc.loop(10)
        while True:
            if ( self.mqtt_connected ):
                rc = self.mqttc.loop(10)
                if rc != 0:
                    self.mqtt_connected = False
                    print "Stalling for 5 seconds to allow broker connection to time out."
                    time.sleep(5)
                    self.mqtt_connect()
                    self.mqttc.loop(10)


def main(daemon):
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'run' == sys.argv[1]:
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
