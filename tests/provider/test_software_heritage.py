# coding=utf-8

import unittest
from xml.etree.ElementTree import Element
from elifearticle import parse
from elifearticle.article import Article
import provider.software_heritage as software_heritage


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
