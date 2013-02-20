import boto.swf
import os
import json
import random
import datetime

# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

#import settings as settingsLib
#import log

"""
Amazon SWF activity base class
"""

class activity(object):
	# Base class
	def __init__(self, settings, logger):
		self.settings = settings
		self.logger = logger

		
