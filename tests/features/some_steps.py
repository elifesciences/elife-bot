from lettuce import *
import importlib

@step('I have the package name (\S+)')
def i_have_the_package_name(step, package_name):
  world.package_name = package_name
  assert world.package_name is not None, \
    "Got package_name %s" % world.package_name

@step('I import the package')
def i_import_the_package(step):
  imported = None
  try:
    world.package = importlib.import_module(world.package_name)
    imported = True
  except:
    imported = False
  assert imported is True, \
    "Package %s was imported" % world.package_name

@step('I get the package with name (\S+)')
def i_get_the_package_with_name(step, package_name):
  assert world.package.__name__ == package_name, \
    "Got package_name %s" % world.package.__name__