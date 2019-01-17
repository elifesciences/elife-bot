# coding=utf-8

import unittest
import copy
from collections import OrderedDict
from mock import patch
from ddt import ddt, data
from activity.activity_CreateDigestMediumPost import (
    activity_CreateDigestMediumPost as activity_object)
import provider.article as article
import provider.article_processing as article_processing
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext


ACTIVITY_DATA = {
    "run": "",
    "article_id": "99999",
    "version": "1",
    "status": "vor",
    "expanded_folder": "digests",
    "run_type": None
}


def digest_activity_data(data, status=None, run_type=None):
    new_data = copy.copy(data)
    if new_data and status:
        new_data["status"] = status
    if new_data and run_type:
        new_data["run_type"] = run_type
    return new_data


EXPECTED_MEDIUM_CONTENT = OrderedDict(
    [
        ('title', u'Fishing for errors in the\xa0tests'),
        ('contentFormat', 'html'),
        ('content', u'<h1>Fishing for errors in the\xa0tests</h1><h2>Testing a document which mimics the format of a file we’ve used \xa0before plus CO<sub>2</sub> and Ca<sup>2+</sup>.</h2><hr/><p>Microbes live in us and on us. They are tremendously important for our health, but remain difficult to understand, since a microbial community typically consists of hundreds of species that interact in complex ways that we cannot fully characterize. It is tempting to ask whether one might instead characterize such a community as a whole, treating it as a multicellular "super-organism". However, taking this view beyond a metaphor is controversial, because the formal criteria of multicellularity require pervasive levels of cooperation between organisms that do not occur in most natural communities.</p><p>In nature, entire communities of microbes routinely come into contact – for example, kissing can mix together the communities in each person’s mouth. Can such events be usefully described as interactions between community-level "wholes", even when individual bacteria do not cooperate with each other? And can these questions be asked in a rigorous mathematical framework?</p><p>Mikhail Tikhonov has now developed a theoretical model that shows that communities of purely "selfish" members may effectively act together when competing with another community for resources. This model offers a new way to formalize the "super-organism" metaphor: although individual members compete against each other within a community, when seen from the outside the community interacts with its environment and with other communities much like a single organism.</p><p>This perspective blurs the distinction between two fundamental concepts: competition and genetic recombination. Competition combines two communities to produce a third where species are grouped in a new way, just as the genetic material of parents is recombined in their offspring.</p><p>Tikhonov’s model is highly simplified, but this suggests that the "cohesion" seen when viewing an entire community is a general consequence of ecological interactions. In addition, the model considers only competitive interactions, but in real life, species depend on each other; for example, one organism\'s waste is another\'s food. A natural next step would be to incorporate such cooperative interactions into a similar model, as cooperation is likely to make community cohesion even stronger.</p>'),
        ('tags', [
            'Face Recognition', 'Neuroscience', 'Vision']
        ),
        ('license', 'cc-40-by')
    ]
)


@ddt
class TestCreateDigestMediumPost(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(article_processing, 'storage_context')
    @patch.object(article, 'storage_context')
    @patch('activity.activity_CreateDigestMediumPost.storage_context')
    @patch.object(activity_object, 'emit_monitor_event')
    @data(
        {
            "comment": "",
            "bucket_resources": ["elife-15747-v2.xml"],
            "bot_bucket_resources": ["digests/outbox/99999/digest-99999.docx",
                                     "digests/outbox/99999/digest-99999.jpg"],
        },
    )
    def test_do_activity(self, test_data, fake_emit, fake_storage_context,
                         fake_article_storage_context, fake_processing_storage_context):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        activity_data = digest_activity_data(
            ACTIVITY_DATA
            )
        named_storage_context = FakeStorageContext()
        if test_data.get('bucket_resources'):
            named_storage_context.resources = test_data.get('bucket_resources')
        fake_article_storage_context.return_value = named_storage_context
        bot_storage_context = FakeStorageContext()
        if test_data.get('bot_bucket_resources'):
            bot_storage_context.resources = test_data.get('bot_bucket_resources')
        fake_storage_context.return_value = bot_storage_context
        fake_processing_storage_context.return_value = FakeStorageContext()
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)
        self.assertEqual(self.activity.medium_content, EXPECTED_MEDIUM_CONTENT)


if __name__ == '__main__':
    unittest.main()
