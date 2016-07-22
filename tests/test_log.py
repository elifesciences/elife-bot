import logging
import log
import unittest

class TestLog(unittest.TestCase):
    def test_logger_creation(self):
        logger = log.logger('worker.log', 'INFO', 'worker_123')
        self.assertIsInstance(logger, logging.Logger)

    def test_identity_generation(self):
        self.assertRegexpMatches(log.identity('worker'), '^worker_[0-9]+$')

