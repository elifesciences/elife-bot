import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import settings as settingsLib
import log
import json
import random
import datetime
import time
from multiprocessing import Process

from workflow import workflow_Ping
from workflow import workflow_Sum

"""
Amazon SWF decider
"""

def decide(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Decider event history length requested
	maximum_page_size = 100
	
	# Log
	identity = "decider_%s" % int(random.random() * 1000)
	logFile = "decider.log"
	#logFile = None
	logger = log.logger(logFile, settings.setLevel, identity)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	token = None

	# Poll for a decision task
	while(True):
		if(token == None):
			logger.info('polling for decision...')
			
			decision = conn.poll_for_decision_task(settings.domain, settings.default_task_list, identity, maximum_page_size)
			
			try:
				token = decision["taskToken"]
			except KeyError:
				# No taskToken returned
				pass
			
			logger.info('got decision: [json omitted]')
			#logger.info('got decision: \n%s' % json.dumps(decision, sort_keys=True, indent=4))
			
			if(token != None):
				# Get the workflowType and attempt to do the work
				try:
					workflowType = decision["workflowType"]["name"]
					logger.info('workflowType: %s' % workflowType)
				except KeyError:
					continue
				
				# Instantiate and object for the workflow using eval
				#try:
				# Build a string for the object name
				workflow_name = "workflow_" + workflowType
				# Concatenate the object_name.object_name as the callable
				f = eval(workflow_name + "." + workflow_name)
				# Create the object
				workflow_object = f(settings, logger, conn, token, decision, maximum_page_size)
				
				# Process the workflow
				data = None
				success = workflow_object.do_workflow(data)
					
				#except NameError:
					# Workflow class of the type we want does not exist
				#	success = False
				logger.info('%s success %s' % (workflow_name, success))
				
		# Reset and loop
		token = None
		
def start_single_thread(ENV):
	"""
	Start in single process / threaded mode, but
	return a pool resource of None to indicate it
	is running in a single thread
	"""
	decide(ENV)
	return None
	
def start_multiple_thread(ENV):
	"""
	Start multiple processes using a manual pool
	"""
	pool = []
	for num in range(forks):
		p = Process(target=decide, args=(ENV,))
		p.start()
		pool.append(p)
		print 'started decider thread'
	return pool

def monitor_KeyboardInterrupt(pool = None):
	# Monitor for keyboard interrupt ctrl-C
	try:
		time.sleep(10)
	except KeyboardInterrupt:
		print 'caught KeyboardInterrupt, terminating threads'
		if(pool != None):
			for p in pool:
				p.terminate()
		return False
	return True

if __name__ == "__main__":
	forks = 10
	ENV = "dev"

	pool = None
	try:
		if(forks > 1):
			pool = start_multiple_thread(ENV)
		else:
			pool = start_single_thread(ENV)
	except:
		# If forks is not specified start in single threaded mode
		pool = start_single_thread(ENV)

	# Monitor for keyboard interrupt ctrl-C
	loop = True
	while(loop):
		loop = monitor_KeyboardInterrupt(pool)
