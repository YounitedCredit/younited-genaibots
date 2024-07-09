import importlib
import sys
import traceback

from fastapi import APIRouter

from core.plugin_base import PluginBase
from utils.config_manager.config_model import Plugins


class PluginManager:
    def __init__(self, base_directory, global_manager):
        # Import GlobalManager here instead
        from core.global_manager import GlobalManager
        if not isinstance(global_manager, GlobalManager):
            raise TypeError("global_manager must be an instance of GlobalManager")

        # Base directory where plugins are located
        self.base_directory = base_directory
        self.config_manager = global_manager.config_manager
        self.plugin_configs: Plugins = self.config_manager.config_model.PLUGINS
        self.global_manager = global_manager
        self.logger = global_manager.logger
        # Dictionary to store loaded plugins
        self.plugins = {}

    def load_plugins(self):
        for category, subcategories in self.plugin_configs.model_dump().items():
            for subcategory, plugins in subcategories.items():
                for plugin_name, plugin_config in plugins.items():

                    plugin_dir = category + '.' + subcategory
                    plugin_class = self.get_plugin(plugin_name=plugin_name.lower(), subdirectory=plugin_dir.lower())

                    if hasattr(plugin_class, '__abstractmethods__') and plugin_class.__abstractmethods__:
                        self.logger.error(f"Class '{plugin_class.__name__}' has not implemented all abstract methods: {', '.join(plugin_class.__abstractmethods__)}")
                        continue  # Skip this plugin and move to the next one

        self.logger.debug("initialize plugins...")

    def get_plugin_by_category(self, category, subcategory=None):
        # Check if the category exists in the plugins dictionary
        if category in self.plugins:
            # If a subcategory is provided, return the specific plugin
            if subcategory:
                # Check if the subcategory exists in the category dictionary
                if subcategory in self.plugins[category]:
                    # Return the plugin instance from the plugins dictionary
                    return self.plugins[category][subcategory]
                else:
                    # If the subcategory does not exist, log an error and return None
                    self.logger.error(f"Plugin not found for category '{category}' and subcategory '{subcategory}'")
                    return None
            else:
                # If no subcategory is provided, return all plugins in the category
                return self.plugins[category]

        # If the category does not exist, log an error and return None
        self.logger.error(f"Plugin not found for category '{category}'")
        return None

    def get_plugin(self, plugin_name, subdirectory):
        # Split the subdirectory into category and subcategory
        category, subcategory = subdirectory.split('.')
        # Construct the module name from the subdirectory and plugin name
        module_name = f"{subdirectory}.{plugin_name}.{plugin_name}"
        try:
            # Try to load the plugin
            plugin_instance = self.load_plugin(self.base_directory, module_name)
        except NotImplementedError as e:
            # Log the error and return None if the plugin fails to load
            self.logger.error(f"Failed to load plugin '{plugin_name}': {str(e)}")
            return None
        except Exception as e:
            # Log the error and return None if the plugin fails to load
            self.logger.error(f"Failed to load plugin '{plugin_name}': {str(e)}")
            return None

        # If the plugin is successfully loaded, add it to the plugins dictionary
        if plugin_instance:
            category_upper = category.upper()
            subcategory_upper = subcategory.upper()

            if category_upper not in self.plugins:
                self.plugins[category_upper] = {}

            # Check if the subcategory already exists
            if subcategory_upper not in self.plugins[category_upper]:
                # If it does not exist, create a new list with the plugin instance
                self.plugins[category_upper][subcategory_upper] = [plugin_instance]
            else:
                # If it exists, simply append the plugin instance to the existing list
                self.plugins[category_upper][subcategory_upper].append(plugin_instance)

        # Return the plugin instance
        return plugin_instance

    def load_plugin(self, plugin_dir, module_name):

        try:
            sys.path.insert(0, str(plugin_dir))
            mod = importlib.import_module(module_name)
            last_segment = module_name.split('.')[-1]
            camel_case_name = ''.join(word.capitalize() for word in last_segment.split('_'))
            expected_class_name = f"{camel_case_name}Plugin"

            # Iterate through attributes in the module and find the class that inherits from base_class_name
            for attribute_name in dir(mod):
                attribute = getattr(mod, attribute_name)
                if isinstance(attribute, type) and attribute.__name__ == expected_class_name and issubclass(attribute, PluginBase):
                    # Check if the class has implemented all the abstract methods
                    if attribute.__abstractmethods__:
                        self.logger.error(f"Class '{attribute.__name__}' has not implemented all abstract methods: {', '.join(attribute.__abstractmethods__)}")
                        return None
                    self.logger.debug(f"Plugin {module_name}.py installed")
                    if str(plugin_dir) in sys.path:
                        sys.path.remove(str(plugin_dir))
                    return attribute(self.global_manager)

            self.logger.error(f"No suitable class found in module '{module_name}'")
            return None

        except Exception as e:
            self.logger.error(f"Error loading plugin '{module_name}': {e}", exc_info=True)
            return None


    def initialize_plugins(self):
        for category, category_plugins in self.plugins.items():
            for plugin_type, plugins in category_plugins.items():
                for plugin in plugins:
                    try:
                        self.logger.info(f"Initializing <{category}> plugin <{plugin.__class__.__name__}>...")
                        plugin.initialize()
                    except Exception as e:
                        self.logger.error(f"An error occurred while initializing the plugin <{plugin.__class__.__name__}>: {str(e)}")
                        self.logger.error(traceback.format_exc())

    def intialize_routes(self, app):
        # Create a new APIRouter instance
        router = APIRouter()

        # Check if the "user_interactions" category exists in the plugins dictionary
        if "USER_INTERACTIONS" in self.plugins:
            # Iterate over all subcategories in the "user_interactions" category
            for subcategory in self.plugins["USER_INTERACTIONS"]:
                # Get the plugin instances
                plugin_instances = self.plugins["USER_INTERACTIONS"][subcategory]

                for plugin_instance in plugin_instances:
                    # Define the methods and path for the route from the plugin configuration
                    methods = plugin_instance.route_methods
                    path = plugin_instance.route_path

                    # Add the route to the router for each method
                    for method in methods:
                        # Convert the method to lowercase
                        method = method.lower()

                    # Add the route to the router
                    router.add_api_route(path, plugin_instance.handle_request, methods=[method])

                # Include the router in the FastAPI application
                app.include_router(router)
                self.logger.info(f"Route [{methods}] {path} set up with the user interactions plugin <{plugin_instance.__class__.__name__}>")

