from datetime import datetime
from typing import List, Optional

from fastapi import BackgroundTasks

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions.reaction_base import ReactionBase
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from utils.config_manager.config_model import BotConfig


class UserInteractionsDispatcher(UserInteractionsPluginBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugins : List[UserInteractionsPluginBase] = []
        self.default_plugin_name = None
        self.default_plugin : Optional[UserInteractionsPluginBase] = None

    def initialize(self, plugins: List[UserInteractionsPluginBase] = None):
        # Access the event queue manager from the global manager
        if self.global_manager.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING:
            self.event_queue_manager = self.global_manager.interaction_queue_manager

        self.bot_config: BotConfig = self.global_manager.bot_config
        if not plugins:
            self.logger.error("No plugins provided for UserInteractionsDispatcher")
            return

        self.plugins = plugins

    def get_plugin(self, plugin_name=None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        # Ensure plugins is treated as a dictionary
        if isinstance(self.plugins, dict):
            for plugins_in_category in self.plugins.values():
                for plugin in plugins_in_category:
                    if plugin.plugin_name == plugin_name:
                        return plugin

        self.logger.error(f"UserInteractionsDispatcher: Plugin '{plugin_name}' not found, returning default plugin")

        # Return the default plugin if the requested one is not found
        if self.default_plugin:
            return self.default_plugin

        # Handle the case where no default plugin is set
        self.logger.error("No default plugin configured.")
        return None

    def set_default_plugin(self, plugin_name):
        self.default_plugin_name = plugin_name
        self.default_plugin = self.get_plugin(plugin_name)

    @property
    def plugins(self) -> List[UserInteractionsPluginBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[UserInteractionsPluginBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin : UserInteractionsPluginBase = self.get_plugin()
        plugin.plugin_name = value

    @property
    def route_path(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.route_path

    @property
    def route_methods(self, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.route_methods  # replace with your route methods

    @property
    def reactions(self, plugin_name = None) -> ReactionBase:
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.reactions  # replace with your reactions

    @reactions.setter
    def reactions(self, value: ReactionBase, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        plugin.reactions = value  # replace with your logic

    def validate_request(self, request, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.validate_request(request)

    def handle_request(self, request, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.handle_request(request)

    async def request_to_notification_data(self, event_data, plugin_name = None):
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.request_to_notification_data(event_data)

    def format_trigger_genai_message(self, event: IncomingNotificationDataBase = None, message = None, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.format_trigger_genai_message(message)

    async def process_event_data(self, event: IncomingNotificationDataBase, headers, raw_body_str, plugin_name = None):
        if event is not None:
            plugin_name = event.origin_plugin_name
        plugin : UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.process_event_data(event_data=event, headers=headers, raw_body_str=raw_body_str)

    async def fetch_conversation_history(
        self, event: IncomingNotificationDataBase, channel_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> List[IncomingNotificationDataBase]:
        """
        Fetch conversation history from the plugin for a given channel and thread.
        """
        plugin_name = event.origin_plugin_name
        plugin: UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return await plugin.fetch_conversation_history(event=event, channel_id=channel_id, thread_id=thread_id)

    def get_bot_id(self, plugin_name=None) -> str:
        """
        Get the bot ID from the plugin.
        """
        plugin: UserInteractionsPluginBase = self.get_plugin(plugin_name)
        return plugin.get_bot_id()

    async def remove_reaction_from_thread(self, channel_id: str, thread_id: str, reaction_name: str, plugin_name=None, is_replayed=False, background_tasks: BackgroundTasks = None):
        """
        Remove reaction from a thread using the specified plugin.
        If `is_replayed` is True, process it directly.
        If `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled and not replayed, enqueue the event or add it to background tasks.
        Otherwise, process it directly using the plugin.
        """
        if not is_replayed and self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING:
            # Build method parameters for queuing
            method_params = {
                "channel_id": channel_id,
                "thread_id": thread_id,
                "reaction_name": reaction_name,
                "plugin_name": plugin_name
            }

            # Use FastAPI background tasks if provided
            if background_tasks:
                background_tasks.add_task(self._remove_reaction_from_thread_background, method_params)
                self.logger.debug(f"Event 'remove_reaction_from_thread' added to background tasks with parameters: {method_params}")
            else:
                await self.event_queue_manager.add_to_queue("remove_reaction_from_thread", method_params)
                self.logger.debug(f"Event 'remove_reaction_from_thread' queued with parameters: {method_params}")
        else:
            # Process the event directly
            plugin: UserInteractionsPluginBase = self.get_plugin(plugin_name)
            return await plugin.remove_reaction_from_thread(channel_id, thread_id, reaction_name)

    async def _remove_reaction_from_thread_background(self, method_params):
        await self.remove_reaction_from_thread(
            channel_id=method_params['channel_id'],
            thread_id=method_params['thread_id'],
            reaction_name=method_params['reaction_name'],
            plugin_name=method_params['plugin_name'],
            is_replayed=True
        )

    async def send_message(self, message, event: IncomingNotificationDataBase, message_type=MessageType.TEXT, title=None, is_internal=False, show_ref=False, plugin_name=None, is_replayed=False, background_tasks: BackgroundTasks = None, action_ref=None):
        """
        Send a message using the specified plugin. If `is_replayed` is True, process it directly.
        If `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled and not replayed, enqueue the event or add it to background tasks.
        Otherwise, process it directly using the plugin.
        """
        self.logger.debug("Entering send_message method")
        try:
            if event is not None:
                if is_replayed == False:
                    # Get the session
                    session = await self.global_manager.session_manager.get_or_create_session(
                        event.channel_id, event.thread_id, enriched=True
                    )

                    interaction = {
                        "message": message,
                        "message_type": message_type.value,
                        "timestamp": datetime.now().isoformat(),
                        "action_ref": action_ref
                    }

                    # Search for the most recent assistant message
                    message_index = None
                    for idx in range(len(session.messages) - 1, -1, -1):
                        if session.messages[idx].get("role") == "assistant":
                            message_index = idx
                            break

                    if message_index is not None:
                        if is_internal:
                            # Add the interaction to mind_interactions in the correct assistant message
                            session.add_mind_interaction_to_message(message_index=message_index, interaction=interaction)
                        else:
                            # Add the interaction to user_interactions in the correct assistant message
                            session.add_user_interaction_to_message(message_index=message_index, interaction=interaction)

                    # Save the session after adding the interaction
                    await self.global_manager.session_manager.save_session(session)

                plugin_name = event.origin_plugin_name
                self.logger.debug(f"Event provided with origin_plugin_name: {plugin_name}")

                if not is_replayed and self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING and not show_ref:
                    self.logger.debug("Queuing the send_message event")
                    # Build method parameters for queuing
                    method_params = {
                        "message": message,
                        "event": event.to_dict(),
                        "message_type": message_type.value,
                        "title": title,
                        "is_internal": is_internal,
                        "show_ref": show_ref
                    }

                    # Enqueue the event in the InteractionQueueManager
                    await self.event_queue_manager.add_to_queue("send_message", method_params)
                    self.logger.debug(f"Event 'send_message' enqueued with parameters: {method_params}")
                else:
                    self.logger.debug("Processing the send_message event directly")
                    # Process the event directly if replayed
                    plugin = self.get_plugin(plugin_name)
                    result = await plugin.send_message(message=message, event=event, message_type=message_type, title=title, is_internal=is_internal, show_ref=show_ref)
                    self.logger.debug("send_message event processed directly")
                    return result
        except Exception as e:
            self.logger.error(f"Error in send_message: {e}")
            raise
        finally:
            self.logger.debug("Exiting send_message method")

    async def upload_file(self, event: IncomingNotificationDataBase, file_content, filename, title, is_internal=False, plugin_name=None, is_replayed=False, background_tasks: BackgroundTasks = None):
        if event is not None:
            plugin_name = event.origin_plugin_name

            if not is_replayed and self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING:
                method_params = {
                    "event": event.to_dict(),
                    "file_content": file_content,
                    "filename": filename,
                    "title": title,
                    "is_internal": is_internal
                }

                # Enqueue the event
                await self.event_queue_manager.add_to_queue("upload_file", method_params)
                self.logger.debug(f"Event 'upload_file' enqueued with parameters: {method_params}")
            else:
                # Process the event directly
                plugin = self.get_plugin(plugin_name)
                return await plugin.upload_file(event=event, file_content=file_content, filename=filename, title=title, is_internal=is_internal)


    async def _upload_file_background(self, method_params):
        event = IncomingNotificationDataBase.from_dict(method_params['event'])
        await self.upload_file(
            event=event,
            file_content=method_params['file_content'],
            filename=method_params['filename'],
            title=method_params['title'],
            is_internal=method_params['is_internal'],
            is_replayed=True
        )

    async def add_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name, plugin_name=None, is_replayed=False, background_tasks: BackgroundTasks = None):
        """
        Add a reaction using the specified plugin. If `is_replayed` is True, process it directly.
        If `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled and not replayed, enqueue the event or add it to background tasks.
        Otherwise, process it directly using the plugin.
        """
        if event is not None:
            plugin_name = event.origin_plugin_name

            if not is_replayed and self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING:
                method_params = {
                    "event": event.to_dict(),
                    "channel_id": channel_id,
                    "timestamp": timestamp,
                    "reaction_name": reaction_name
                }

                # Enqueue the event
                await self.event_queue_manager.add_to_queue("add_reaction", method_params)
                self.logger.debug(f"Event 'add_reaction' enqueued with parameters: {method_params}")
            else:
                # Process the event directly
                plugin = self.get_plugin(plugin_name)
                return await plugin.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=reaction_name)


    async def remove_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, reaction_name, plugin_name=None, is_replayed=False, background_tasks: BackgroundTasks = None):
        """
        Remove a reaction using the specified plugin. If `is_replayed` is True, process it directly.
        If `ACTIVATE_USER_INTERACTION_EVENTS_QUEUING` is enabled and not replayed, enqueue the event or add it to background tasks.
        Otherwise, process it directly using the plugin.
        """
        if event is not None:
            plugin_name = event.origin_plugin_name

            if not is_replayed and self.bot_config.ACTIVATE_USER_INTERACTION_EVENTS_QUEUING:
                method_params = {
                    "event": event.to_dict(),
                    "channel_id": channel_id,
                    "timestamp": timestamp,
                    "reaction_name": reaction_name
                }

                # Enqueue the event
                await self.event_queue_manager.add_to_queue("remove_reaction", method_params)
                self.logger.debug(f"Event 'remove_reaction' enqueued with parameters: {method_params}")
            else:
                # Process the event directly
                plugin = self.get_plugin(plugin_name)
                return await plugin.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=reaction_name)
