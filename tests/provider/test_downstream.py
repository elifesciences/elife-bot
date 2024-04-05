import unittest
from collections import OrderedDict
from provider import downstream
from tests import settings_mock


class TestLoadConfig(unittest.TestCase):
    def test_load_config(self):
        rules = downstream.load_config(settings_mock)
        self.assertTrue(isinstance(rules, dict))


class TestFolderMap(unittest.TestCase):
    def test_workflow_s3_bucket_folder_map(self):
        rules = downstream.load_config(settings_mock)
        folder_map = downstream.workflow_s3_bucket_folder_map(rules)
        self.assertTrue(isinstance(folder_map, OrderedDict))


class TestChooseOutboxes(unittest.TestCase):
    def setUp(self):
        self.rules = downstream.load_config(settings_mock)

    def test_empty_rules(self):
        rules = None
        outbox_list = downstream.choose_outboxes("vor", True, rules)
        self.assertEqual(outbox_list, [])

    def test_empty_workflow_rules(self):
        rules = {"HEFCE": {}}
        outbox_list = downstream.choose_outboxes("vor", True, rules)
        self.assertEqual(outbox_list, [])

    def test_choose_outboxes_poa_first(self):
        "first poa version"
        outbox_list = downstream.choose_outboxes("poa", True, self.rules)
        # schedule the following
        for folder_name in [
            "ovid",
            "publication_email",
            "pubmed",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

        # do not schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "crossref",
            "gooa",
            "oaswitchboard",
            "pmc",
            "pub_router",
            "wos",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_poa_not_first(self):
        "poa but not the first poa"
        outbox_list = downstream.choose_outboxes("poa", False, self.rules)
        # schedule the following
        for folder_name in [
            "ovid",
            "pubmed",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnpiec",
            "cnki",
            "crossref",
            "gooa",
            "oaswitchboard",
            "pmc",
            "pub_router",
            "publication_email",
            "wos",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_first(self):
        "first vor version"
        outbox_list = downstream.choose_outboxes("vor", True, self.rules)
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "oaswitchboard",
            "ovid",
            "pmc",
            "pub_router",
            "publication_email",
            "pubmed",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_not_first(self):
        "vor but not the first vor"
        outbox_list = downstream.choose_outboxes("vor", False, self.rules)
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "pubmed",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )

        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_silent_first(self):
        outbox_list = downstream.choose_outboxes(
            "vor", True, self.rules, "silent-correction"
        )
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
            "pubmed",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )

    def test_choose_outboxes_vor_silent_not_first(self):
        "silent correction vor but not the first vor"
        outbox_list = downstream.choose_outboxes(
            "vor", False, self.rules, "silent-correction"
        )
        # schedule the following
        for folder_name in [
            "cengage",
            "clockss",
            "cnki",
            "cnpiec",
            "gooa",
            "ovid",
            "pmc",
            "pub_router",
            "wos",
            "zendy",
        ]:
            self.assertTrue(
                "%s/outbox/" % folder_name in outbox_list,
                "did not find %s folder" % folder_name,
            )
        # do not schedule the following
        for folder_name in [
            "oaswitchboard",
            "publication_email",
            "pubmed",
        ]:
            self.assertFalse(
                "%s/outbox/" % folder_name in outbox_list,
                "unexpectedly found %s folder" % folder_name,
            )
