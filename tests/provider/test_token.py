# coding=utf-8

import unittest
from collections import OrderedDict
from provider import token


class TestTokenProvider(unittest.TestCase):

    def setUp(self):
        self.article_id = 'article_id'
        self.version = 'version'
        self.run = 'run'
        self.expanded_folder = 'expanded_folder'
        self.status = 'status'
        self.update_date = 'update_date'
        self.run_type = 'run_type'

    def expected_workflow_data(self):
        """for reuse in tests some expected workflow data"""
        return OrderedDict([
            ('article_id', self.article_id),
            ('version', self.version),
            ('run', self.run),
            ('expanded_folder', self.expanded_folder),
            ('status', self.status),
            ('update_date', self.update_date),
            ('run_type', self.run_type),
        ])

    def test_build_workflow_data(self):
        """test building workflow data"""
        expected = self.expected_workflow_data()
        workflow_data = OrderedDict([
            ('article_id', self.article_id),
            ('version', self.version),
            ('run', self.run),
            ('expanded_folder', self.expanded_folder),
            ('status', self.status),
            ('update_date', self.update_date),
            ('run_type', self.run_type),
        ])
        self.assertEqual(workflow_data, expected)

    def test_starter_message(self):
        """test building a starter message with a workflow name and workflow data"""
        workflow_name = 'workflow_name'
        expected = OrderedDict([
            ('workflow_name', workflow_name),
            ('workflow_data', self.expected_workflow_data())
        ])
        starter_message = token.starter_message(
            article_id=self.article_id,
            version=self.version,
            run=self.run,
            expanded_folder=self.expanded_folder,
            status=self.status,
            update_date=self.update_date,
            run_type=self.run_type,
            workflow_name=workflow_name
        )
        self.assertEqual(starter_message, expected)
