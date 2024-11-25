import copy

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import IncomingNotificationDataBase
from core.user_interactions.message_type import MessageType
from core.user_interactions.user_interactions_dispatcher import UserInteractionsDispatcher
class UserInteraction(ActionBase):
    REQUIRED_PARAMETERS = ['value']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher : UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input : ActionInput, event: IncomingNotificationDataBase):
        parameters = action_input.parameters
        value = parameters.get('value')
        channel_id = parameters.get('channelid', None)
        thread_id = parameters.get('threadid', None)
        as_file = parameters.get('AsFile', False)
        title = parameters.get('title', "file_upload.txt")
        
        event_copy = copy.deepcopy(event)
        is_custom_target = False
        if channel_id and channel_id.lower() != "none":
            event_copy.channel_id = channel_id
            is_custom_target = True

        if thread_id and channel_id.lower() != "none":
            is_custom_target = True
            if thread_id.lower() == "none":
                event_copy.thread_id = ""
                event_copy.timestamp = ""
                event_copy.response_id = ""
            else:
                event_copy.thread_id = thread_id

        message = value if value else ''
        if not message:
            raise ValueError("Empty message")
        else:
            if as_file:
                if is_custom_target:
                    await self.user_interactions_dispatcher.upload_file(event=event_copy, file_content=message, filename=title, title=title)
                else:
                    await self.user_interactions_dispatcher.upload_file(event=event, file_content=message, filename=title, title=title)
            else:
                if is_custom_target:
                    await self.user_interactions_dispatcher.send_message(event=event_copy, message=message, message_type=MessageType.TEXT, action_ref="user_interaction")
                else:
                    await self.user_interactions_dispatcher.send_message(event=event, message=message, message_type=MessageType.TEXT, action_ref="user_interaction")