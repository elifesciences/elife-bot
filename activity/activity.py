import boto.swf
import json
import random
import datetime

"""
Amazon SWF activity base class
"""

class activity(object):
	# Base class
	def __init__(self, settings, logger):
		self.settings = settings
		self.logger = logger
		self.result = None


