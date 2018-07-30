from provider import imageresize, memory
from collections import namedtuple

source = 'scripts/elife-03318-fig2.tif'
format_spec = {'source': 'tif', 'format': 'jpg', 'download': 'yes'}
fp = open(source)
Info = namedtuple('Info', ['filename'])
info = Info('dummy.jpg')
before = memory.current()
imageresize.resize(format_spec, fp, info, None)
after = memory.current()
print("Before: %s" % before)
print("After: %s" % after)
print("Memory delta: %s" % (after - before))

