from provider import imageresize, memory
from collections import namedtuple

source = '/home/giorgio/code/elife-spectrum/spectrum/templates/elife-03318-vor-r1/elife-03318-fig2.tif'
format_spec = {'source': 'tif', 'format': 'jpg', 'download': 'yes'}
fp = open(source)
Info = namedtuple('Info', ['filename'])
info = Info('dummy.jpg')
print(memory.current())
imageresize.resize(format_spec, fp, info, None)
print(memory.current())

