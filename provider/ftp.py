import os
import ftplib


class FTP:
    def __init__(self, logger):
        self.logger = logger

    def ftp_connect(self, uri, username, password, passive=True):
        """
        Connect to FTP server
        """
        ftp_instance = ftplib.FTP()
        if passive is False:
            self.logger.info("Disabling passive mode in FTP")
            ftp_instance.set_pasv(False)
        self.logger.info("Connecting to FTP host %s" % uri)
        ftp_instance.connect(uri)
        self.logger.info("Logging in to FTP host %s" % uri)
        ftp_instance.login(username, password)
        return ftp_instance

    def ftp_disconnect(self, ftp_instance):
        """
        Disconnect from FTP server
        """
        self.logger.info("Disconnecting from FTP host %s" % ftp_instance.host)
        ftp_instance.quit()

    def ftp_upload(self, ftp_instance, filename):
        ext = os.path.splitext(filename)[1]
        self.logger.info("FTP uploading filename %s" % filename)
        uploadname = filename.split(os.sep)[-1]
        if ext in (".txt", ".htm", ".html"):
            ftp_instance.storlines("STOR " + uploadname, open(filename))
            self.logger.info(
                "Uploaded %s by storlines method to %s" % (filename, uploadname)
            )
        else:
            ftp_instance.storbinary("STOR " + uploadname, open(filename, "rb"), 1024)
            self.logger.info(
                "Uploaded %s by storbinary method to %s" % (filename, uploadname)
            )

    def ftp_cwd_mkd(self, ftp_instance, sub_dir):
        """
        Given an FTP connection and a sub_dir name
        try to cwd to the directory. If the directory
        does not exist, create it, then cwd again
        """
        try:
            ftp_instance.cwd(sub_dir)
            return
        except ftplib.error_perm:
            self.logger.exception(
                'Exception when changing working directory to "%s" at host %s'
                % (sub_dir, ftp_instance.host)
            )

        # Directory may not exist, create it
        try:
            ftp_instance.mkd(sub_dir)
            ftp_instance.cwd(sub_dir)
        except ftplib.error_perm:
            self.logger.exception(
                'Exception when creating directory "%s" at host %s'
                % (sub_dir, ftp_instance.host)
            )
            raise

    def ftp_to_endpoint(self, ftp_instance, uploadfiles, sub_dir_list=None):
        for uploadfile in uploadfiles:
            self.ftp_cwd_mkd(ftp_instance, "/")
            if sub_dir_list is not None:
                for sub_dir in sub_dir_list:
                    self.ftp_cwd_mkd(ftp_instance, sub_dir)
            self.ftp_upload(ftp_instance, uploadfile)
