import copy

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class LongText(ActionBase):
    REQUIRED_PARAMETERS = ['value','is_finished']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.user_interactions_text_plugin = None
        self.logger = self.global_manager.logger
        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        try:
            self.event: IncomingNotificationDataBase = copy.deepcopy(event)
            self.action_input: ActionInput = action_input

            self.concatenate_folder = self.backend_internal_data_processing_dispatcher.concatenate
            self.sessions_folder = self.backend_internal_data_processing_dispatcher.sessions

            value = action_input.parameters.get('value', '')
            is_finished = action_input.parameters.get('is_finished', False) == True
            response_id = event.thread_id if event.thread_id else event.timestamp
            blob_name = f"{event.channel_id}-{response_id}.txt"

            if not is_finished:
                if not await self._process_continuation(value, blob_name, event):
                    return False
            else:
                if not await self._process_end_of_conversation(value, blob_name, event):
                    return False

            return True
        except Exception as e:
            
            self.logger.error(f"An error occurred: {str(e)}")
            return False

    async def _process_continuation(self, value, blob_name, event):
        try:
            existing_content = await self.backend_internal_data_processing_dispatcher.read_data_content(self.concatenate_folder, blob_name)
            updated_content = f'{existing_content or ""} \n\n{value}'.strip()
            await self.backend_internal_data_processing_dispatcher.write_data_content(self.concatenate_folder, blob_name, updated_content)

            event.text = "Great, thanks, now create the next longtext action."
            event.files_content = []
            event.images = []
            await self.genai_interactions_text_dispatcher.trigger_genai(event=event)
            return True
        except Exception as e:
            self.logger.error(f"Error in _process_continuation: {str(e)}")
            return False

    async def _process_end_of_conversation(self, value, blob_name, event):
        try:
            concatenated_content = await self.backend_internal_data_processing_dispatcher.read_data_content(self.concatenate_folder, blob_name)
            complete_content = f"{concatenated_content or ''} \n\n{value}".strip()

            await self.backend_internal_data_processing_dispatcher.update_session(self.sessions_folder, blob_name, "assistant", complete_content)
            await self.backend_internal_data_processing_dispatcher.remove_data_content(self.concatenate_folder, blob_name)

            if not event.thread_id:
                event.thread_id = event.timestamp

            await self.user_interaction_dispatcher.upload_file(event=event, file_content=complete_content, filename="LongText.txt", title="Long Text")
            await self.user_interaction_dispatcher.upload_file(event=event, file_content=complete_content, filename="LongText.txt", title="Long Text", is_internal=True)
            return True
        except Exception as e:
            self.logger.error(f"Error in _process_end_of_conversation: {str(e)}")
            return False
