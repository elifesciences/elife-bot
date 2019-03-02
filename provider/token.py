from collections import OrderedDict


def build_workflow_data(**kwargs):
    """create a dict of workflow_data from the supplied keyword arguments"""
    workflow_data = OrderedDict()
    for data_property in ['article_id', 'version', 'run', 'expanded_folder', 'status',
                          'update_date', 'run_type']:
        workflow_data[data_property] = kwargs.get(data_property)
    return workflow_data


def starter_message(**kwargs):
    """create a dict for a workflow starter message"""
    starter_message = OrderedDict()
    workflow_data = build_workflow_data(**kwargs)
    starter_message['workflow_name'] = kwargs.get('workflow_name')
    starter_message['workflow_data'] = workflow_data
    return starter_message
