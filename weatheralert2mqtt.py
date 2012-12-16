#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# weather-alert-bridge
#	Provides NOAA weather alert information
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"



import os
import sys
import mosquitto
import time
import logging
import signal
import threading
from config import Config
from weatheralerts import nws


CLIENT_NAME = "weatheralert2mqtt"
CLIENT_VERSION = "0.4"
MQTT_TIMEOUT = 60	#seconds


#TODO might want to add a lock file
#TODO  need to deal with no config file existing!!!
#TODO move config file to home dir


#read in configuration file
homedir = os.path.expanduser("~")
f = file(homedir + '.weatheralert2mqtt.conf')
cfg = Config(f)
MQTT_HOST = cfg.MQTT_HOST
MQTT_PORT = cfg.MQTT_PORT
CLIENT_TOPIC = cfg.CLIENT_TOPIC
BASE_TOPIC = cfg.BASE_TOPIC
COUNTIES = cfg.COUNTIES
INTERVAL = cfg.INTERVAL


mqtt_connected = 0


#define what happens after connection
def on_connect(self, obj, rc):
	global mqtt_connected
	global running
	global alerts

	mqtt_connected = True
	print "MQTT Connected"
	mqttc.publish( CLIENT_TOPIC + "status" , "running", 1, 1 )
	mqttc.publish( CLIENT_TOPIC + "version", CLIENT_VERSION, 1, 1 )
	mqttc.subscribe( CLIENT_TOPIC + "ping", 2)


def do_weatheralert_loop():
	global running
	global COUNTIES
	global mqttc

	while ( running ):
		if ( mqtt_connected ):
			for location in COUNTIES:
				req_county = location.county
				req_state = location.state
				print "Querrying for ", req_county, " county ", req_state
				try:
					alerts.activefor_county(location)
					result = alerts.activefor_county(location)
					mqttc.publish( BASE_TOPIC + req_state + "/" + req_county + "/alert", str(result), qos = 2, retain = 1 )
				except KeyboardInterrupt:
					print u"  ........Exiting."
					sys.exit()

				mqttc.publish( BASE_TOPIC + req_state + "/" + req_county + "/time", time.strftime( "%x %X" ), qos = 2, retain = 1)
			if ( INTERVAL ):
				print "Waiting ", INTERVAL, " minutes for next update."
				time.sleep(60 * INTERVAL)
			else:
				running = False	#do a single shot
				print "Querries complete."
		pass


def mqtt_connect():

	rc = 1
	while ( rc ):
		print "Attempting connection..."
		mqttc.will_set(CLIENT_TOPIC + "status", "disconnected_", 1, 1)

		#define the mqtt callbacks
		mqttc.on_message = on_message
		mqttc.on_connect = on_connect
#		mqttc.on_disconnect = on_disconnect

		#connect
		rc = mqttc.connect( MQTT_HOST, MQTT_PORT, MQTT_TIMEOUT )
		if rc != 0:
			logging.info( "Connection failed with error code $s, Retrying in 30 seconds.", rc )
			print "Connection failed with error code ", rc, ", Retrying in 30 seconds." 
			time.sleep(30)
		else:
			print "Connect initiated OK"


def on_message(self, obj, msg):
	if (( msg.topic == CLIENT_TOPIC + "ping" ) and ( msg.payload == "request" )):
		mqttc.publish( CLIENT_TOPIC + "ping", "response", qos = 1, retain = 0 )


def do_disconnect():
       global connected
       mqttc.disconnect()
       connected = 0
       print "Disconnected"

#TODO are these redundant?????????????

def mqtt_disconnect():
	global mqtt_connected
	print "Disconnecting..."
	mqttc.disconnect()
	if ( mqtt_connected ):
		mqtt_connected = False 
		print "MQTT Disconnected"


def mqtt_connect():

	rc = 1
	while ( rc ):
		print "Attempting connection..."
		mqttc.will_set(CLIENT_TOPIC + "status", "disconnected_", 1, 1)

		#define the mqtt callbacks
		mqttc.on_message = on_message
		mqttc.on_connect = on_connect
#		mqttc.on_disconnect = on_disconnect

		#connect
		rc = mqttc.connect( MQTT_HOST, MQTT_PORT, MQTT_TIMEOUT )
		if rc != 0:
			logging.info( "Connection failed with error code $s, Retrying in 30 seconds.", rc )
			print "Connection failed with error code ", rc, ", Retrying in 30 seconds." 
			time.sleep(30)
		else:
			print "Connect initiated OK"



def cleanup(signum, frame):
	mqtt_disconnect()
	sys.exit(signum)


alerts = nws.Alerts()

#create a client
mqttc = mosquitto.Mosquitto( CLIENT_NAME ) 

#trap kill signals including control-c
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

running = True

t = threading.Thread(target=do_weatheralert_loop)
t.start()


def main_loop():
	global mqtt_connected
	mqttc.loop(10)
	while running:
		if ( mqtt_connected ):
			rc = mqttc.loop(10)
			if rc != 0:	
				mqtt_disconnect()
				print rc
				print "Stalling for 20 seconds to allow broker connection to time out."
				time.sleep(20)
				mqtt_connect()
				mqttc.loop(10)
		pass


mqtt_connect()
main_loop()












