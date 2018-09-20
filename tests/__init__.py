"helper functions for running tests"
import os
import importlib

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

def fixture_path_parts(path_parts):
    "extract non-empty values from the path folders"
    return [part for part in path_parts if part is not None and part != '']

def fixture_module_name(filename, folder_name=''):
    "concatenate a module name for importing for the fixture"
    return '.'.join(fixture_path_parts(
        ["tests", "fixtures", folder_name, filename.rstrip('.py')]))

def fixture_file(filename, folder_name=''):
    "return the path of a file fixture to be read"
    if filename is None:
        return None
    return os.path.join(BASE_DIR, "tests", "fixtures", folder_name, filename)

def read_fixture(filename, folder_name=''):
    "read a file from the fixtures directory"
    full_filename = fixture_file(filename, folder_name)
    if full_filename.endswith('.py'):
        # import the fixture and return the value of expected
        module_name = fixture_module_name(filename, folder_name)
        mod = importlib.import_module(module_name)
        # assert expected exists before continuing
        assert hasattr(mod, 'EXPECTED'), (
            'expected property not found in module {module_name}'.format(module_name=module_name))
        return mod.EXPECTED
    else:
        with open(full_filename, 'rb') as file_fp:
            return file_fp.read()
