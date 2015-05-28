import feeds

def scrape(xml):

    res = feeds.scrape(xml, lambda x: x[0]['article'][0])

    return res

def main(args):
    xml = open(args[0], "r").read()
    print scrape(xml)

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])

