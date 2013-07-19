import json
import random
import datetime
import calendar
import time
import zipfile
import requests
import urlparse
import os

"""
Local file system data provider
A home for functions so code is not duplicated
"""

class Filesystem(object):
	
	def __init__(self, tmp_dir):
		self.tmp_dir = tmp_dir
	
	def read_document_to_content(self, document):
		mode = "r"
		
		try:
			o = urlparse.urlparse(document)
			if(o.scheme != ""):
				document = self.download_document(document)
				self.document = document
		except AttributeError:
			pass
		
		if(self.is_zip(document)):
			document = self.unzip_document(document)
			self.document = document
		
		f = open(document, mode)
		self.content = f.read()
		f.close()

	def write_content_to_document(self, filename):
		mode = "w"
		
		f = self.open_file_from_tmp_dir(filename, mode)
		f.write(self.content)
		f.close()
		
		# Reset the object document
		tmp_dir = self.get_tmp_dir()
		if(tmp_dir):
			self.document = tmp_dir + os.sep + filename
		else:
			self.document = filename

	def download_document(self, document, filename = None, validate_url = True, scheme = None, netloc = None):
		"""
		Attempt to download the document, with some simple
		URL validation built in
		"""

		o = urlparse.urlparse(document)
		
		if(validate_url == True):
			if(scheme is not None and netloc is not None):
				# User defined scheme and netloc to validate
				pass
			else:
				# If not supplied, rely on S3
				scheme = "https"
				netloc = "s3.amazonaws.com"
			# Validate
			if(o.scheme != scheme and o.netloc != netloc):
				return None
			
		# All good, continue
		if(filename is None):
			filename = ""
			path_array = o.path.split('/')
			filename = path_array[-1]
		
		r = requests.get(document, prefetch=False)
		mode = "wb"
		f = self.open_file_from_tmp_dir(filename, mode)
		for block in r.iter_content(1024):
			if not block:
				break
			f.write(block)
		f.close()
			
		tmp_dir = self.get_tmp_dir()
		if(tmp_dir):
			document = tmp_dir + os.sep + filename
		else:
			document = filename

		return document

	def open_file_from_tmp_dir(self, filename, mode = 'r'):
		"""
		Read the file from the tmp_dir
		"""
		tmp_dir = self.get_tmp_dir()
		
		if(tmp_dir):
			full_filename = tmp_dir + os.sep + filename
		else:
			full_filename = filename
		
		f = open(full_filename, mode)
		return f

	def is_zip(self, document):
		"""
		Given a document name, determine if it a zip file
		"""
		fileName, fileExtension = os.path.splitext(document)
		if(fileExtension == ".zip"):
			return True
		return False
		
	def unzip_document(self, document):
		"""
		Unzip the document if it is a zip,
		and return the document name
		"""
		mode = "r"

		tmp_dir = self.get_tmp_dir()

		z = zipfile.ZipFile(document)

		filename = None
		for f in z.namelist():
			z.extract(f, tmp_dir)
			filename = f
		z.close()
		
		# Only handles one file at a time, for now
		if(tmp_dir):
			document = tmp_dir + os.sep + filename
		else:
			document = filename
		
		return document
	
	def get_document(self):
		"""
		Return the document name of the file
		"""
		# Only handles one file at a time, for now
		return self.document
	
	def get_tmp_dir(self):
		"""
		Get the temporary file directory
		"""
		if(self.tmp_dir):
			return self.tmp_dir
		return None
