import scraper
import json
import feeds

def scrape(xml, status=1):

    res = scraper.scrape(feeds, doc=xml, status=status)

    return json.dumps(res[0]['article'][0], indent=4)

def main(args):
    xml = open(args[0], "r").read()
    print scrape(xml, status=1)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])

