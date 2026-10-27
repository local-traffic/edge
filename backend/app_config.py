import yaml


def load_yaml_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f) or {}


def save_yaml_config(config_path: str, data: dict):
    with open(config_path, 'w') as f:
        yaml.dump(data, f)
