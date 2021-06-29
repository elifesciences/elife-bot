# coding=utf-8

import unittest
from collections import OrderedDict
from xml.etree.ElementTree import Element
from mock import patch
from elifearticle import parse
from elifearticle.article import Article, Contributor
from provider import software_heritage, utils


def pretty_string(bytes):
    return str(bytes).replace("\\n", "\n")


class TestSoftwareHeritageProviderMetadata(unittest.TestCase):
    def setUp(self):
        self.file_name = "elife-15747-v1-era.zip"
        self.article, error_count = parse.build_article_from_xml(
            "tests/test_data/elife-15747-v2.xml", detail="full"
        )

    def test_metadata_xml(self):
        description = "A description & 0 < 1."
        create_origin_url = "https://elifesciences.org/articles/15747/executable"
        expected_xml_string = b"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0" xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit">
    <title>Community-level cohesion without cooperation</title>
    <id>elife-15747-v1-era.zip</id>
    <swhdeposit:deposit>
        <swhdeposit:create_origin>
            <swhdeposit:origin url="https://elifesciences.org/articles/15747/executable"/>
        </swhdeposit:create_origin>
    </swhdeposit:deposit>
    <codemeta:description>A description &amp; 0 &lt; 1.</codemeta:description>
    <codemeta:referencePublication>
        <codemeta:name>Community-level cohesion without cooperation</codemeta:name>
        <codemeta:identifier>10.7554/eLife.15747</codemeta:identifier>
    </codemeta:referencePublication>
    <codemeta:license>
        <codemeta:url>http://creativecommons.org/licenses/by/4.0/</codemeta:url>
    </codemeta:license>
    <codemeta:author>
        <codemeta:name>Mikhail Tikhonov</codemeta:name>
        <codemeta:affiliation>Center of Mathematical Sciences and Applications, Harvard University, Cambridge, United States</codemeta:affiliation>
        <codemeta:affiliation>Harvard John A Paulson School of Engineering and Applied Sciences, Harvard University, Cambridge, United States</codemeta:affiliation>
        <codemeta:affiliation>Kavli Institute for Bionano Science and Technology, Harvard University, Cambridge, United States</codemeta:affiliation>
    </codemeta:author>
</entry>
"""
        metadata_object = software_heritage.metadata(self.file_name, self.article)
        metadata_object.codemeta["description"] = description
        metadata_object.swhdeposit["deposit"]["create_origin"][
            "url"
        ] = create_origin_url
        metadata_element = software_heritage.metadata_element(metadata_object)
        metadata_xml = software_heritage.metadata_xml(
            metadata_element, pretty=True, indent="    "
        )
        self.assertEqual(
            metadata_xml,
            expected_xml_string,
            "\n\n%s\n\nis not equal to expected\n\n%s"
            % (
                pretty_string(metadata_xml),
                pretty_string(expected_xml_string),
            ),
        )

    def test_metadata_xml_not_pretty(self):
        "test for non-pretty XML output"
        element = Element("root")
        expected = b'<?xml version="1.0" encoding="utf-8"?><root/>'
        self.assertEqual(software_heritage.metadata_xml(element), expected)

    def test_metadata_xml_contrib_collab(self):
        "test for group authors in collab tags and group member contributors"
        collab_contributor = Contributor("author", "", "", "Test Research Group")
        collab_contributor.group_author_key = "group1"
        group_member = Contributor("author", "Smith", "Chris")
        group_member.group_author_key = "group1"
        self.article.contributors.append(collab_contributor)
        self.article.contributors.append(group_member)
        metadata_object = software_heritage.metadata(self.file_name, self.article)
        expected = [
            OrderedDict(
                [
                    ("name", "Mikhail Tikhonov"),
                    (
                        "affiliations",
                        [
                            "Center of Mathematical Sciences and Applications, Harvard University, Cambridge, United States",
                            "Harvard John A Paulson School of Engineering and Applied Sciences, Harvard University, Cambridge, United States",
                            "Kavli Institute for Bionano Science and Technology, Harvard University, Cambridge, United States",
                        ],
                    ),
                ]
            ),
            OrderedDict([("name", "Test Research Group")]),
        ]
        self.assertEqual(metadata_object.codemeta["authors"], expected)


class TestSoftwareHeritageProviderReadme(unittest.TestCase):
    def test_readme(self):
        kwargs = {
            "article_title": "The eLife research article",
            "doi": "https://doi.org/10.7554/eLife.00666",
            "article_id": utils.pad_msid(666),
            "create_origin_url": "https://stencila.example.org/article-00666/",
            "content_license": "http://creativecommons.org/licenses/by/4.0/",
        }
        with open("tests/test_data/software_heritage/README.md", "r") as open_file:
            expected = open_file.read()
        readme_string = software_heritage.readme(kwargs)
        self.assertEqual(readme_string, expected)

    @patch.object(software_heritage, "Template")
    def test_readme_(self, mock_template):
        mock_template.return_value = None
        kwargs = {}
        readme_string = software_heritage.readme(kwargs)
        self.assertEqual(readme_string, "")
