#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# weather-alert-bridge
#	Provides NOAA weather alert information
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"



import sys
import mosquitto
import socket
import time
import subprocess
import logging
import signal
import pynotify
import threading
#from config import Config
from weatheralerts import nws


CLIENT_NAME = "weather-alert-bridge"
CLIENT_VERSION = "0.4"
BASE_TOPIC = "/raw/weatheralert/"
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TIMEOUT = 60	#seconds

timer = 10000
mqtt_connected = 0

REQCOUNTY = sys.argv[1]
REQSTATE = sys.argv[2]


#define what happens after connection
def on_connect(self, obj, rc):
	global connected
	global timer
	global alerts

	connected = 1
	print "MQTT Connected"
	mqttc.publish ( "/clients/" + CLIENT_NAME + "/status" , "running", 1, 1 )
	mqttc.publish("/clients/" + CLIENT_NAME + "/version", CLIENT_VERSION, 1, 1)

	req_location = { u'county': REQCOUNTY, u'state': REQSTATE }
	try:
		alerts.activefor_county(req_location)
		result = alerts.activefor_county(req_location)
		mqttc.publish( BASE_TOPIC + REQCOUNTY + "-" + REQSTATE + "/alert", str(result), qos = 2, retain = 1 )
	except KeyboardInterrupt:
		print u"  ........Exiting."
		sys.exit()

	mqttc.publish( BASE_TOPIC + REQCOUNTY + "-" + REQSTATE + "/time", time.strftime( "%x %X" ), qos = 2, retain = 1)
	timer = 20


def do_disconnect():
       global connected
       mqttc.disconnect()
       connected = 0
       print "Disconnected"


#create a client
mqttc = mosquitto.Mosquitto( CLIENT_NAME ) 

mqttc.will_set("/clients/" + CLIENT_NAME + "/status", "done", 1, 1)

#define the callbacks
mqttc.on_connect = on_connect

alerts = nws.Alerts()

#connect
rc = mqttc.connect( MQTT_HOST, MQTT_PORT, MQTT_TIMEOUT )
print "waiting for message to pass"
if rc == 0:
	mqttc.loop()
while  timer > 0:
			rc = mqttc.loop()
			if rc != 0:
				do_disconnect()
				pass
			pass
			timer = timer - 1
mqttc.publish("/clients/" + CLIENT_NAME + "/status", "done", 1, 1)
mqttc.loop()
mqttc.loop()
mqttc.disconnect()
print "disconnected"












