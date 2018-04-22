#!/usr/bin/env python

#
# ROS node for Xiaomi Yi action camera
#
# (c) 2018 - Bayu Laksono <bayu.laksono@gmail.com>
#

import rospy
import socket
import fcntl, os
import errno
import sys
import json
import time
from std_msgs.msg import String
from ros_yi.srv import *

sock = None
buff = ""
token = 0
battery = 0
last_dt = time.time()

def send(obj):
	global sock
	if sock != None:
		try: 
			data = json.dumps(obj)
			#print data
			sock.sendall(data)
		except:
			raise

def receive():
	global sock, buff
	if sock != None:
		try:
			data = ""
			while True:
				if len(buff) <= len(data):
					buff = buff + sock.recv(1024)
				if len(buff) > len(data):
					data = buff[:len(data)+1]
					try:
						obj = json.loads(data);
						print data
						buff = buff[len(data):]
						return obj;
					except:
						pass
				else:
					break
			return None

		except socket.error, e:
			err = e.args[0]
			if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
				return None
			else:
				raise
	return None

def handle_connect(param):
	global sock, token
	if sock != None:
		token = 0
		sock.close()
		sock = None
	res = 0
	try:
		sock = socket.create_connection((param.host, 7878))
		fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)
		req = {}
		req["msg_id"] = 257
		req["token"] = 0
		send(req)
		res = 1
	except:
		res = 0
		raise
	return ConnectResponse(res)

def send_command(msg_id):
	global token
	res = 0
	if token != 0:
		try:
			req = {}
			req["msg_id"] = msg_id
			req["token"] = token
			send(req)
			res = 1
		except:
			res = 0
			raise
	return res

def handle_command(param):
	res = send_command(param.msg_id)
	return CommandResponse(res)

def handle_streaming(param):
	global token
	res = 0
	if param.flag == 1:
		res = send_command(259)
	else:
		res = send_command(260)
	return StreamingResponse(res)

def handle_capture(param):
	res = send_command(769)
	return CaptureResponse(res)

def handle_record(param):
	if param.flag == 1:
		res = send_command(513)
	else:
		res = send_command(514)
	return RecordResponse(res)

def handle_setting(param):
	global token
	res = 0
	if token != 0:
		try:
			req = {}
			req["msg_id"] = 2
			req["type"] = param.name
			req["param"] = param.value
			req["token"] = token
			send(req)
			res = 1
		except:
			res = 0
			raise
	return SettingResponse(res)

def check_status():
	global last_dt
	send_command(13)
	last_dt = time.time()
	
def ros_yi_server():
	global sock, token, last_dt
	rospy.init_node('ros_yi')
	pub = rospy.Publisher('ros_yi_monitor', String, queue_size=10)
	connect = rospy.Service('ros_yi/connect', Connect, handle_connect)
	command = rospy.Service('ros_yi/command', Command, handle_command)
	streaming = rospy.Service('ros_yi/streaming', Streaming, handle_streaming)
	capture = rospy.Service('ros_yi/capture', Capture, handle_capture)
	record = rospy.Service('ros_yi/record', Record, handle_record)
	setting = rospy.Service('ros_yi/setting', Setting, handle_setting)
	rate = rospy.Rate(10) # 10hz
  	while not rospy.is_shutdown():
		if time.time() - last_dt > 30:
			last_dt = time.time()
			check_status()
		obj = receive()
		if obj is None:
			rate.sleep()
		else:
			if obj["msg_id"] == 257:
				token = obj["param"]
				check_status()
			if obj["msg_id"] == 7:
				if obj["type"] == "battery":
					battery = obj["param"]
					stat = {}
					stat["battery"] = battery
					pub.publish(json.dumps(stat))
			if obj["msg_id"] == 13:
				if obj["type"] == "battery":
					battery = obj["param"]
					stat = {}
					stat["battery"] = battery
					pub.publish(json.dumps(stat))
			rate.sleep()
	if sock != None:
		sock.close()

if __name__ == '__main__':
	try:
		ros_yi_server()
	except rospy.ROSInterruptException:
		pass

