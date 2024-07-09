import os

import yaml

from .config_model import ConfigModel, Plugin


class ConfigManager:
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        # Get the configuration file path from the environment variable or use a default value
        self.global_manager: GlobalManager = global_manager
        self.config_path = os.getenv('CONFIG_FILE_PATH', 'config.yaml')

        try:
            # Load the configuration from the file
            with open(self.config_path, 'r') as config_file:
                self.config = yaml.safe_load(config_file)
        except FileNotFoundError:
            self.config = {}
            raise FileNotFoundError(f"Configuration file '{self.config_path}' not found.")

        self.config = self.replace_env_vars(self.config)

        if 'BOT_CONFIG' not in self.config:
            self.config['BOT_CONFIG'] = {'LOG_DEBUG_LEVEL': 'DEBUG'}

        if 'LOG_DEBUG_LEVEL' not in self.config['BOT_CONFIG']:
            raise KeyError("Missing field in config.yaml: BOT_CONFIG.LOG_DEBUG_LEVEL")

        # Handle empty plugin categories gracefully
        for plugin_category in self.config.get('PLUGINS', {}).keys():
            if plugin_category not in self.config['PLUGINS']:
                self.config['PLUGINS'][plugin_category] = {}

            for plugin_subcategory in self.config['PLUGINS'][plugin_category].keys():
                if plugin_subcategory not in self.config['PLUGINS'][plugin_category]:
                    self.config['PLUGINS'][plugin_category][plugin_subcategory] = {}

        self.config_model = ConfigModel(**self.config)
        self.load_action_interactions()

    def load_action_interactions(self):
        # Get the action interactions configuration
        action_interactions_config = self.config['PLUGINS'].get('ACTION_INTERACTIONS', {})

        # Iterate over the DEFAULT and CUSTOM configurations
        for category in ['DEFAULT', 'CUSTOM']:
            category_config = action_interactions_config.get(category, {})

            # Iterate over the plugins in the category
            for plugin_name, plugin_config in category_config.items():
                # Create an instance of the plugin
                plugin = Plugin(**plugin_config)

                # Add the plugin to the ActionInteractions instance
                getattr(self.config_model.PLUGINS.ACTION_INTERACTIONS, category)[plugin_name] = plugin

    def replace_env_vars(self, value):
        if isinstance(value, str) and value.startswith("$(") and value.endswith(")"):
            env_var = value[2:-1]
            if env_var not in os.environ:
                raise ValueError(f"Environment variable {env_var} not found")
            return os.environ.get(env_var)
        elif isinstance(value, dict):
            return {k: self.replace_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.replace_env_vars(v) for v in value]
        else:
            return value

    def get_config(self, keys, default=None):
        try:
            # Navigate the config model using the keys
            value = self.config_model
            for key in keys:
                if hasattr(value, key):
                    value = getattr(value, key)
                else:
                    raise KeyError(f"Key '{key}' not found in configuration at {'.'.join(keys)}")  # Include the full path of the key in the error message


            # If the value is a string of the form "$(ENV_VAR)", get the environment variable
            if isinstance(value, str) and value.startswith("$(") and value.endswith(")"):
                env_var = value[2:-1]

                if env_var in os.environ:
                    return os.environ[env_var]
                else:
                    raise KeyError(f"Environment variable '{env_var}' not found.")  # Raise KeyError if the environment variable is not found

            return value
        except Exception as e:
            print(f"Failed to get configuration value: {e}")
            raise
