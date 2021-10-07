import logging
import log
import unittest

class TestLog(unittest.TestCase):
    def test_logger_creation_and_usage(self):
        logger = log.logger('worker.log', 'INFO', 'worker_123')
        self.assertIsInstance(logger, logging.Logger)
        logger.info("Test info message")
        logger.error("Test error message")

    def test_identity_generation(self):
        self.assertRegex(log.identity('worker'), r'^worker_[0-9]+$')

