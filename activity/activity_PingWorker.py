import boto.swf
import os
import json
import random
import datetime

# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

import activity

"""
PingWorker activity
"""

class activity_PingWorker(activity.activity):
	
	def do_activity(self, data = None):
		"""
		PingWorker activity, do the work, in this case
		just return true
		"""
		return True
