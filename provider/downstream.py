import yaml
from collections import OrderedDict


def load_config(settings):
    # load config from the YAML file specified in the settings
    return load_yaml(settings.downstream_recipients_yaml)


def load_yaml(file_path):
    # load config from the file_path YAML file
    with open(file_path, "r") as open_file:
        return yaml.load(open_file.read(), Loader=yaml.FullLoader)


def workflow_s3_bucket_folder_map(rules):
    "return a map of workflow name to s3_bucket_folder from the YAML file rules"
    folder_map = OrderedDict()
    for workflow_name in rules:
        if rules.get(workflow_name) and rules.get(workflow_name).get(
            "s3_bucket_folder"
        ):
            folder_map[workflow_name] = rules.get(workflow_name).get("s3_bucket_folder")
    return folder_map
