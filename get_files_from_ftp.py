import glob
from ftplib import FTP
from collections import namedtuple

current_xml_path = "/Users/ian/code/public-code/elife-articles"

# pull in credentials

ftp_auth_info = "/Users/ian/code/private-code/elife-api-workflow/ftp-credentials.txt"
FtpKeys = namedtuple('Keys', "host user password")

def get_value_from_line(line):
    value = line.split(":")[1].strip()
    return value 

def get_keys(keys_file, myTuple):
    lines = open(keys_file, 'r').readlines()
    values = []
    expected_number_of_fields = len(myTuple._fields)
    for i in range(expected_number_of_fields):
        part = get_value_from_line(lines[i])
        values.append(part)
    thisTuple = myTuple._make(values)
    return thisTuple
    
FtpAuth = get_keys(ftp_auth_info, FtpKeys)

# do stuff

def download_cb(block):
    file.write(block)

def get_current_files():
    current_files = glob.glob(current_xml_path + "/*.xml")
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
    for f in files:
        ftp.cwd(f)
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

home = "/For PMC/"
ftp = FTP(FtpAuth.host, FtpAuth.user, FtpAuth.password)
ftp.cwd(home)

all_ftp_files = ftp.nlst()
current_file_numbers = get_current_file_numbers()

new_files = list_new_ftp_files(all_ftp_files, current_file_numbers)
print new_files 
retreive_files(ftp, home, new_files)
