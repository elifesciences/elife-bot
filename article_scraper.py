__author__ = 'Luke Skibinski <l.skibinski@elifesciences.org>'
__copyright__ = 'eLife Sciences'
__licence__ = 'GNU General Public License (GPL)'

import os, glob
from elifetools import parseJATS as parser
from scraper.utils import fattrs

import logging

FORMAT = logging.Formatter("%(created)f - %(levelname)s - %(processName)s - %(name)s - %(message)s")
LOGFILE = "%s.log" % __file__

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

h = logging.FileHandler(LOGFILE)
h.setLevel(logging.INFO)
h.setFormatter(FORMAT)

logger.addHandler(h)

class ParserWrapper(object):
    def __init__(self, soup):
        self.soup = soup
        
    def __getattr__(self, attr):
        def awooga(*args,**kwargs):
            logger.warn('* WARNING: I have no attribute %s' % attr)
            return None
        return getattr(parser, attr, awooga)(self.soup)

def article_wrapper(path):
    soup = parser.parse_document(path)
    # return a wrapper around the parser module that injects the soup when a function is called
    return ParserWrapper(soup)

def unsupported():
    return '* not implemented *'

@fattrs('doc')
def article_list(doc):
    if os.path.isfile(doc):
        return [article_wrapper(doc)]
    elif os.path.isdir(doc):
        return map(article_wrapper, glob.glob(doc + "*.xml"))
    elif doc.startswith("<?xml"):
        return [ParserWrapper(parser.parse_xml(doc))]

@fattrs('parent as article')
def author_list(article):
    x = article.authors
    return x

#
#
#

DESCRIPTION = [
    ('article', {
        'iterable': article_list,
        'attrs': {
            'jcode': 'this.journal_id',
            'jtitle': 'this.journal_title',
            'jissn': 'this.journal_issn',

            'state': 'unsupported',

            'title': 'this.title',
            'title_short': 'unsupported',
            
            'slug': 'unsupported',
            'subtitle': 'unsupported',

            'type': 'this.article_type',
            'doi': 'this.doi',
            'ppub': 'unsupported',
            'epub': 'unsupported',
            'fpub': 'unsupported',

            'first_page': 'unsupported',
            'last_page': 'unsupported',
            'issue': 'unsupported',
            'volume': 'unsupported',

            'category_list': 'unsupported',
            'keyword_list': ('this.keyword_group', None, str),

            'version': 'unsupported'
        },
        'subs': [
            ('authors', {
                'iterable': author_list,
                'attrs': {
                    'first_name': 'this.given_names',
                    'last_name': 'this.surname',
                    'suffix': 'this.suffix',
                    'institution': 'this.institution',
                },
            }),
        ] # ends article.subs block
    }) # ends article block
]


def main(args):
    if not len(args) == 1:
        print 'Usage: python feeds.py <xml [dir|file]>'
        exit(1)
    docs_dir = args[0]
    print convert(docs_dir)

def convert(doc):
    import scraper
    mod = __import__(__name__)
    res = scraper.scrape(mod, doc=doc)
    import json
    return json.dumps(res, indent=4)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
