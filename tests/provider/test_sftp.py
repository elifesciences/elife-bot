import unittest
from mock import patch
from provider import sftp as sftp_provider
from tests.activity.classes_mock import FakeLogger


class FakeSftpClient:
    def mkdir(self, *args):
        pass

    def put(self, *args):
        pass


class FakeParamikoSession:
    "partial SFTP session to help run tests, test mocks mean send() and recv() are not needed"

    def invoke_subsystem(self, *args):
        pass

    def get_name(self):
        pass


class FakeParamikoTransport:
    "mock object for paramiko.Transport"

    def __init__(self, *args):
        pass

    def connect(self, **kwargs):
        pass

    def open_session(self, **kwargs):
        return FakeParamikoSession()

    def close(self):
        pass


class TestSftpConnect(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.sftp_instance = sftp_provider.SFTP(self.logger)

    @patch("paramiko.sftp.BaseSFTP._send_version")
    @patch("paramiko.sftp.BaseSFTP._read_packet")
    @patch("paramiko.Transport")
    def test_sftp_connect(
        self, fake_paramiko_transport, fake_read_packet, fake_send_version
    ):
        fake_paramiko_transport.return_value = FakeParamikoTransport()
        fake_read_packet.return_value = True
        fake_send_version.return_value = True
        self.assertIsNotNone(
            self.sftp_instance.sftp_connect("sftp.example.org", None, None)
        )

    @patch.object(FakeParamikoTransport, "connect")
    @patch("paramiko.Transport")
    def test_sftp_connect_exception(self, fake_paramiko_transport, fake_connect):
        fake_paramiko_transport.return_value = FakeParamikoTransport()
        fake_connect.side_effect = Exception("An exception")
        self.sftp_instance.sftp_connect("sftp.example.org", None, None)
        self.assertEqual(
            self.logger.loginfo[-1], "was unable to connect to SFTP server"
        )


class TestSftpToEndpoint(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.sftp_instance = sftp_provider.SFTP(self.logger)

    def test_sftp_to_endpoint(self):
        upload_files = ["file.txt"]
        self.sftp_instance.sftp_to_endpoint(FakeSftpClient(), upload_files)
        self.assertEqual(
            self.logger.loginfo[-1],
            "putting file by sftp %s to remote_file %s"
            % (upload_files[0], upload_files[0]),
        )

    def test_sftp_to_endpoint_subdirs(self):
        "test supplying a remote current directory and sub_dir folder"
        upload_files = ["file.txt"]
        remote_cwd = "remote_cwd"
        sub_dir = "sub_dir"
        self.sftp_instance.sftp_to_endpoint(
            FakeSftpClient(), upload_files, remote_cwd, sub_dir
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "putting file by sftp %s to remote_file %s/%s/%s"
            % (upload_files[0], remote_cwd, sub_dir, upload_files[0]),
        )

    @patch.object(FakeSftpClient, "mkdir")
    def test_sftp_to_endpoint_ioerror(self, fake_mkdir):
        "test IOError exception when making a remote directory, assuming it already exists"
        fake_mkdir.side_effect = IOError("An exception")
        upload_files = ["file.txt"]
        remote_cwd = "remote_cwd"
        sub_dir = "sub_dir"
        self.sftp_instance.sftp_to_endpoint(
            FakeSftpClient(), upload_files, remote_cwd, sub_dir
        )
        self.assertEqual(
            self.logger.loginfo[-1],
            "putting file by sftp %s to remote_file %s/%s/%s"
            % (upload_files[0], remote_cwd, sub_dir, upload_files[0]),
        )


class TestSftpDisconnect(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.sftp_instance = sftp_provider.SFTP(self.logger)
        self.sftp_instance.transport = FakeParamikoTransport()

    def test_sftp_disconnect(self):
        self.sftp_instance.disconnect()
        self.assertEqual(
            self.logger.loginfo[-1], "Closed transport connection in SFTP provider"
        )

    @patch.object(FakeParamikoTransport, "close")
    def test_sftp_disconnect_exception(self, fake_close):
        fake_close.side_effect = Exception("An exception")
        self.sftp_instance.disconnect()
        self.assertEqual(
            self.logger.logexception,
            "Failed to close the transport connection in SFTP provider: An exception",
        )
