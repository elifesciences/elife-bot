from lettuce import *
import importlib

@step('I see the string (.*)')
def i_see_the_string(step, string):
    # Remove new lines for when comparing
    if type(world.string) == unicode or type(world.string) == str:
        world.string = world.string.replace("\n", "\\n")
    # Convert our value to int if world string is int for comparison
    if type(world.string) == int:
        string = int(string)
        
    if string == "None":
        string = None
    if string == "True":
        string = True
    if string == "False":
        string = False
        
    assert world.string == string, "Got %s" % world.string