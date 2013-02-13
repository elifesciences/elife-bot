import datetime

def get_time():
	"""
	Return the current time in UTC for logging
	"""
	return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')