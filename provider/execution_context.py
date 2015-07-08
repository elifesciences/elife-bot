
class Session(object):

    # TODO : replace with better implementation - e.g. use Redis/Elasticache

    def __init__(self, settings):
        self.settings = settings

    def store_value(self, execution_id, key, value):
        f = open(self.settings.workflow_context_path + self.get_full_key(execution_id, key), 'w')
        f.write(value + '\n')

    def get_value(self, execution_id, key):
        f = open(self.settings.workflow_context_path + self.get_full_key(execution_id, key), 'r')
        return f.readline()

    @staticmethod
    def get_full_key(execution_id, key):
        return execution_id + '__' + key
