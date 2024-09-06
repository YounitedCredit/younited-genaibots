import copy
import json
from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType

class VectorSearch(ActionBase):
    REQUIRED_PARAMETERS = ['query', 'index_name', 'result_count']

    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.vector_search_dispatcher = self.global_manager.genai_vectorsearch_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        event_copy = copy.deepcopy(event)
        event_copy.images = []
        event_copy.files_content = []

        try:
            # Notify user that search is starting
            await self.user_interactions_dispatcher.send_message(
                event=event_copy, message="Looking at existing documentation...", message_type=MessageType.COMMENT
            )

           # Call the vector search
            vectorfeedback_json = await self.vector_search_dispatcher.handle_action(action_input)

            if vectorfeedback_json:
                # Ensure the JSON is loaded properly if it's in string form
                if isinstance(vectorfeedback_json, str):
                    vectorfeedback_dict = json.loads(vectorfeedback_json)
                else:
                    vectorfeedback_dict = vectorfeedback_json
                
                if 'search_results' in vectorfeedback_dict:
                    search_results = vectorfeedback_dict['search_results']
                    
                    # Construct the message from the search result JSON
                    message = "Here's the result from the vector db search with the cosine similarity score to help you judge the most relevant data regarding your query:\n"
                    for result in search_results:
                        message += f"Document ID: {result['id']}\n"
                        message += f"Score: {result['@search.score']}\n"
                        message += f"Title: {result['title']}\n"
                        message += f"File Path: {result['file_path']}\n"  # Add file path
                        message += f"Content: {result['content']}\n"  
                        message += "Based on this result and its similarity related to the user's input, answer their previous query. Use only information relevant to the user question, everything is not necessary relevant but use anything useful\n\n"

                # Send message to trigger the GenAI interaction
                event_copy.text = message
                await self.genai_interactions_text_dispatcher.trigger_genai(event=event_copy)
            else:
                await self.user_interactions_dispatcher.send_message(
                    event=event_copy, message="Vector search failed, sorry about that :/ see logs for more details", message_type=MessageType.COMMENT
                )

        except Exception as e:
            # Log the error and notify the user of the failure
            self.logger.exception(f"An error occurred: {e}")
            await self.user_interactions_dispatcher.send_message(
                event=event_copy, message="Vector search failed, sorry about that :/ see logs for more details", message_type=MessageType.COMMENT
            )
