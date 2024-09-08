import importlib
import sys
import traceback
import types
from fastapi import APIRouter
import asyncio
from core.plugin_base import PluginBase
from utils.config_manager.config_model import Plugins
from core.action_interactions.action_base import ActionBase

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
        """
        Load plugins based on the configuration.
        If `LOAD_ACTIONS_FROM_BACKEND` is True, custom actions will be loaded from the backend folder via the dispatcher.
        Otherwise, actions are loaded from the plugin folders.
        """
        loaded_actions = []  # List to keep track of successfully loaded actions

        if self.global_manager.bot_config.LOAD_ACTIONS_FROM_BACKEND:
            self.logger.info("Loading custom actions from backend using the dispatcher...")

            # Planifier la tâche asynchrone sans utiliser asyncio.run() pour éviter l'erreur
            asyncio.ensure_future(self._load_custom_actions_from_backend(loaded_actions))
        else:
            # Classic loading from plugin folders
            self.logger.info("Loading plugins and actions from plugin folders...")
            for category, subcategories in self.plugin_configs.model_dump().items():
                for subcategory, plugins in subcategories.items():
                    for plugin_name, plugin_config in plugins.items():
                        plugin_dir = category + '.' + subcategory
                        self.logger.debug(f"Attempting to load plugin '{plugin_name}' from '{plugin_dir}'...")

                        try:
                            plugin_class = self.get_plugin(plugin_name=plugin_name.lower(), subdirectory=plugin_dir.lower())

                            if hasattr(plugin_class, '__abstractmethods__') and plugin_class.__abstractmethods__:
                                self.logger.error(f"Class '{plugin_class.__name__}' has not implemented all abstract methods: {', '.join(plugin_class.__abstractmethods__)}")
                                continue

                            # Add the plugin to the list of loaded plugins
                            loaded_actions.append(plugin_name)
                        
                        except Exception as e:
                            self.logger.error(f"Error while loading plugin '{plugin_name}' from '{plugin_dir}': {e}")

            # Log the loaded plugins and actions
            if loaded_actions:
                self.logger.info(f"Plugins and actions loaded from plugin folders: {', '.join(loaded_actions)}")
            else:
                self.logger.info("No plugins or actions were loaded from the plugin folders.")

    async def _load_custom_actions_from_backend(self, loaded_actions):
        """
        Load custom actions asynchronously from the backend storage using the dispatcher.
        """
        custom_actions_container = "custom_actions"
        self.logger.debug(f"Listing custom action files from backend container '{custom_actions_container}'...")

        try:
            custom_actions_files = await self.global_manager.backend_internal_data_processing_dispatcher.list_container_files(
                custom_actions_container
            )

            if not custom_actions_files:
                self.logger.warning(f"No custom action files found in backend container '{custom_actions_container}'.")
            else:
                self.logger.info(f"Found {len(custom_actions_files)} custom action files in backend container.")

            for action_file in custom_actions_files:
                self.logger.debug(f"Reading custom action file '{action_file}' from backend...")

                action_content = await self.global_manager.backend_internal_data_processing_dispatcher.read_data_content(
                    custom_actions_container, f"{action_file}.py"
                )

                if action_content:
                    self.logger.debug(f"Successfully read content of custom action file '{action_file}'")
                    self._load_custom_action_from_content(action_file, action_content)
                    loaded_actions.append(action_file)
                else:
                    self.logger.warning(f"Failed to read content for action file '{action_file}' from backend.")
        
        except Exception as e:
            self.logger.error(f"Error while loading custom actions from backend: {e}")

        # Log the list of loaded actions in one info log
        if loaded_actions:
            self.logger.info(f"Custom actions loaded from backend: {', '.join(loaded_actions)}")
        else:
            self.logger.info("No custom actions were loaded from the backend.")
            
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

