from lettuce import *
import activity
import json


@step('I have the date format (\S+)')
def have_the_date_format(step, date_format):
    world.date_format = date_format
    assert world.date_format is not None, \
        "Got date_format %s" % world.date_format
