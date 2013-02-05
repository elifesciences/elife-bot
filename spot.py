import boto
from boto.s3.connection import S3Connection
from boto.ec2.connection import EC2Connection
import settings as settingsLib
import json
import datetime

"""
A simple beginning to start and stop EC2 spot instances
TODO:
 - Better control features (rather than altering main and re-running)
 - Label instances better to only turn off specific ones, not all (perhaps using CloudFront)
"""

def main(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Simple EC2 connect
	conn = EC2Connection(settings.aws_access_key_id, settings.aws_secret_access_key)
	
	# Total number of spots we want to run,
	#  In test code: use 1 to start one, change to 0 to stop it
	want_spots = 0
	max_price = 0.02
	# Get 48 hours period for spot pricing history
	two_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=2)
	price_start = two_days_ago.strftime('%Y-%m-%dT%H:%M:%SZ')   # '2012-12-04T00:00:00.000Z'
	# Reference: http://aws.amazon.com/amazon-linux-ami/
	image = 'ami-e8249881'
	key_name = 'aws'
	ip_address = '107.22.188.183'
	
	# Get current spot requests
	requests = spot_request_status(conn, {'state': ['open','active']})

	if(len(requests) < want_spots):
		instance_types = ['m1.large', 'm1.medium', 'm1.small']
		average_prices = avg_spot_price(conn, instance_types, start_time = price_start)
		
		# Select the instance that matches our max price
		inst = select_instance_type(instance_types, average_prices, max_price)
		if(inst):
			# Make the new spot request
			spot_request_new(conn, instance_type=inst, price=max_price, image_id=image, key_name=key_name)
		else:
			print "No instance type met maximum price specified"
	elif (len(requests) == want_spots):
		print str(len(requests)) + " spot instances current requested"
		spotrequests = spot_request_status(conn)
		
		running = False
		running_instance = None
		for req in spotrequests:
			if(req.state == 'active'):
				running = True
				running_instance = req
		
		if(running):
			# Assign elastic IP address
			addr = boto.ec2.address.Address(conn, ip_address)
			print "Associating " + ip_address + " with instance"
			addr.associate(running_instance.instance_id)
		else:
			print "No instance running yet"
	elif (len(requests) > want_spots):
		# Too many spot instances, cancel them all
		spotrequests = spot_request_status(conn, {'state': ['open','active']})
		cancel = []
		for req in spotrequests:
			print "Cancelling request " + req.id
			cancel.append(req.id)
		print conn.cancel_spot_instance_requests(cancel, filters = {'state': ['open','active']})
		# Shutdown all running instances
		reservations = conn.get_all_instances()
		instances = []
		for res in reservations:
			for inst in res.instances:
				print "Terminating instance " + inst.id
				instances.append(inst.id)
		conn.terminate_instances(instances)
		

	
def select_instance_type(instance_types, average_prices, max_price):
	"""
	Given ordered list of instance_types, in order of preference,
	return the first instance type with price not above the max_price
	If none found, return None
	"""
	for inst in instance_types:
		if average_prices[inst] < max_price:
			return inst
	return None

def avg_spot_price(conn, instance_types, start_time):
	"""
	Get average cost of spot instances
	"""
	avgs = {}
	for instance_type in instance_types:
		spotp = conn.get_spot_price_history(instance_type=instance_type, start_time=start_time)
		count = 0
		sum = 0
		avg = 0
		for price in spotp:
			sum += price.price
			count += 1
		try:
			avg = sum/count
		except():
			avg = None
		# Push onto return array
		#avg_result = {instance_type: avg}
		avgs[instance_type] = avg
		
	return avgs
	
def spot_request_new(conn, instance_type, price, image_id, key_name = None):
	"""
	Stub, make new spot request
	"""
	print 'Making new spot request'

	# Make the actual request!
	conn.request_spot_instances(price, image_id, instance_type=instance_type, key_name=key_name)
	
def spot_request_status(conn, filters = None):
	"""
	Get spot request status
	"""
	return conn.get_all_spot_instance_requests(filters=filters)
	
def bind_elastic_ip(instance_id):
	"""
	Bind elastic IP to an instance
	"""

if __name__ == "__main__":
	main()