#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# weather-alert-bridge
#	Provides NOAA weather alert information
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"


APPNAME = "weatheralert2mqtt"
VERSION = "0.7"
WATCHTOPIC = "/raw/" + APPNAME + "/command"


from weatheralerts import nws
import time
import subprocess
from daemon import Daemon
from mqttcore import MQTTClientCore
from mqttcore import main
import threading

class MyMQTTClientCore(MQTTClientCore):
    def __init__(self, appname, clienttype):
        MQTTClientCore.__init__(self, appname, clienttype)
        self.clientversion = VERSION
        self.watchtopic = WATCHTOPIC
        self.workingdir = self.cfg.WORKINGDIR
        self.counties = self.cfg.COUNTIES
        self.interval = self.cfg.INTERVAL
        self.basetopic = self.cfg.BASE_TOPIC
    
        t = threading.Thread(target=self.do_thread_loop)
        t.start()

    def on_connect(self, mself, obj, rc):
        MQTTClientCore.on_connect(self, mself, obj, rc)
        self.mqttc.subscribe(self.watchtopic, qos=2)

    def on_message(self, mself, obj, msg):
        MQTTClientCore.on_message(self, mself, obj, msg)
        if (msg.topic == self.watchtopic):
            try:
                print msg.payload
                filename = self.workingdir + msg.payload + ".mp3"
                pid = subprocess.Popen('mplayer -softvol ' +
                                        filename, shell=True).pid
            except:
                print "Unknown command"

    def do_thread_loop(self):
        alerts = nws.Alerts()
        while ( self.running ):
		    if ( self.mqtt_connected ):
			    for location in self.counties:
				    print "Querrying for ", location.county, " county ", location.state
				    try:
#qos set wrong!!! broken TODO	
                        result = "Failed to retreive"
					    result = alerts.activefor_county(location)
					    self.mqttc.publish( self.basetopic + location.state + "/" + location.county + "/alert", str(result), qos = 0, retain = 1 )
				    except:
					    print "error in weatheralerts."
				    self.mqttc.publish( self.basetopic + location.state + "/" + location.county + "/time", time.strftime( "%x %X" ), qos = 0, retain = 1)
			    if ( self.interval ):
				    print "Waiting ", self.interval, " minutes for next update."
				    time.sleep(60 * self.interval)
			    else:
				    self.running = False	#do a single shot
				    print "Querries complete."
		    pass


class MyDaemon(Daemon):
    def run(self):
        mqttcore = MyMQTTClientCore(APPNAME, clienttype="type1")
        mqttcore.main_loop()


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/' + APPNAME + '.pid')
    main(daemon)
