import boto.swf
import os
import json
import random
import datetime

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
		self.result = True
		return True
