import yaml


def load_config(settings):
    # load config from the YAML file specified in the settings
    return load_yaml(settings.downstream_recipients_yaml)


def load_yaml(file_path):
    # load config from the file_path YAML file
    with open(file_path, "r", encoding="utf-8") as open_file:
        return yaml.load(open_file.read(), Loader=yaml.FullLoader)
