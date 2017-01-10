import os
import json
import log

class NullRequiredDataException(Exception):
    pass

def get_starter_identity(name):
        return "starter_" + name + "." + str(os.getpid())


def get_starter_logger(set_level, identity, log_file="starter.log"):
        return log.logger(log_file, set_level, identity)


def set_workflow_information(name, workflow_version, child_policy, data, workflow_id_part,
                             extra="", start_to_close_timeout=str(60 * 30)):
        workflow_id = "%s_%s.%s" % (name, workflow_id_part, extra)
        workflow_name = name
        workflow_version = workflow_version
        child_policy = child_policy
        execution_start_to_close_timeout = start_to_close_timeout
        workflow_input = json.dumps(data, default=lambda ob: ob.__dict__)

        return workflow_id, \
               workflow_name, \
               workflow_version, \
               child_policy, \
               execution_start_to_close_timeout, \
               workflow_input