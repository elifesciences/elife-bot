from lettuce import *
import os
import json
import decimal

@step('I get JSON from the document')
def get_JSON_from_the_document(step):
    f = open(world.document)
    world.json_string = f.read()
    f.close()
    #world.json_string = open(os.getcwd() + os.sep + world.document)
    assert world.json_string is not None, \
        "Got json_string %s" % world.json_string

@step('I parse the JSON string')
def parse_the_JSON_string(step):
    world.json = json.loads(world.json_string, parse_float = decimal.Decimal)
    assert world.json is not None, \
        "Got json %s" % json.dumps(world.json)
