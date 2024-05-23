import yaml


def load_config(settings, config_type="downstream_recipients"):
    # load config from the YAML file specified in the settings
    if config_type == "downstream_recipients":
        return load_yaml(settings.downstream_recipients_yaml)
    if config_type == "publication_email":
        return load_yaml(settings.publication_email_yaml)
    return None


def load_yaml(file_path):
    # load config from the file_path YAML file
    with open(file_path, "r", encoding="utf-8") as open_file:
        return yaml.load(open_file.read(), Loader=yaml.FullLoader)


def value_as_list(value):
    "cast the value as a list"
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return None
