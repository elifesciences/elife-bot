import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import settings as settingsLib
import log
import json
import random
import datetime
import importlib
import time
from multiprocessing import Process
from optparse import OptionParser

import workflow

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
			
			# Check for a nextPageToken and keep polling until all events are pulled
			decision = get_all_paged_events(decision, conn, settings.domain, settings.default_task_list, identity, maximum_page_size)
			
			token = get_taskToken(decision)
			
			logger.info('got decision: [json omitted], token %s' % token)
			#logger.info('got decision: \n%s' % json.dumps(decision, sort_keys=True, indent=4))

			if(token != None):
				# Get the workflowType and attempt to do the work
				workflowType = get_workflowType(decision)
				if(workflowType != None):

					logger.info('workflowType: %s' % workflowType)

					# Instantiate and object for the workflow using eval
					# Build a string for the object name
					workflow_name = get_workflow_name(workflowType)
					
					# Attempt to import the module for the workflow
					if(import_workflow_class(workflow_name)):
						# Instantiate the workflow object
						workflow_object = get_workflow_object(workflow_name, settings, logger, conn, token, decision, maximum_page_size)
				
						# Process the workflow
						success = workflow_object.do_workflow()
						
						# Print the result to the log
						logger.info('%s success %s' % (workflow_name, success))
						
					else:
						logger.info('error: could not load object %s\n' % workflow_name)
						
		# Reset and loop
		token = None
		
def get_all_paged_events(decision, conn, domain, task_list, identity, maximum_page_size):
	"""
	Given a poll_for_decision_task response, check if there is a nextPageToken
	and if so, recursively poll for all workflow events, and assemble a final
	decision response to return
	"""
	
	# First check if there is no nextPageToken, if there is none
	#  return the decision, nothing to page
	next_page_token = None
	try:
		next_page_token = decision["nextPageToken"]
	except KeyError:
		next_page_token = None
	if(next_page_token is None):
		return decision

	# Continue, we have a nextPageToken. Assemble a full array of events by continually polling
	all_events = decision["events"]
	while(next_page_token is not None):
		try:
			next_page_token = decision["nextPageToken"]
			if(next_page_token is not None):
				decision = conn.poll_for_decision_task(domain, task_list, identity, maximum_page_size, next_page_token)
				for event in decision["events"]:
					all_events.append(event)
		except KeyError:
			next_page_token = None
	
	# Finally, reset the original decision response with the full set of events
	decision["events"] = all_events

	return decision
		
def get_input(decision):
	"""
	From the decision response, which is JSON data form SWF, get the
	input data that started the workflow
	"""
	try:
		input = json.loads(decision["events"][0]["workflowExecutionStartedEventAttributes"]["input"])
	except KeyError:
		input = None
	return input
		
def get_taskToken(decision):
	"""
	Given a response from polling for decision from SWF via boto,
	extract the taskToken from the json data, if present
	"""
	try:
		return decision["taskToken"]
	except KeyError:
		# No taskToken returned
		return None
		
def get_workflowType(decision):
	"""
	Given a polling for decision response from SWF via boto,
	extract the workflowType from the json data
	"""
	try:
		return decision["workflowType"]["name"]
	except KeyError:
		# No workflowType found
		return None

def get_workflow_name(workflowType):
	"""
	Given a workflowType, return the name of a
	corresponding workflow class to load
	"""
	return "workflow_" + workflowType
		
def import_workflow_class(workflow_name):
	"""
	Given an workflow subclass name as workflow_name,
	attempt to lazy load the class when needed
	"""
	try:
		module_name = "workflow." + workflow_name
		importlib.import_module(module_name)
		# Reload the module, in case it was imported before
		reload_module(module_name)
		return True
	except ImportError:
		return False
	
def reload_module(module_name):
	"""
	Given an module name,
	attempt to reload the module
	"""
	try:
		reload(eval(module_name))
	except:
		pass
		
def get_workflow_object(workflow_name, settings, logger, conn, token, decision, maximum_page_size):
	"""
	Given a workflow_name, and if the module class is already
	imported, create an object an return it
	"""
	full_path = "workflow." + workflow_name + "." + workflow_name
	f = eval(full_path)
	# Create the object
	workflow_object = f(settings, logger, conn, token, decision, maximum_page_size)
	return workflow_object
		
def start_single_thread(ENV):
	"""
	Start in single process / threaded mode, but
	return a pool resource of None to indicate it
	is running in a single thread
	"""
	print 'starting single thread'
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
		# Sleep briefly so polling connections do not happen at once
		time.sleep(0.5)
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
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	parser.add_option("-f", "--forks", default=10, action="store", type="int", dest="forks", help="specify the number of forks to start")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env
	if options.forks: 
		forks = options.forks

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
