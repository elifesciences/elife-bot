import paramiko
import os

"""

"""

class SFTP(object):

    def __init__(self, logger=None):
        paramiko.util.log_to_file('paramiko.log')
        self.logger = logger

    def sftp_connect(self, uri, username, password, port=22):
        """
        Connect to SFTP server without a host key
        """
        #print "trying to SFTP now"

        transport = paramiko.Transport((uri, port))

        try:
            transport.connect(hostkey=None,
                              username=username,
                              password=password)
        except:
            if self.logger:
                self.logger.info("was unable to connect to SFTP server")
            return None

        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp

    def sftp_to_endpoint(self, sftp_client, uploadfiles, sftp_cwd='', sub_dir=None):
        """
        Given a paramiko SFTP client, upload files to it
        """

        if sub_dir:
            # Making the sub directory if it does or does not exist
            absolute_sub_dir = sftp_cwd + '/' + sub_dir
            try:
                sftp_client.mkdir(absolute_sub_dir)
            except IOError:
                pass

        for uploadfile in uploadfiles:
            remote_file = uploadfile.split(os.sep)[-1]
            if sub_dir:
                remote_file = sub_dir + '/' + remote_file
            if sftp_cwd != '':
                remote_file = sftp_cwd + '/' + remote_file
            if self.logger:
                self.logger.info("putting file by sftp " + uploadfile +
                                 " to remote_file " + remote_file)
            result = sftp_client.put(uploadfile, remote_file)
