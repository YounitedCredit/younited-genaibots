import copy

import pandas as pd

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class VectorSearch(ActionBase):
    REQUIRED_PARAMETERS = ['query','index_name', 'result_count']
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.vector_search_dispatcher = self.global_manager.genai_vectorsearch_dispatcher

    async def execute(self, action_input: ActionInput , event: IncomingNotificationDataBase):
        event_copy = copy.deepcopy(event)
        event_copy.images = []
        event_copy.files_content = []

        try:
            await self.user_interactions_dispatcher.send_message(event=event_copy, message="Looking at existing documentations...", message_type=MessageType.COMMENT)
            vectorfeedback = await self.vector_search_dispatcher.handle_action(action_input)

            if vectorfeedback:
                vectorfeedback_df = pd.DataFrame(vectorfeedback, columns=['document_id', 'passage_id', 'similarity', 'text', 'title', 'file_path'])

                # Construct the message
                message = "Here's the result from the vector db search:\n"
                for _, row in vectorfeedback_df.iterrows():
                    message += f"document_id: {row['document_id']}\n"
                    message += f"similarity: {row['similarity']}\n"
                    message += f"title: {row['title']}\n"
                    message += f"text: {row['text']}\n"
                    message += "Based on this result and similarity related to the user input, answer its previous query.\n\n"

                event_copy.text = message
                await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
            else:
                await self.user_interactions_dispatcher.send_message(event=event_copy, message="Vector search failed, sorry about that :/ see logs for more details", message_type=MessageType.COMMENT)

        except Exception as e:
            self.logger.exception(f"An error occurred: {e}")
