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
        self.backend_internal_queue_processing_dispatcher = self.global_manager.backend_internal_queue_processing_dispatcher

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
                self.logger.debug("IM behavior: No event")
                return

            self.logger.info("IM behavior: Converting event_data to IncomingNotificationDataBase")
            event: IncomingNotificationDataBase = await self.user_interaction_dispatcher.request_to_notification_data(event_data, plugin_name=event_origin)
            if event is None:
                self.logger.error("IM behavior: No event data found")
                return

            # Create a session info in the processing container
            ts = event.timestamp
            channel_id = event.channel_id
            thread_id = event.thread_id
            session_name = f"{str(channel_id).replace(':','_')}-{ts}.txt"
            processing_container = self.backend_internal_data_processing_dispatcher.processing
            await self.backend_internal_data_processing_dispatcher.write_data_content(processing_container, session_name, data="processing")
            self.logger.info(f"IM behavior: Processing session data for {session_name} created successfully.")

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
            self.abort_container = self.backend_internal_data_processing_dispatcher.abort
            self.message_container = self.backend_internal_queue_processing_dispatcher.messages_queue
            self.wait_queue = self.backend_internal_queue_processing_dispatcher.wait_queue  # Utilisation du nouveau dispatcher

            break_keyword = self.global_manager.bot_config.BREAK_KEYWORD
            start_keyword = self.global_manager.bot_config.START_KEYWORD
            clear_keyword = self.global_manager.bot_config.CLEARQUEUE_KEYWORD

            # Check if the text message is the break keyword
            if event.event_label == "thread_message":
                if break_keyword in event.text:
                    abort_name = f"{str(channel_id).replace(':','_')}-{thread_id}.txt"
                    self.logger.info(f"IM behavior: Break keyword detected in thread message, stopping processing with flag {abort_name}.")
                    await self.user_interaction_dispatcher.send_message(event=event, message=f"Break keyword detected, stopping further autogenerated processing in this thread. use {start_keyword} to resume", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message=f"Break keyword detected, stopping further autogenerated processing in this thread. use {start_keyword} to resume", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)
                    await self.backend_internal_data_processing_dispatcher.write_data_content(self.abort_container, abort_name, data="abort")
                    return
                elif start_keyword in event.text:
                    abort_name = f"{str(channel_id).replace(':','_')}-{thread_id}.txt"
                    self.logger.info(f"IM behavior: Start keyword detected in thread message, resuming processing with flag {abort_name}.")
                    await self.user_interaction_dispatcher.send_message(event=event, message="Start keyword detected, resuming further autogenerated processing in this thread.", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message="Start keyword detected, resuming further autogenerated processing in this thread.", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)
                    await self.backend_internal_data_processing_dispatcher.remove_data_content(self.abort_container, abort_name)
                    return
                elif clear_keyword in event.text:
                    self.logger.info(f"IM behavior: Clear keyword detected in thread message, invoking clearing queue for {channel_id} {thread_id}.")
                    messages_in_queue = await self.backend_internal_queue_processing_dispatcher.get_all_messages(channel_id=event.channel_id, thread_id=event.thread_id)  # Utilisation du nouveau dispatcher

                    await self.user_interaction_dispatcher.send_message(event=event, message="Clear keyword detected, clearing queue.", message_type=MessageType.COMMENT, is_internal=True, show_ref=False)
                    await self.user_interaction_dispatcher.send_message(event=event, message="Clear keyword detected, clearing queue.", message_type=MessageType.COMMENT, is_internal=False, show_ref=False)

                    await self.backend_internal_queue_processing_dispatcher.clear_messages_queue(channel_id=event.channel_id, thread_id=event.thread_id)  # Utilisation du nouveau dispatcher
                    for message in messages_in_queue:
                        event_to_process = IncomingNotificationDataBase.from_json(message)
                        await self.user_interaction_dispatcher.remove_reaction(event=event_to_process, channel_id=event.channel_id, timestamp=event_to_process.timestamp, reaction_name=self.reaction_wait)
                    return

            # Check if the event should be processed based on the configuration
            if event.event_label == "thread_message" and not event.is_mention and require_mention_thread_message:
                self.logger.info(
                    "IM behavior: Event is a threaded message without mention and the bot configuration "
                    f"requires mentions for thread messages REQUIRE_MENTION_THREAD_MESSAGE: "
                    f"{self.bot_config.REQUIRE_MENTION_THREAD_MESSAGE}), not processing."
                )
                return
            elif event.event_label == "message":
                if require_mention_new_message and not event.is_mention:
                    self.logger.info("IM behavior: Event is a new message without mention and mentions are required, not processing.")
                    return
                if not require_mention_new_message:
                    self.logger.info("IM behavior: Event is a new message and mentions are not required, processing.")
                elif event.is_mention:
                    self.logger.info("IM behavior: Event is a new message with mention, processing.")
                else:
                    self.logger.info("IM behavior: Event is a new message without mention and non-processed messages are not recorded, not processing.")
                    return

            # Check if there are pending messages in the queue for this event's channel/thread
            self.logger.info(f"IM behavior: Checking for pending messages in channel '{event.channel_id}' and thread '{event.thread_id}'")
            if await self.backend_internal_queue_processing_dispatcher.has_older_messages(data_container=self.message_container, channel_id=event.channel_id, thread_id=event.thread_id):
                
                # If message queuing is enabled, just enqueue the message and add reaction wait
                if self.global_manager.bot_config.ACTIVATE_MESSAGE_QUEUING:
                    event_json = event.to_json()
                    await self.backend_internal_queue_processing_dispatcher.enqueue_message(
                        data_container=self.message_container,
                        channel_id=event.channel_id,
                        thread_id=event.thread_id,
                        message_id=event.timestamp,
                        message=event_json
                    )
                    await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_wait)
                    self.logger.info(f"IM behavior: Message from channel {event.channel_id} enqueued due to pending messages.")
                    return
                else:
                    wait_queue_key = f"{channel_id}_{thread_id}"

                    # Check if the "I'm working on a previous query" message has already been sent for this thread
                    messages_in_wait_queue = await self.backend_internal_queue_processing_dispatcher.get_all_messages(
                        data_container=self.wait_queue,
                        channel_id=channel_id,
                        thread_id=thread_id
                    )

                    await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=event.timestamp, reaction_name=self.reaction_wait)

                    if not messages_in_wait_queue:
                        # Send the "I'm working on a previous query" message only if it hasn't been sent before
                        await self.user_interaction_dispatcher.send_message(
                            event=event,
                            message=f"I'm working on a previous query, wait for max {self.bot_config.MESSAGE_QUEUING_TTL} seconds and try again :-)",
                            message_type=MessageType.COMMENT,
                            is_internal=False
                        )

                        # Enqueue the event in the wait_queue to avoid duplicate messages
                        await self.backend_internal_queue_processing_dispatcher.enqueue_message(
                            data_container=self.wait_queue,
                            channel_id=channel_id,
                            thread_id=thread_id,
                            message_id="0000.0000",
                            message=json.dumps({"status": "wait_message_sent"})
                        )

                    return  # Don't process further until the previous query is resolved

            # Enqueue this message for processing
            self.logger.info(f"IM behavior: No pending messages found. Enqueuing current message for processing in channel '{event.channel_id}', thread '{event.thread_id}'")

            await self.backend_internal_queue_processing_dispatcher.enqueue_message(
                data_container=self.message_container,
                channel_id=event.channel_id,
                thread_id=event.thread_id,
                message_id=event.timestamp,
                message=event.to_json()
            )

            # remove the potential waiting reaction and acknowledge the message
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_wait)
            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_acknowledge)

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
            self.logger.error(f"IM behavior: Error processing incoming request: {str(e)}")
            self.logger.error(traceback.format_exc())
            await self.user_interaction_dispatcher.send_message(event=event, message=f":warning: Error processing incoming request : {str(e)}", message_type=MessageType.TEXT, is_internal=True, show_ref=False)
            await self.mark_error(event, event.channel_id, event.timestamp)
            raise

        finally:
            end_time = time.time()  # Stop the timer
            elapsed_time = end_time - start_time  # Calculate elapsed time
            self.logger.info(f"IM behavior: process_interaction in instant messaging default behavior took {elapsed_time} seconds.")


    async def process_incoming_notification_data(self, event: IncomingNotificationDataBase):
        try:
            # Get the channel ID and timestamp from the event
            channel_id = event.channel_id
            timestamp = event.timestamp

            # Clear up misleading residual reactions
            self.reaction_processing = self.user_interaction_dispatcher.reactions.PROCESSING
            self.reaction_done = self.user_interaction_dispatcher.reactions.DONE
            self.reaction_acknowledge = self.user_interaction_dispatcher.reactions.ACKNOWLEDGE
            self.reaction_generating = self.user_interaction_dispatcher.reactions.GENERATING
            self.reaction_writing = self.user_interaction_dispatcher.reactions.WRITING
            self.reaction_error = self.user_interaction_dispatcher.reactions.ERROR
            self.reaction_wait = self.user_interaction_dispatcher.reactions.WAIT
            self.message_container = self.backend_internal_queue_processing_dispatcher.messages_queue

            # Remove any outdated reactions
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_done)
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=event.channel_id, timestamp=event.timestamp, reaction_name=self.reaction_wait)

            # Check if the event label is a message
            if event.event_label == "message":
                # If the bot requires a mention for a new message and the event is not a mention, log a warning and return
                if self.bot_config.REQUIRE_MENTION_NEW_MESSAGE and not event.is_mention:
                    self.logger.warning("IM behavior: Message is not a mention and the config requires direct mention for new messages, ignoring.")
                    return

            # Log the event details
            self.logger.debug('IM behavior:\n' + json.dumps(event.to_dict(), indent=4))
            genai_output = None

            # If there are genai interaction text plugins, handle the request with the specified plugin and store the output
            genai_output = await self.genai_interactions_text_dispatcher.handle_request(event)

            # Remove the 'processing' reaction for each plugin
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_generating)

            # If there is genai output, process it as an Action and handle the request with the action interactions handler
            if genai_output and genai_output != "":
                await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_writing)
                genai_response = await GenAIResponse.from_json(genai_output)
                await self.global_manager.action_interactions_handler.handle_request(genai_response, event)
            else:
                self.logger.info("IM behavior: No GenAI completion generated, not processing.")

            # If no GenAI output, add the 'done' reaction
            if genai_output is None:
                await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_done)

            # Remove the 'writing' and 'acknowledge' reactions and add the 'done' reaction
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_writing)
            await self.user_interaction_dispatcher.remove_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_acknowledge)
            await self.user_interaction_dispatcher.add_reaction(event=event, channel_id=channel_id, timestamp=timestamp, reaction_name=self.reaction_done)

            # After processing, dequeue the processed message if queuing is enabled
            if self.bot_config.ACTIVATE_MESSAGE_QUEUING:
                await self.backend_internal_queue_processing_dispatcher.dequeue_message(
                    data_container=self.message_container,
                    message_id=event.timestamp,
                    channel_id=event.channel_id,
                    thread_id=event.thread_id
                )

                # Process the next message in the queue, if any
                next_message_id, next_message_content = await self.backend_internal_queue_processing_dispatcher.get_next_message(
                    data_container=self.message_container,
                    channel_id=event.channel_id,
                    thread_id=event.thread_id,
                    current_message_id=event.timestamp
                )

                while next_message_id:
                    self.logger.info(f"IM behavior: Found next message in the queue: {next_message_id}. Processing next message.")
                    try:
                        event_to_process = IncomingNotificationDataBase.from_json(next_message_content)
                        await self.user_interaction_dispatcher.remove_reaction(event=event_to_process, channel_id=str(event_to_process.channel_id), timestamp=event_to_process.timestamp, reaction_name=self.reaction_wait)
                        await self.user_interaction_dispatcher.add_reaction(event=event_to_process, channel_id=str(event_to_process.channel_id), timestamp=event_to_process.timestamp, reaction_name=self.reaction_acknowledge)
                        await self.process_incoming_notification_data(event_to_process)
                    except Exception as e:
                        self.logger.error(f"IM behavior: Error parsing next message: {str(e)}\n{traceback.format_exc()}")
                        self.logger.error(f"IM behavior: Next message content: {next_message_content}")

                    # Dequeue the message regardless of success or failure
                    await self.backend_internal_queue_processing_dispatcher.dequeue_message(
                        data_container=self.message_container,
                        message_id=next_message_id,
                        channel_id=event.channel_id,
                        thread_id=event.thread_id
                    )

                    # Get the next message in the queue
                    next_message_id, next_message_content = await self.backend_internal_queue_processing_dispatcher.get_next_message(
                        data_container=self.message_container,
                        channel_id=event.channel_id,
                        thread_id=event.thread_id,
                        current_message_id=event.timestamp
                    )
            else:
                # If message queuing is disabled, remove the "wait" reaction from the thread
                self.logger.info(f"IM behavior: Message queuing is disabled, removing wait reaction from thread {event.thread_id}")
                await self.user_interaction_dispatcher.remove_reaction_from_thread(
                    channel_id=event.channel_id,
                    thread_id=event.thread_id,
                    reaction_name=self.reaction_wait
                )

                await self.backend_internal_queue_processing_dispatcher.dequeue_message(
                    data_container=self.wait_queue,
                    channel_id=event.channel_id,
                    thread_id=event.thread_id,
                    message_id="0000.0000"
                )

        except Exception as e:
            self.logger.error(f"IM behavior: Error processing incoming notification data: {str(e)}\n{traceback.format_exc()}")


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
