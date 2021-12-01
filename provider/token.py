from collections import OrderedDict


def build_workflow_data(
    article_id, version, run, expanded_folder, status, update_date, run_type
):
    """create a dict of workflow_data from the supplied keyword arguments"""
    workflow_data = OrderedDict()
    workflow_data["article_id"] = article_id
    workflow_data["version"] = version
    workflow_data["run"] = run
    workflow_data["expanded_folder"] = expanded_folder
    workflow_data["status"] = status
    workflow_data["update_date"] = update_date
    workflow_data["run_type"] = run_type
    return workflow_data


def starter_message(
    article_id,
    version,
    run,
    expanded_folder,
    status,
    update_date,
    run_type,
    workflow_name,
):
    """create a dict for a workflow starter message"""
    starter_message_dict = OrderedDict()
    workflow_data = build_workflow_data(
        article_id, version, run, expanded_folder, status, update_date, run_type
    )
    starter_message_dict["workflow_name"] = workflow_name
    starter_message_dict["workflow_data"] = workflow_data
    return starter_message_dict
