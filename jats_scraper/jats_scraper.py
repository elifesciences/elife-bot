import feeds

def scrape(xml, article_version=None):

    res = feeds.scrape(xml, lambda x: x[0]['article'][0], article_version)

    return res

def main(args):
    xml = open(args[0], "r").read()
    print scrape(xml)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])

