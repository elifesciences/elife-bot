import glob
from ftplib import FTP
from collections import namedtuple
from optparse import OptionParser

"""
check files at an ftp server
compare with a set of files locally
download new files

"""


CURRENT_XML_PATH = "/Users/ian/code/public-code/elife-articles"

# pull ftp in credentials

FTP_AUTH_INFO = "/Users/ian/code/public-code/elife-bot/ftp-credentials.txt"
FTP_KEYS = namedtuple('Keys', "host user password")

def get_value_from_line(line):
    value = line.split(":")[1].strip()
    return value 

def get_keys(keys_file, tuple):
    lines = open(keys_file, 'r').readlines()
    values = []
    expected_number_of_fields = len(tuple._fields)
    for i in range(expected_number_of_fields):
        part = get_value_from_line(lines[i])
        values.append(part)
    this_tuple = tuple._make(values)
    return this_tuple
    
FTP_AUTH = get_keys(FTP_AUTH_INFO, FTP_KEYS)

# do stuff

def download_cb(block):
    file.write(block)

def get_current_files():
    current_files = glob.glob(CURRENT_XML_PATH + "/*.xml")
    return current_files 

def get_number_from_filename(filename):
    number = filename[-9:-4] # filenames have the form elife00065.xml 
    return number 

def get_current_file_numbers():
    current_file_numbers = []
    current_files = get_current_files()
    for current_file in current_files:
        current_file_numbers.append(get_number_from_filename(current_file))
    return current_file_numbers

def retreive_file(ftp, filename):
    print filename
    file = open(filename, "wb")
    ftp.retrbinary("RETR " + filename, file.write)
    file.close()

def list_new_ftp_files(all_files, old_files):
    new_files = []
    for filename in all_files:
        if filename not in old_files:
            new_files.append(filename)
    return new_files

def retreive_files(ftp, home, files):
    for filenum in files:
        ftp.cwd(filenum)
        data = ftp.nlst()
        wants = []
        for representation in data:
            if representation.find("xml") > -1 or representation.find("pdf") > -1:
                wants.append(representation)
        for wanted in wants:
            print wanted 
            retreive_file(ftp, wanted)
        print wants
        ftp.cwd(home)

def setup_ftp():
    elife_ftp = FTP(FTP_AUTH.host, FTP_AUTH.user, FTP_AUTH.password)
    elife_ftp.cwd(HOME)
    return elife_ftp

if __name__ == "__main__":
    HOME = "/"
    ftp = setup_ftp()
    all_ftp_files = ftp.nlst()
    current_file_numbers = get_current_file_numbers()

    # Add options
    parser = OptionParser()
    parser.add_option("-l", "--list", action="store_true", dest="list", help="lists new files to be retreived from ftp server", default="true")
    parser.add_option("-g", "--get", action="store_false", dest="list", help="retreives new files from ftp server")
    (options, args) = parser.parse_args()
    if options.list: 
        print "I'm going to list the files"
        new_files = list_new_ftp_files(all_ftp_files, current_file_numbers)
        print new_files 
    else:
        print "I'm going to get the files"
        new_files = list_new_ftp_files(all_ftp_files, current_file_numbers)
        print new_files 
        retreive_files(ftp, HOME, new_files)
        print "files retrieved"
