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
		self.document = None
	
	def read_document_from_tmp_dir(self, filename):
		mode = "r"
		
		content = None
		
		# Hack: remove the tmp directory from the filename if already present
		try:
			filename = filename.replace(self.tmp_dir + os.sep, "")
		except:
			pass

		f = self.open_file_from_tmp_dir(filename, mode)
		content = f.read()
		f.close()
		
		return content
		
	def write_document_to_tmp_dir(self, document, filename = None):

		try:
			o = urlparse.urlparse(document)
			if(o.scheme != ""):
				# Downloading a document should always result in a single document
				filename = self.download_document(document, filename)
			else:
				# A local file, copy it over to our tmp directory
				if(filename is None):
					filename = ""
					path_array = document.split('/')
					filename = path_array[-1]
				
				f_read = open(document, "rb")
				f_write = self.open_file_from_tmp_dir(filename, "wb")
				f_write.write(f_read.read())
				f_write.close()
				f_read.close()

		except AttributeError:
			pass

		if(self.is_zip(filename)):
			# If the document is a zip file, unzipping it may result in multiple files
			#  and if so unzip_document will return a list of document
			document = self.unzip_document(filename)
		else:
			document = filename
		# Finally set the class variable with the result
		self.document = document

	def write_content_to_document(self, content, filename, mode = "w"):
		
		f = self.open_file_from_tmp_dir(filename, mode)
		f.write(content)
		f.close()
		
		self.document = filename

	def download_document(self, document_url, filename = None, validate_url = True, scheme = None, netloc = None):
		"""
		Attempt to download the document, with some simple
		URL validation built in
		"""

		o = urlparse.urlparse(document_url)
		
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
		
		r = requests.get(document_url, stream=True)
		mode = "wb"
		f = self.open_file_from_tmp_dir(filename, mode)
		for block in r.iter_content(1024):
			if not block:
				break
			f.write(block)
		f.close()

		return filename

	def open_file_from_tmp_dir(self, filename, mode = 'r'):
		"""
		Read the file from the tmp_dir
		"""
		tmp_dir = self.get_tmp_dir()

		# Create or check tmp_dir exists when we open files
		self.make_tmp_dir()

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
		
	def unzip_document(self, filename):
		"""
		Unzip the document if it is a zip,
		and return the document name
		"""
		mode = "r"

		tmp_dir = self.get_tmp_dir()

		if(tmp_dir):
			full_filename = tmp_dir + os.sep + filename
		else:
			full_filename = filename

		z = zipfile.ZipFile(full_filename)

		new_filename = None
		new_document = None
		
		for f in z.namelist():
			z.extract(f, tmp_dir)
			new_filename = f

			# Handle single or multiple files as zip contents
			if(len(z.namelist()) == 1):
				# A single file inside
				new_document = new_filename
			elif(len(z.namelist()) > 1):
				# Multiple files inside
				if(new_document is None):
					new_document = []
				new_document.append(new_filename)
				
		z.close()

		return new_document
	
	def get_document(self):
		"""
		Return the document name of the file
		or list of document names
		"""
		return self.document
	
	def get_tmp_dir(self):
		"""
		Get the temporary file directory
		"""
		if(self.tmp_dir):
			return self.tmp_dir
		return None

	def make_tmp_dir(self):
		"""
		Make the tmp_dir directory
		"""
		# Check if the tmp_dir exists, if not create it
		if(self.tmp_dir):
			try:
				os.mkdir(self.tmp_dir)
			except OSError:
				# Directory may already exist, happens when running tests, check if it exists
				if(os.path.isdir(self.tmp_dir)):
					self.tmp_dir = self.tmp_dir
				else:
					self.tmp_dir = None