import os
import json
import log

def get_starter_identity(name):
        return "starter_" + name + "." + str(os.getpid())

def get_starter_logger(set_level, identity, log_file="starter.log"):
        return log.logger(log_file, set_level, identity)

def set_workflow_information(name, workflow_version, child_policy, data):
        publication_from = "lax" if 'requested_action' in data else 'website'
        workflow_id = "%s_%s.%s" % (name, data['article_id'], publication_from)
        workflow_name = name
        workflow_version = workflow_version
        child_policy = child_policy
        execution_start_to_close_timeout = str(60 * 30)
        workflow_input = json.dumps(data, default=lambda ob: ob.__dict__)

        return workflow_id, \
               workflow_name, \
               workflow_version, \
               child_policy, \
               execution_start_to_close_timeout, \
               workflow_input