from lettuce import *
import activity
import json


@step('I have the timestamp (\S+)')
def have_the_timestamp(step, timestamp):
    if(timestamp == "None"):
        world.timestamp = None
        assert world.timestamp is None, \
            "Got timestamp %s" % world.timestamp
    else:
        # Takes a float, apparently
        world.timestamp = float(timestamp)
        assert world.timestamp is not None, \
            "Got timestamp %f" % world.timestamp
