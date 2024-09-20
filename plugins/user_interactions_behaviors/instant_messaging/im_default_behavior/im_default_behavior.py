import json
import time
import traceback

from core.genai_interactions.genai_response import GenAIResponse
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from core.user_interactions_behaviors.user_interactions_behavior_base import (
    UserInteractionsBehaviorBase,
)
from core.user_interactions.user_interactions_plugin_base import (
    UserInteractionsPluginBase,
)
from utils.config_manager.config_model import BotConfig


class ImDefaultBehaviorPlugin(UserInteractionsBehaviorBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager

        if not isinstance(global_manager, GlobalManager):
            raise TypeError("global_manager must be an instance of GlobalManager")

        self.global_manager : GlobalManager = global_manager        
        self.logger = global_manager.logger
        bot_config_dict = global_manager.config_manager.config_model.BOT_CONFIG
        self.bot_config : BotConfig = bot_config_dict
        self.reaction_done = None
        self.reaction_generating = None
        self.reaction_writing = None
        self.reaction_error = None
        self.reaction_acknowledge = None

    def initialize(self):
        #Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    @property
    def plugin_name(self):
        return "im_default_behavior"

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    async def process_interaction(self, event_data, event_origin=None):
        try:
            start_time = time.time()  # Start the timer

            if event_data is None:
                self.logger.debug("No event")
                return

            self.logger.info(f"Converting event_data to IncomingNotificationDataBase")
            event: IncomingNotificationDataBase = await self.user_interaction_dispatcher.request_to_notification_data(event_data, plugin_name=event_origin)
            if event is None:
                self.logger.error("No event data found")
                return

            # Create a session info in the processing container
            ts = event.timestamp
            channel_id = event.channel_id
            thread_id = event.thread_id
            session_name = f"{str(channel_id).replace(':','_')}-{ts}.txt"
            processing_container = self.backend_internal_data_processing_dispatcher.processing
            await self.backend_internal_data_processing_dispatcher.write_data_content(processing_container, session_name, data="processing")
            self.logger.info(f"Processing session data for {session_name} created successfully.")

            # Retrieve bot configuration settings
            require_mention_new_message = self.bot_config.REQUIRE_MENTION_NEW_MESSAGE
            require_mention_thread_message = self.bot_config.REQUIRE_MENTION_THREAD_MESSAGE

            # Reactions for the bot to use in the chat
            self.user_interaction_dispatcher.set_default_plugin(event.origin_plugin_name)
            self.reaction_processing = self.user_interaction_dispatcher.reactions.PROCESSING
            self.reaction_done = self.user_interaction_dispatcher.reactions.DONE
            self.reaction_acknowledge = self.user_interaction_dispatcher.reactions.ACKNOWLEDGE
            self.reaction_generating = self.user_interaction_dispatcher.reactions.GENERATING
            self.reaction_writing = self.user_interaction_dispatcher.reactions.WRITING
            self.reaction_error = self.user_interaction_dispatcher.reactions.ERROR
            self.reaction_wait = self.user_interaction_dispatcher.reactions.WAIT    

            break_keyword = self.global_manager.bot_config.BREAK_KEYWORD
            start_keyword = self.global_manager.bot_config.START_KEYWORD
            clear_keyword = self.global_manager.bot_config.CLEARQUEUE_KEYWORD

            # Check if the text message is the break keyword
            if event.event_label == "thread_message":
                if break_keyword in event.text:
                    abort_name = f"{str(channel_id).replace(':','_')}-{thread_id}.txt"
                    self.logger.info(f"Break keyword detected in thread message, stopping processing with flag {abort_name}.")
                    await self.user_interaction_dispatcher.send_message(event=event, message=f"Break keyword detected, stopping further autogenerated processing in this thread. use {start_keyword} to resume", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message=f"Break keyword detected, stopping further autogenerated processing in this thread. use {start_keyword} to resume", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)
                    await self.backend_internal_data_processing_dispatcher.write_data_content(abort_container, abort_name, data="abort")
                    return
                elif start_keyword in event.text:
                    abort_name = f"{str(channel_id).replace(':','_')}-{thread_id}.txt"
                    self.logger.info(f"Start keyword detected in thread message, resuming processing with flag {abort_name}.")
                    await self.user_interaction_dispatcher.send_message(event=event, message="Start keyword detected, resuming further autogenerated processing in this thread.", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message="Start keyword detected, resuming further autogenerated processing in this thread.", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)
                    await self.backend_internal_data_processing_dispatcher.remove_data_content(abort_container, abort_name)
                    return
                elif clear_keyword in event.text:
                    self.logger.info(f"Clear keyword detected in thread message, invoking clearing queue for {channel_id} {thread_id}.")
                    await self.user_interaction_dispatcher.send_message(event=event, message="Clear keyword detected, clearing queue.", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message="Clear keyword detected, clearing queue.", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)
                    await self.backend_internal_data_processing_dispatcher.clear_messages_queue(channel_id=event.channel_id, thread_id=event.thread_id)
                    return            

            # Check if the event should be processed based on the configuration
            if event.event_label == "thread_message" and not event.is_mention and require_mention_thread_message:                
                self.logger.info(
                    "Event is a threaded message without mention and the bot configuration "
                    f"requires mentions for thread messages REQUIRE_MENTION_THREAD_MESSAGE: "
                    f"{self.bot_config.REQUIRE_MENTION_THREAD_MESSAGE}), not processing."
                )
                return
            elif event.event_label == "message":
                if require_mention_new_message and not event.is_mention:
                    self.logger.info("Event is a new message without mention and mentions are required, not processing.")
                    return
                if not require_mention_new_message:
                    self.logger.info("Event is a new message and mentions are not required, processing.")
                elif event.is_mention:
                    self.logger.info("Event is a new message with mention, processing.")
                else:
                    self.logger.info("Event is a new message without mention and non-processed messages are not recorded, not processing.")
                    return

            # Check if there are pending messages in the queue for this event's channel/thread
            self.logger.info(f"Checking for pending messages in channel '{event.channel_id}' and thread '{event.thread_id}'")
            if await self.backend_internal_data_processing_dispatcher.has_older_messages(channel_id=event.channel_id, thread_id=event.thread_id):
                await self.backend_internal_data_processing_dispatcher.enqueue_message(channel_id=event.channel_id, thread_id=event.thread_id, message_id=event.timestamp, message=str(json.dumps(event.to_dict())))
                self.logger.info(f"Message from channel {event.channel_id} enqueued due to pending messages.")
                await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_wait)
                return

            # Enqueue this message for processing
            self.logger.info(f"No pending messages found. Enqueuing current message for processing in channel '{event.channel_id}', thread '{event.thread_id}'.")
            await self.backend_internal_data_processing_dispatcher.enqueue_message(channel_id=event.channel_id, thread_id=event.thread_id, message_id=event.timestamp, message=str(event_data))

            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_acknowledge)            
            
            abort_container = self.backend_internal_data_processing_dispatcher.abort            

            # If the event is a thread message
            if event.event_label == "thread_message":
                # If the bot is configured to require a mention in thread messages and the event is a mention,
                # or if the bot is configured to not require a mention in thread messages
                if (self.global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE == False or (self.global_manager.bot_config.REQUIRE_MENTION_THREAD_MESSAGE and event.is_mention)):
                    # Send a message in response to the event
                    await self.user_interaction_dispatcher.send_message(event=event, message="", message_type=MessageType.TEXT, is_internal=True, show_ref=True)
            else:
                await self.user_interaction_dispatcher.send_message(event=event, message="", message_type=MessageType.TEXT, is_internal=True, show_ref=True)

            # Process the incoming notification data
            await self.process_incoming_notification_data(event)

            
        except Exception as e:
            self.logger.error(f"Error processing incoming request: {str(e)}")
            self.logger.error(traceback.format_exc())
            await self.user_interaction_dispatcher.send_message(event=event, message=f":warning: Error processing incoming request : {str(e)}", message_type=MessageType.TEXT, is_internal=True, show_ref=False)
            await self.mark_error(event, event.channel_id, event.timestamp)
            raise

        finally:
              
            end_time = time.time()  # Stop the timer
            elapsed_time = end_time - start_time  # Calculate elapsed time
            self.logger.info(f"process_interaction in instant messaging default behavior took {elapsed_time} seconds.")
    
    async def process_incoming_notification_data(self, event: IncomingNotificationDataBase):
        try:
            # Get the channel ID and timestamp from the event
            channel_id = event.channel_id
            timestamp = event.timestamp
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_done)

            # Check if the event label is a message
            if event.event_label == "message":
                # If the bot requires a mention for a new message and the event is not a mention, log a warning and return
                if self.bot_config.REQUIRE_MENTION_NEW_MESSAGE and event.is_mention is False:
                    self.logger.warning("Message is not a mention and the config is set to required direct mention for new message, ignoring")
                    return

            # Log the event details
            self.logger.debug('\n' + json.dumps(event.to_dict(), indent=4))
            genai_output = None

            # If there are genai interaction text plugins, handle the request with specified plugin and store the output
            genai_output = await self.genai_interactions_text_dispatcher.handle_request(event)

            # If there are user interaction plugins, add the 'done' reaction and remove the 'processing' reaction for each plugin
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_generating)

            # If there is genai output, process it to an Action and handle the request with the action interactions handler
            if genai_output and genai_output != "":
                await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name = self.reaction_writing)
                genai_response = await GenAIResponse.from_json(genai_output)
                # If the genai response is not None, handle the request with the action interactions handler
                await self.global_manager.action_interactions_handler.handle_request(genai_response, event)
            else:
                # If there is no genai output, log a warning
                self.logger.info("No GenAI completion generated, not processing")

            # don't ack if the bot config says not to
            if genai_output is None:
                if self.global_manager.bot_config.ACKNOWLEDGE_NONPROCESSED_MESSAGE:
                    await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_done)
            else:
                await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_done)

            # Remove the 'writing' and 'acknowledge' reactions and add the 'done' reaction
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_writing)
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_acknowledge)

            # Add the "done" reaction and dequeue the processed message
            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_done)
            
            # After processing, check if there are any pending messages in the queue and process them
            await self.backend_internal_data_processing_dispatcher.dequeue_message(message_id=event.timestamp, channel_id=event.channel_id, thread_id=event.thread_id)

            # Check if there are any pending messages in the queue and process them
            next_message_id, next_message_content = await self.backend_internal_data_processing_dispatcher.get_next_message(channel_id=event.channel_id, thread_id=event.thread_id, current_message_id=event.timestamp)

            while next_message_id:
                self.logger.info(f"Found next message in the queue: {next_message_id}. Processing next message.")
                try:
                    next_event = json.loads(next_message_content)
                    event_to_process = IncomingNotificationDataBase.from_dict(next_event)
                    await self.user_interaction_dispatcher.remove_reaction(event=event_to_process, channel_id=str(event_to_process.channel_id), timestamp=event_to_process.timestamp, reaction_name=self.reaction_wait)
                    await self.process_incoming_notification_data(event_to_process)
                except Exception as e:
                    self.logger.error(f"Error parsing next message: {str(e)}\n{traceback.format_exc()}")
                    self.logger.error(f"Next message content: {next_message_content}")
                
                # Dequeue the message regardless of success or failure
                await self.backend_internal_data_processing_dispatcher.dequeue_message(message_id=next_message_id, channel_id=event.channel_id, thread_id=event.thread_id)
                
                # Get the next message in the queue
                next_message_id, next_message_content = await self.backend_internal_data_processing_dispatcher.get_next_message(channel_id=event.channel_id, thread_id=event.thread_id, current_message_id=event.timestamp)

        except Exception as e:
            # If an error occurs, log the error and raise the exception
            self.logger.error(f"Error processing interaction: {str(e)}\n{traceback.format_exc()}")
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_done)
            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_error)

    async def begin_genai_completion(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when GenAI starts generating a completion.
        # It updates the reaction on the message in the specified channel and timestamp.
        # The 'writing' reaction is removed and the 'generating' reaction is added.
        await self.update_reaction(event=event, channel_id=channel_id, timestamp=timestamp, remove_reaction= self.reaction_writing, add_reaction=self.reaction_generating)

    async def end_genai_completion(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when GenAI finishes generating a completion.
        # It removes the 'generating' reaction from the message in the specified channel and timestamp.
        await self.update_reaction(event=event, channel_id=channel_id, timestamp=timestamp, remove_reaction=self.reaction_generating)

    async def begin_long_action(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when a long action starts.
        # It updates the reaction on the message in the specified channel and timestamp.
        # The 'generating' reaction is removed and the 'processing' reaction is added.
        await self.update_reaction(event=event, channel_id=channel_id, timestamp=timestamp, remove_reaction= self.reaction_generating, add_reaction=self.reaction_processing)

    async def end_long_action(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when a long action ends.
        # It removes the 'processing' reaction from the message in the specified channel and timestamp.
        await self.update_reaction(event=event, channel_id=channel_id, timestamp=timestamp, remove_reaction= self.reaction_processing)

    async def begin_wait_backend(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when the backend starts processing a request.
        # It adds the 'wait' reaction to the message in the specified channel and timestamp.
        pass
        # await self.instantmessaging_plugin.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_wait)

    async def end_wait_backend(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when the backend finishes processing a request.
        # It removes the 'wait' reaction from the message in the specified channel and timestamp.
        pass
        # await self.instantmessaging_plugin.remove_reaction(channel_id=channel_id, timestamp=timestamp, reaction_name= self.reaction_wait)

    async def mark_error(self, event: IncomingNotificationDataBase, channel_id, timestamp):
        # This method is called when an error occurs.
        # It updates the reaction on the message in the specified channel and timestamp.
        # The 'generating' reaction is removed and the 'error' reaction is added.
        await self.update_reaction(event=event, channel_id=channel_id, timestamp=timestamp, remove_reaction= self.reaction_generating, add_reaction=self.reaction_error)

    async def update_reaction(self, event: IncomingNotificationDataBase, channel_id, timestamp, remove_reaction, add_reaction=None):
        # This method is used to update the reaction on a message.
        # It removes the specified reaction and, if provided, adds a new one.
        await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=remove_reaction)
        if add_reaction:
            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=add_reaction)
