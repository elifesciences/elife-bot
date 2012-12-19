from lettuce import world
import os
"""
Set world.basedir relative to this terrain.py file,
when running lettuce from this directory,
and add the directory it to the import path
"""
world.basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,world.basedir)