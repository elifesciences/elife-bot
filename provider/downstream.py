from collections import OrderedDict
from provider import outbox_provider


def workflow_s3_bucket_folder_map(rules):
    "return a map of workflow name to s3_bucket_folder from the YAML file rules"
    folder_map = OrderedDict()
    for workflow_name in rules:
        if rules.get(workflow_name) and rules.get(workflow_name).get(
            "s3_bucket_folder"
        ):
            folder_map[workflow_name] = rules.get(workflow_name).get("s3_bucket_folder")
    return folder_map


def workflow_outbox(downstream_workflow_map, workflow_name):
    "get the outbox folder for the workflow name from the map"
    return outbox_provider.outbox_folder(
        outbox_provider.workflow_foldername(workflow_name, downstream_workflow_map)
    )


def choose_outboxes(
    status,
    first_by_status,
    rules,
    run_type=None,
    article_profile_type=None,
):
    outbox_list = []

    if not rules:
        return outbox_list

    downstream_workflow_map = workflow_s3_bucket_folder_map(rules)

    for workflow in rules.keys():
        workflow_rules = rules.get(workflow)
        # check if the workflow should be scheduled by this activity
        if not workflow_rules:
            # no rules to check
            continue
        if not workflow_rules.get("schedule_downstream"):
            # do not assess for sending by this activity
            continue
        if (
            article_profile_type
            and workflow_rules.get("do_not_schedule")
            and article_profile_type in workflow_rules.get("do_not_schedule")
        ):
            # do not schedule it for downstream delivery for the article type
            continue

        if run_type == "silent-correction" and not workflow_rules.get(
            "schedule_silent_correction"
        ):
            # do not send
            continue

        if not first_by_status and workflow_rules.get("schedule_first_version_only"):
            # do not send
            continue

        if workflow_rules.get("schedule_article_types"):
            if status in workflow_rules.get("schedule_article_types", []):
                # add it to the outbox
                outbox_list.append(workflow_outbox(downstream_workflow_map, workflow))

    return outbox_list
