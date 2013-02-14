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
import datetime


class MQTTClientCore:
    """
    A generic MQTT client framework class

    """
    def __init__(self, appname, clienttype, clean_session=True):
        self.running = True
        self.connectcount = 0
        self.starttime=datetime.datetime.now()
        self.connecttime=0 #datetime.datetime.now()
        self.mqtt_connected = False
        self.clienttype = clienttype
        self.clean_session = clean_session
        self.clientversion = "unknown"
        homedir = os.path.expanduser("~")
        self.configfile = homedir + "/." + appname + '.conf'
        self.mqtttimeout = 60    # seconds

        if ('type1' == self.clienttype):
            self.clientname = appname
            self.persist = True
        elif ('type2' == self.clienttype):
            self.persist = True
            self.clientname = appname + "[" + socket.gethostname() + "]"
        elif ('type3' == self.clienttype):
            self.clientname = appname + "[" + socket.gethostname() + "_" +\
                              str(os.getpid()) + "]"
            self.persist = False
        else: # catchall
            self.clientname = appname
        self.clientbase = "/clients/" + self.clientname + "/"
        LOGFORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        #TODO  need to deal with no config file existing!!!
        #read in configuration file
        f = self.configfile
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
                    sys.exit(99)

        self.mqtthost = self.cfg.MQTT_HOST
        self.mqttport = self.cfg.MQTT_PORT
        self.mqtttimeout = 60  # get from config file  TODO
        self.logfile = self.cfg.LOGFILE
        self.loglevel = self.cfg.LOGLEVEL
        try:
            self.ca_path = cfg.CA_PATH
        except:
            self.ca_path = None
            try:
                self.ssl_port = cfg.SSL_PORT
                self.ssl_host = cfg.SSL_HOST
            except:
                self.ssl_port = None
                self.ssl_host = None

        logging.basicConfig(filename=self.logfile, level=self.loglevel,
                            format=LOGFORMAT)

        #create an mqtt client
        self.mqttc = mosquitto.Mosquitto(self.clientname, clean_session=self.clean_session)

        #trap kill signals including control-c
        signal.signal(signal.SIGTERM, self.cleanup)
        signal.signal(signal.SIGINT, self.cleanup)

    def getifip(ifn):
        # print ip
        import socket, fcntl, struct

        sck = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(sck.fileno(),0x8915,struct.pack('256s', ifn[:15]))[20:24])

    def identify(self):
        self.mqttc.publish(self.clientbase + "version",
                            self.clientversion, qos=1, retain=self.persist)
#        p = subprocess.Popen("curl ifconfig.me/forwarded", shell=True,
        p = subprocess.Popen("ip -f inet  addr show | tail -n 1 | cut -f 6 -d' ' | cut -f 1 -d'/'", shell=True,
                              stdout=subprocess.PIPE)
        ip = p.stdout.readline()
        self.mqttc.publish(self.clientbase + "locip", ip.strip('\n'), qos=1, retain=self.persist)
        p = subprocess.Popen("curl -s ifconfig.me/ip", shell=True,
                             stdout=subprocess.PIPE)
        extip = p.stdout.readline()
        self.mqttc.publish(self.clientbase + "extip", extip.strip('\n'), qos=1, retain=self.persist)
        self.mqttc.publish(self.clientbase + "pid", os.getpid(), qos=1, retain=self.persist)
        self.mqttc.publish(self.clientbase + "status", "online", qos=1, retain=self.persist)
        self.mqttc.publish(self.clientbase + "start", str(self.starttime), qos=1, retain=self.persist)
        self.mqttc.publish(self.clientbase + "connecttime", str(self.connecttime), qos=1, retain=self.persist)
        self.mqttc.publish(self.clientbase + "count", self.connectcount, qos=1, retain=self.persist)

    #define what happens after connection
    def on_connect(self, mself, obj, rc):
        self.mqtt_connected = True
        self.connectcount = self.connectcount+1
        self.connecttime=datetime.datetime.now()
        print "MQTT Connected"
        logging.info("MQTT connected")
        self.mqttc.subscribe(self.clientbase + "ping", qos=2)
        self.mqttc.subscribe("/clients/global/#", qos=2)
        self.identify()

    def on_disconnect( self, mself, obj, rc ):
        pass

    #On recipt of a message create a pynotification and show it
    def on_message( self, mself, obj, msg):
        if ((( msg.topic == self.clientbase + "ping" ) and
            ( msg.payload == "request" )) or
            (( msg.topic == "/clients/global/ping" ) and
            ( msg.payload == "request" ))):
            self.mqttc.publish(self.clientbase + "ping", "response", qos=1,
                               retain=0)
        if (( msg.topic == "/clients/global/identify" ) and
            ( msg.payload == "request" )):
            self.identify()

    def mqtt_connect(self):
        if ( True != self.mqtt_connected ):
            rc = 1
            while ( rc ):
                print "Attempting connection..."
                if(self.ssl_port != None):
                    print "Using ssl for security"
                    self.sslpid = subprocess.Popen("ssh -f -n -N -L 127.0.0.1:%d:localhost:%d user@%s"
                             % (self.ssh_port, self.mqtt_port, self.ssh_host),
                                 shell=True, close_fds=True)
                    self.mqtt_host = "localhost"
                    self.mqtt_port = self.ssh
                else: 
                    self.sslpid = None
                if(self.ca_path != None):
                    print "Using CA for security"
                    self.mqttc.tls_set(self.ca_path)

                self.mqttc.will_set(self.clientbase, "disconnected", qos=1, retain=self.persist)
                
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
            self.mqttc.publish ( self.clientbase + "status" , "offline", qos=1, retain=self.persist )
            self.mqttc.disconnect()
            try:
                os.kill(self.sslpid, 15) # 15 = SIGTERM
            except:
                print "PID invalid"


    def cleanup(self, signum, frame):
        self.running = False
        self.mqtt_disconnect()
        sys.exit(signum)


    def main_loop(self):
        self.mqtt_connect()
        self.mqttc.loop()
        while True:
            if ( self.mqtt_connected ):
                rc = self.mqttc.loop()
                if rc != 0:
                    self.mqtt_connected = False
                    print "Stalling for 5 seconds to allow broker connection to time out."
                    time.sleep(5)
                    self.mqtt_connect()
                    self.mqttc.loop()


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
