import os
import ftplib

"""

"""

class FTP(object):

    def __init__(self, logger=None):
        self.logger = logger

    def ftp_connect(self, uri, username, password, passive=True):
        """
        Connect to FTP server
        """
        ftp_instance = ftplib.FTP()
        if passive is False:
            ftp_instance.set_pasv(False)
        ftp_instance.connect(uri)
        ftp_instance.login(username, password)
        return ftp_instance

    def ftp_disconnect(self, ftp_instance):
        """
        Disconnect from FTP server
        """
        ftp_instance.quit()

    def ftp_upload(self, ftp_instance, filename):
        ext = os.path.splitext(filename)[1]
        #print filename
        uploadname = filename.split(os.sep)[-1]
        if ext in (".txt", ".htm", ".html"):
            ftp_instance.storlines("STOR " + filename, open(filename))
        else:
            #print "uploading " + uploadname
            ftp_instance.storbinary("STOR " + uploadname, open(filename, "rb"), 1024)
            #print "uploaded " + uploadname

    def ftp_cwd_mkd(self, ftp_instance, sub_dir):
        """
        Given an FTP connection and a sub_dir name
        try to cwd to the directory. If the directory
        does not exist, create it, then cwd again
        """
        cwd_success = None
        try:
            ftp_instance.cwd(sub_dir)
            cwd_success = True
        except ftplib.error_perm:
            # Directory probably does not exist, create it
            ftp_instance.mkd(sub_dir)
            cwd_success = False
        if cwd_success is not True:
            ftp_instance.cwd(sub_dir)
        return cwd_success

    def ftp_to_endpoint(self, ftp_instance, uploadfiles, sub_dir_list=None):
        for uploadfile in uploadfiles:
            self.ftp_cwd_mkd(ftp_instance, "/")
            if sub_dir_list is not None:
                for sub_dir in sub_dir_list:
                    self.ftp_cwd_mkd(ftp_instance, sub_dir)
            self.ftp_upload(ftp_instance, uploadfile)
