from core.action_interactions.action_interactions_plugin_base import ActionInteractionsPluginBase
import types
import asyncio

class CustomActionsFromBackendPlugin(ActionInteractionsPluginBase):
    def initialize(self):
        """
        Standard initialize method that loads actions from the backend.
        """
        self.plugin_name = "custom_actions_from_backend"
        self.logger.info(f"Initializing actions for plugin {self.plugin_name} from backend.")
        
        # Call the async load_actions method using asyncio.run to handle it synchronously
        asyncio.create_task(self.load_actions())

    @property
    def plugin_name(self):
        # This is a required property to implement for the abstract class
        return "custom_actions_from_backend"
    
    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value


    async def load_actions(self):
        """
        Overrides load_actions to fetch actions from the backend using the dispatcher asynchronously.
        """
        loaded_actions = []
        custom_actions_container = "custom_actions"  # Backend container for custom actions

        self.logger.info(f"Fetching custom actions from backend container: {custom_actions_container}")

        try:
            # Fetch action files asynchronously from the backend
            custom_actions_files = await self.global_manager.backend_internal_data_processing_dispatcher.list_container_files(custom_actions_container)

            if not custom_actions_files:
                self.logger.warning(f"No custom actions found in backend container '{custom_actions_container}'")
            else:
                # Process each action file asynchronously
                for action_file in custom_actions_files:
                    # Read the action file content asynchronously from the backend
                    action_content = await self.global_manager.backend_internal_data_processing_dispatcher.read_data_content(custom_actions_container, f"{action_file}.py")
                    if action_content:
                        # Dynamically load the action module from the content
                        module = types.ModuleType(f"custom_action_{action_file}")
                        exec(action_content, module.__dict__)
                        # Process the loaded module to register actions
                        self._process_module(module, loaded_actions)
                    else:
                        self.logger.warning(f"Failed to load content for action file '{action_file}'")

        except Exception as e:
            self.logger.error(f"Error while loading actions from backend: {e}")

        # Log the loaded actions
        self._log_loaded_actions(loaded_actions)
