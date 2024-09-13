import base64
import inspect
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
import aiohttp
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pypdf import PdfReader
from slack_sdk import WebClient

from core.global_manager import GlobalManager
from plugins.user_interactions.instant_messaging.slack.slack_event_data import (
    SlackEventData,
)
from plugins.user_interactions.instant_messaging.slack.utils.slack_block_processor import (
    SlackBlockProcessor,
)
from utils.plugin_manager.plugin_manager import PluginManager
from slack_sdk.web.async_client import AsyncWebClient

class SlackInputHandler:
    def __init__(self, global_manager : GlobalManager, slack_config):
        from ..slack import SlackConfig
        self.global_manager = global_manager
        self.logger = global_manager.logger
        self.plugin_manager : PluginManager = global_manager.plugin_manager
        self.slack_config : SlackConfig = slack_config
        self.APPLICATION_PLACEHOLDER = 'application/pdf'
        if self.slack_config is None:
            self.logger.error("No 'SLACK' configuration found in 'USER_INTERACTIONS_PLUGINS'")
            return

        self.SLACK_API_URL = self.slack_config.SLACK_API_URL
        if self.SLACK_API_URL is None:
            self.logger.error("No 'SLACK_API_URL' found in 'SLACK' configuration")
            return

        self.SLACK_USER_INFO = f'{self.SLACK_API_URL}users.info?user='
        self.SLACK_POST_MESSAGE = f'{self.SLACK_API_URL}chat.postMessage'

        self.SLACK_MESSAGE_TTL = self.slack_config.SLACK_MESSAGE_TTL

        if self.SLACK_MESSAGE_TTL is None:
            self.logger.error("No 'SLACK_MESSAGE_TTL' found in 'SLACK' configuration")
            return

        self.SLACK_AUTHORIZED_CHANNELS = self.slack_config.SLACK_AUTHORIZED_CHANNELS.split(",")
        self.SLACK_AUTHORIZED_APPS = self.slack_config.SLACK_AUTHORIZED_APPS.split(",")
        self.SLACK_AUTHORIZED_WEBHOOKS = self.slack_config.SLACK_AUTHORIZED_WEBHOOKS.split(",")
        self.SLACK_BOT_USER_ID = self.slack_config.SLACK_BOT_USER_ID
        self.SLACK_BOT_TOKEN = self.slack_config.SLACK_BOT_TOKEN
        self.SLACK_BOT_USER_TOKEN = self.slack_config.SLACK_BOT_USER_TOKEN
        self.client = WebClient(token=self.SLACK_BOT_TOKEN)
        self.WORKSPACE_NAME = self.slack_config.SLACK_WORKSPACE_NAME
        self.async_client = AsyncWebClient(token=self.SLACK_BOT_TOKEN)

    def is_message_too_old(self, event_ts):

        # Convertir le timestamp de l'événement en objet datetime
        event_datetime = event_ts
        # Obtenir le datetime actuel
        current_datetime = datetime.now(timezone.utc)
        # Calculer la différence
        diff = current_datetime - event_datetime
        return diff.total_seconds() > self.SLACK_MESSAGE_TTL

    async def is_relevant_message(self, event_type, event_ts, user_id, app_id, api_app_id, bot_user_id, channel_id):

        if event_type == "reaction_added":
            self.logger.info("Ignoring emoji reaction notification")
            return False

        # Ignore events prior to TTL
        elif self.is_message_too_old(event_ts):
            self.info("Ignoring old message notification")
            return False

        elif user_id == bot_user_id:
            self.logger.info("Ignoring message from the bot itself.")
            return False

        elif (app_id not in self.SLACK_AUTHORIZED_APPS and app_id is not None):
            self.logger.info(f"Ignoring event from unauthorized app: {app_id}")
            return False
        
        elif (api_app_id not in self.SLACK_AUTHORIZED_WEBHOOKS and api_app_id is not None and app_id is None):
            self.logger.info(f"Ignoring event from unauthorized webhook: {api_app_id}")
            return False

        elif channel_id not in self.SLACK_AUTHORIZED_CHANNELS:
            self.logger.info(f"Ignoring event from unauthorized channel: {channel_id}")
            return False
        else:
            return True

    async def format_slack_timestamp(self, slack_timestamp: str) -> str:
        # Convert Slack timestamp to UTC datetime
        timestamp_float = float(slack_timestamp)

        # Convert the Unix timestamp to a UTC datetime object
        utc_dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)

        # Define the Paris timezone
        paris_tz = ZoneInfo("Europe/Paris")

        # Convert UTC datetime to Paris time
        paris_dt = utc_dt.astimezone(paris_tz)

        # Format the datetime object to a readable string
        paris_time = paris_dt.strftime('%Y-%m-%d %H:%M:%S')
        return paris_time

    # Function to get user info
    async def get_user_info(self, user_id):
        if user_id is not None and user_id != 'Unknown':
            try:
                response = await self.async_client.users_info(user=user_id)
                if response['ok']:
                    user = response['user']
                    name = user.get('real_name') or user.get('name', 'Unknown')
                    email = user.get('profile', {}).get('email', 'Unknown')
                    return name, email, user_id
                else:
                    self.logger.error(f"Failed to fetch user info: {response.get('error', 'Unknown error')}")
            except Exception as e:
                self.logger.error(f"Error fetching user info: {e}")
        return 'Unknown', 'Unknown', user_id

    async def format_slack_timestamp(self, slack_timestamp: str) -> str:
        timestamp_float = float(slack_timestamp)
        utc_dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
        paris_tz = ZoneInfo("Europe/Paris")
        paris_dt = utc_dt.astimezone(paris_tz)
        return paris_dt.strftime('%Y-%m-%d %H:%M:%S')

    def extract_event_details(self, event):
        try:
            ts = event.get('ts')
            user_id = event.get('user')
            app_id = event.get('app_id')
            api_app_id = event.get('api_app_id')
            username = event.get("username")
            channel_id = event.get('channel')
            main_timestamp = event.get('ts')
            return ts, user_id, app_id, api_app_id, username, channel_id, main_timestamp
        except Exception as e:
            self.logger.error(f"Failed to extract event details: {e}")
            return None, None, None, None, None, None, None

    def process_message_event(self, event, bot_user_id, timestamp):
        try:
            text = event.get('text', event.get('message', {}).get('text', ''))
            is_mention = f"<@{bot_user_id}>" in text
            response_id = event.get('thread_ts', timestamp)
            return text, is_mention, response_id
        except Exception as e:
            self.logger.error(f"Error processing message event: {e}")
            return None, None, None

    def determine_event_label_and_thread_id(self, event, thread_id, timestamp):
        try:
            if thread_id is not None and thread_id != timestamp:
                event_label = "thread_message"
                thread_id = event.get('thread_ts', timestamp)
            else:
                event_label = "message"
                thread_id = thread_id if thread_id else timestamp
            return event_label, thread_id
        except Exception as e:
            self.logger.error(f"Error determining event label and thread timestamp: {e}")
            return None, None

    async def handle_exception(self, e, channel_id, timestamp, req):
        self.logger.error(f"Error processing request from Slack: {e} {str(req)}")
        try:
            data = await req.json()
            self.logger.error(f"Request data: {data}")
        except Exception as ex:
            self.logger.error(f"Error reading request data: {ex}")

    def resize_image(self, image_bytes, max_size):
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode in ("RGBA", "P"):  # Check if image has transparency
            image = image.convert("RGB")  # Convert image to RGB
        width, height = image.size
        if width > max_size[0] or height > max_size[1]:  # Only resize if the image is larger than max_size
            ratio = min(max_size[0]/width, max_size[1]/height)
            new_size = (int(width*ratio), int(height*ratio))
            image = image.resize(new_size, Image.BILINEAR)
        byte_arr = io.BytesIO()
        image.save(byte_arr, format='JPEG')
        return byte_arr.getvalue()  # Get a bytes object from the BytesIO object

    async def handle_image_file(self, file, image_bytes=None):
        try:
            if image_bytes is None:
                image_url = file.get('url_private')
                image_bytes = await self.download_image_as_byte_array(image_url)

            if image_bytes:
                resized_image_bytes = base64.b64encode(image_bytes).decode('utf-8')
                return resized_image_bytes
        except Exception as e:
            self.logger.error(f"Failed to process image: {e}")
            return None

    async def handle_zip_file(self, file):
        try:
            file_url = file.get('url_private')
            file_content = await self.download_file_content(file_url)
            if file_content:
                files_content, zip_images = await self.extract_files_from_zip(file_content)
                return files_content, zip_images
        except Exception as e:
            self.logger.error(f"Failed to handle zip file: {e}")
            return None, None

    async def extract_files_from_zip(self, file_content):
        all_files_content = []
        zip_images = []
        try:
            with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_ref:
                for zip_info in zip_ref.infolist():
                    with zip_ref.open(zip_info) as file_in_zip:
                        if zip_info.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            image_data = file_in_zip.read()
                            file = {'url_private': None, 'name': zip_info.filename}
                            img_str = await self.handle_image_file(file, image_bytes=image_data)
                            zip_images.append(img_str)
                            self.logger.debug(f'Successfully processed image file {zip_info.filename}')
                        else:
                            file_content = file_in_zip.read()
                            if zip_info.filename.lower().endswith('.pdf'):
                                file = {'url_private': file_content, 'mimetype': self.APPLICATION_PLACEHOLDER, 'name': zip_info.filename}
                                text_contents = await self.handle_text_file(file, file_content=file_content)
                                all_files_content.extend(text_contents)
                                self.logger.debug(f'Successfully processed PDF file {zip_info.filename}')
                            else:
                                decoded = False
                                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                                    try:
                                        file_content_decoded = file_content.decode(encoding)
                                        all_files_content.append(f"SHARED FILE FULL NAME in a ZIP : {zip_info.filename}\n THIS FILE CONTENT: \n{file_content_decoded}")
                                        self.logger.debug(f'Successfully processed text file {zip_info.filename} with encoding {encoding}')
                                        decoded = True
                                        break
                                    except UnicodeDecodeError as e:
                                        self.logger.warning(f'UnicodeDecodeError for file {zip_info.filename} with encoding {encoding}: start={e.start}, end={e.end}, reason={e.reason}')
                                if not decoded:
                                    self.logger.warning(f'Error decoding file content for file {zip_info.filename}, content might be binary.')
        except Exception as e:
            self.logger.error(f"Failed to extract files from zip: {e}")
        return all_files_content, zip_images

    async def handle_text_file(self, file, file_content=None):
        if file_content is None:
            file_url = file.get('url_private')
            file_content = await self.download_file_content(file_url)
        if file_content:
            if file.get('mimetype') == self.APPLICATION_PLACEHOLDER:
                with io.BytesIO(file_content) as open_pdf_file:
                    pdf_reader = PdfReader(open_pdf_file)
                    pdftext = f"FileName: {file.get('name')}\n"
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdftext += f"Page {page_num + 1}:\n{page.extract_text()}\n"
                    file_content = pdftext
            else:
                file_content = file_content.decode('utf-8')
            return [f"\nYOU RECEIVED A SHARED FILE FROM THE USER. FILE NAME : {file.get('name')}. Here is the file content between BEGIN OF FILE and END OF FILE marquee: ```BEGIN OF FILE \n {file_content} \n ```END OF FILE"]

    async def request_to_notification_data(self, event_data):
        try:
            self.logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")
            bot_user_id = self.SLACK_BOT_USER_ID
            event = event_data.get('event', {})
            if not event:
                self.logger.error("No event data found")
                return None

            timestamp = event.get('ts')
            if not self._is_valid_event(event, bot_user_id):
                return None

            event_type = event.get('type')
            ts, user_id, app_id, api_app_id, username, channel_id, main_timestamp = self.extract_event_details(event)
            thread_id = event.get('thread_ts')

            if event_type not in ['message', 'app_mention']:
                self.logger.info(f"Ignoring event type {event_type}")
                return None

            self.logger.info('Valid event category (message)')
            
            base64_images, files_content = await self._process_files(event)
            
            text, is_mention, response_id = self.process_message_event(event, bot_user_id, timestamp)

            if not text and not base64_images and not files_content:
                self.logger.error(f"No text, images, or files received from Slack cid:{channel_id} ts:{thread_id}")
                return None

            text = await self._process_text(text, main_timestamp, user_id)

            event_label, thread_id = self.determine_event_label_and_thread_id(event, thread_id, ts)
            response_id = ts if thread_id == '' else thread_id

            event_data_instance = await self._create_event_data_instance(
                ts, channel_id, thread_id, response_id, user_id, app_id, api_app_id, username, is_mention, text, base64_images, files_content
            )

            if text or event_data_instance.images or event_data_instance.files_content:
                self.logger.debug(str(event_data_instance))
                return event_data_instance

            return None

        except Exception as e:
            self.logger.error(f"Error in request_to_notification_data: {e}")
            return None

    def _is_valid_event(self, event, bot_user_id):
        if event.get('subtype') == 'message_changed':
            event = event.get('message')
            if event.get('user') == bot_user_id or event.get('user') is None:
                self.logger.info("Discarding request after analysis: received message_changed from Bot")
                return False
        return True

    async def _process_files(self, event):
        base64_images = []
        files_content = []
        if event.get('subtype') == 'file_share' and 'files' in event:
            self.logger.info('Event subtype is a file share and it contains files')
            files = event.get('files', [])
            for file in files:
                await self._process_single_file(file, base64_images, files_content)
        return base64_images, files_content

    async def _process_single_file(self, file, base64_images, files_content):
        try:
            mimetype = file.get('mimetype', '')
            self.logger.debug(f'Processing file with mimetype: {mimetype}')
            if mimetype.startswith('image/'):
                base64_image = await self.handle_image_file(file)
                if base64_image:
                    base64_images.append(base64_image)
                    self.logger.debug('Added base64 image to base64_images')
            elif mimetype in ['text/plain', 'application/csv', 'application/msword', self.APPLICATION_PLACEHOLDER]:
                text_contents = await self.handle_text_file(file)
                if text_contents:
                    files_content.extend(text_contents)
                    self.logger.debug('Added text content to files_content')
            elif mimetype == 'application/zip':
                text_contents, zip_images = await self.handle_zip_file(file)
                if text_contents:
                    files_content.extend(text_contents)
                    self.logger.debug('Added text content to files_content')
                if zip_images:
                    base64_images.extend(zip_images)
                    self.logger.debug('Added zip image to base64_images')
        except Exception as e:
            self.logger.error(f"Error processing file with mimetype {mimetype}: {e}")

    async def _process_text(self, text, main_timestamp, user_id):
        if text is not None:
            text = await self._process_slack_links(text, main_timestamp, user_id)
            text = await self._process_urls(text)
        return text

    async def _process_slack_links(self, text, main_timestamp, user_id):
        slack_message_links = re.findall(r'<(https:\/\/[a-zA-Z0-9\.]+\.slack\.com\/archives\/.*?)>', text)
        for link in slack_message_links:
            processed_content = await self._process_single_slack_link(link, "", main_timestamp, user_id, depth=0)
            text = text.replace(f"<{link}>", processed_content)
        return text

    async def _process_single_slack_link(self, link, original_text, main_timestamp, user_id, depth=0):
        try:
            if depth > 5:
                return f"[Maximum depth reached for Slack link: {link}]"

            self.logger.debug(f"Processing Slack link (depth {depth}): {link}")
            
            # Extract channel, message, and thread info from the URL
            channel_id, message_ts, thread_ts, is_thread = await self.extract_info_from_url(link)
            self.logger.debug(f"Extracted info: channel_id={channel_id}, message_ts={message_ts}, thread_ts={thread_ts}, is_thread={is_thread}")

            # Case 1: If it's a thread link (is_thread == False and no thread_ts), always fetch the entire thread
            if not is_thread and not thread_ts:
                self.logger.info(f"Fetching entire thread for message_ts: {message_ts} (Thread link)")
                result = await self.get_message_content(channel_id, message_ts, thread_ts=message_ts, original_link=link)

            # Case 2: If it's a message inside a thread (is_thread == True), handle based on GET_ALL_THREAD_FROM_MESSAGE_LINKS
            elif is_thread:
                if self.global_manager.bot_config.GET_ALL_THREAD_FROM_MESSAGE_LINKS:
                    self.logger.info(f"GET_ALL_THREAD_FROM_MESSAGE_LINKS is True, fetching entire thread for message: {message_ts} in thread: {thread_ts}")
                    # Fetch the full thread and return all the messages in the thread
                    result = await self.get_message_content(channel_id, message_ts, thread_ts=None, original_link=link)
                else:
                    # Fetch only the specific message
                    self.logger.info(f"Fetching single message for message_ts: {thread_ts}")
                    result = await self.get_message_content(channel_id, thread_ts, thread_ts=None, original_link=link)

            # Handle case where no messages are found
            if not result['messages']:
                return f"No messages found for the given Slack link: {link}"

            # Extract metadata and messages
            metadata = result['metadata']
            content_type = result['content_type']
            messages = result['messages']

            # Tag the exact message that was linked
            tagged_message = None
            if is_thread:
                # When it's a message inside a thread, compare against `thread_ts`
                for message in messages:
                    if message['ts'] == thread_ts:
                        tagged_message = message
                        break
            else:
                # When it's a link to a full thread, compare against `message_ts`
                for message in messages:
                    if message['ts'] == message_ts:
                        tagged_message = message
                        break
            
            if not tagged_message:
                self.logger.error(f"No matching message found for the timestamp: {thread_ts if is_thread else message_ts}")
                return f"No exact message found for the given Slack link: {link}"

            
            # Process the message text and handle nested links recursively
            processed_messages = []
            for message in messages:
                processed_text = await self._process_slack_links_in_text(message['text'], depth + 1)
                message['text'] = processed_text
                processed_messages.append(message)

            # Format the content for display
            formatted_content = await self._format_message_content(processed_messages)

            # Fetch user info for the author of the exact message
            tagged_message_user_id = tagged_message.get('user', None)
            if tagged_message_user_id:
                user_name, user_email, _ = await self.get_user_info(tagged_message_user_id)
            else:
                user_name, user_email = 'Unknown', 'Unknown'

            # Create a metadata string for the source info, including the exact message information and config setting note
            metadata_str = (f"Source: {metadata['source_link']}\n"
                            f"Channel ID: {metadata['channel_id']}\n"
                            f"Thread ID: {metadata['thread_id']}\n"
                            f"Content Type: {content_type}\n")

            if tagged_message:
                # Include the content of the exact message that was referenced in the link, along with user info
                tagged_message_content = tagged_message.get('text', 'No content found')
                metadata_str += (f"Note: The exact message referenced in the link is tagged below.\n"
                                f"Message content: \"{tagged_message_content}\"\n"
                                f"Author: {user_name} (Email: {user_email})\n")

            # If the entire thread was retrieved due to the config, add an explanation
            if self.global_manager.bot_config.GET_ALL_THREAD_FROM_MESSAGE_LINKS and is_thread:
                metadata_str += "Note: Due to the configuration settings, the entire thread was retrieved for analysis.\n"

            # Combine the metadata and formatted message content
            full_message_text = (f"\n[Automated Response] Slack link content (depth {depth}):\n"
                                f"{metadata_str}\n\n"
                                f"{formatted_content}")

            return full_message_text

        except ValueError as ve:
            self.logger.error(f"Invalid Slack URL: {link}. Error: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to process Slack link: {link}. Error: {str(e)}", exc_info=True)
            raise

            
    async def _process_slack_links_in_text(self, text, depth):
        #
        matches = re.findall(r'<(https:\/\/[a-zA-Z0-9\.]+\.slack\.com\/archives\/[^|>]+)(?:\|([^>]+))?>', text)

        for match in matches:
            full_url = match[0]
            display_url = match[1] if len(match) > 1 else full_url
            
            try:
                linked_content = await self._process_single_slack_link(full_url, "", "", "", depth=depth)
                # Remplacer le lien Slack original par le contenu traité
                text = text.replace(f'<{full_url}|{display_url}>', f"[Linked content: {linked_content}]")
                text = text.replace(f'<{full_url}>', f"[Linked content: {linked_content}]")  # Pour les cas sans texte d'affichage
            except Exception as e:
                self.logger.error(f"Failed to process nested Slack link: {full_url}. Error: {e}", exc_info=True)
                # Remplacer le lien par un message d'erreur
                error_message = f"[Failed to retrieve content for Slack link: {full_url}]"
                text = text.replace(f'<{full_url}|{display_url}>', error_message)
                text = text.replace(f'<{full_url}>', error_message)

        return text

    async def _process_urls(self, text):
        urls = re.findall(r'<(http[s]?://[^|]+)', text)
        urls = list(set(urls))
        non_slack_urls = [url for url in urls if "slack.com" not in url]

        if self.global_manager.bot_config.GET_URL_CONTENT:
            final_texts = []
            for url in non_slack_urls:
                final_texts.append(await self._process_single_url(url))
            text += ''.join(final_texts)
        return text

    async def _process_single_url(self, url):
        if "slack.com/archives/" in url:
            try:
                match = re.search(r'archives/(?P<channel_id>[A-Z0-9]+)/p(?P<message_ts>\d+)(?:\?thread_ts=(?P<thread_ts>[\d.]+))?', url)
                if match:
                    channel_id = match.group('channel_id')
                    message_ts = f"{match.group('message_ts')[:10]}.{match.group('message_ts')[10:]}"
                    thread_ts = match.group('thread_ts')

                    messages = await self.global_manager.slack_output_handler.fetch_conversation_history(channel_id, thread_ts or message_ts)

                    if messages:
                        content = "\n".join([f"User: {msg.get('user', 'Unknown')}\nMessage: {msg.get('text', '')}" for msg in messages])
                        return f"The following text is the content of the Slack message or thread:\n{content}\n"
                    else:
                        return f"Unable to retrieve content for Slack URL: {url}"
                else:
                    return f"Invalid Slack URL format: {url}"
            except Exception as e:
                self.logger.error(f"Error processing Slack URL {url}: {e}")
                return f"Error processing Slack URL: {url}"
        else:
            try:
                webcontent = requests.get(url)
                webcontent.raise_for_status()
                soup = BeautifulSoup(webcontent.text, 'html.parser')
                content = soup.get_text()
                content = content.replace('\n', '')
                content = re.sub(' +', ' ', content)
                return f"The following text is an automated response inserted in the user conversation automatically giving the content of the URL in the user message: {content}\n"
            except requests.exceptions.RequestException as e:
                self.logger.error(f"An error occurred while trying to get {url}: {e}")
                return f"An error occurred while trying to get {url}: {e}\n"

    async def _create_event_data_instance(self, ts, channel_id, thread_id, response_id, user_id, app_id, api_app_id, username, is_mention, text, base64_images, files_content):
        converted_timestamp = await self.format_slack_timestamp(ts)
        user_name, user_email, _ = await self.get_user_info(user_id)
        event_label = "thread_message" if thread_id != ts else "message"

        caller_frame = inspect.currentframe().f_back
        caller_name = caller_frame.f_globals['__name__']
        return SlackEventData(
            timestamp=ts,
            converted_timestamp=converted_timestamp,
            event_label=event_label,
            channel_id=channel_id,
            thread_id=thread_id,
            response_id=response_id,
            user_name=user_name,
            username=username,
            user_email=user_email,
            user_id=user_id,
            app_id=app_id,
            api_app_id=api_app_id,
            is_mention=is_mention,
            text=text,
            images=base64_images,
            files_content=files_content,
            origin=caller_name,
            origin_plugin_name=self.slack_config.PLUGIN_NAME
        )

    async def format_slack_timestamp(self, slack_timestamp: str) -> str:
        # Convert Slack timestamp to UTC datetime
        timestamp_float = float(slack_timestamp)

        # Convert the Unix timestamp to a UTC datetime object
        utc_dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)

        # Define the Paris timezone
        paris_tz = ZoneInfo("Europe/Paris")

        # Convert UTC datetime to Paris time
        paris_dt = utc_dt.astimezone(paris_tz)

        # Format the datetime object to a readable string
        paris_time = paris_dt.strftime('%Y-%m-%d %H:%M:%S')
        return paris_time

    async def extract_info_from_url(self, message_url):
        match = re.search(
            r'https:\/\/[a-zA-Z0-9\.]+\.slack\.com\/archives\/(?P<channel_id>[A-Za-z0-9]+)\/p(?P<message_ts>\d+)(?:\?thread_ts=(?P<thread_ts>[\d.]+))?(?:&cid=(?P<cid>[A-Za-z0-9]+))?',
            message_url
        )

        if match:
            channel_id = match.group('channel_id')
            message_ts = f"{match.group('message_ts')[:10]}.{match.group('message_ts')[10:]}"
            thread_ts = match.group('thread_ts')

            if thread_ts:
                # This is a message within a thread
                return channel_id, thread_ts, message_ts, True
            else:
                # This is either an individual message or the start of a thread
                return channel_id, message_ts, None, False
        else:
            raise ValueError("Invalid Slack message URL")

    async def get_message_content(self, channel_id, message_ts, thread_ts=None, original_link=None):
        try:
            self.logger.debug(f"get_message_content called with: channel_id={channel_id}, message_ts={message_ts}, thread_ts={thread_ts}, original_link={original_link}")

            # Function to check if two timestamps match within a tolerance
            def ts_match(ts1, ts2, tolerance=0.001):
                return abs(float(ts1) - float(ts2)) < tolerance

            # If no thread_ts is provided, assume the message_ts is for the thread
            if thread_ts is None:
                thread_ts = message_ts

            self.logger.debug(f"Using thread_ts: {thread_ts}")

            # Fetch all messages in the thread
            data = await self._fetch_thread_messages(channel_id, thread_ts)
            messages = data.get('messages', [])
            self.logger.debug(f"Fetched {len(messages)} messages from thread")

            # Prepare metadata for the response
            metadata = {
                "source_link": original_link,
                "channel_id": channel_id,
                "thread_id": thread_ts,
                "is_full_thread": True  # Assume it's the full thread unless proven otherwise
            }

            # Case 1: If message_ts matches thread_ts, this is a request for the full thread
            if ts_match(message_ts, thread_ts):
                self.logger.debug(f"message_ts matches thread_ts, returning all thread messages")
                return {
                    "metadata": metadata,
                    "content_type": "full_thread",
                    "messages": messages
                }

            # Case 2: If message_ts does not match thread_ts, search for the specific message
            matching_messages = [m for m in messages if ts_match(m['ts'], message_ts)]

            # If the specific message is found, return just that message
            if matching_messages:
                self.logger.debug(f"Found {len(matching_messages)} matching messages")
                metadata["is_full_thread"] = False
                return {
                    "metadata": metadata,
                    "content_type": "single_message",
                    "messages": matching_messages
                }
            
            # Case 3: If no specific match is found, return the entire thread
            self.logger.debug("No exact match found. Returning all thread messages")
            return {
                "metadata": metadata,
                "content_type": "full_thread",
                "messages": messages
            }

        except Exception as e:
            self.logger.error(f"Error in get_message_content: {e}", exc_info=True)
            raise ValueError(f"Failed to retrieve message from Slack API: {str(e)}")
        
    async def _fetch_thread_messages(self, channel_id, thread_ts):
        url = f"{self.SLACK_API_URL}conversations.replies"
        params = {
            'channel': channel_id,
            'ts': thread_ts,
            'limit': 100
        }
        return await self._make_slack_api_call(url, params)

    async def _fetch_single_message(self, channel_id, message_ts):
        url = f"{self.SLACK_API_URL}conversations.history"
        params = {
            'channel': channel_id,
            'latest': message_ts,
            'limit': 1,
            'inclusive': 'true'  # Changé de True à 'true'
        }
        return await self._make_slack_api_call(url, params)
    

    async def _make_slack_api_call(self, url, params):
        headers = {'Authorization': f'Bearer {self.SLACK_BOT_USER_TOKEN}'}
        
        # Convertir tous les paramètres en chaînes
        params = {k: str(v) for k, v in params.items()}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_message = (await response.json()).get('error', 'Unknown error')
                    raise ValueError(f"Failed to retrieve message from Slack API: {error_message}")

                data = await response.json()
                if not data['ok']:
                    raise ValueError(f"Failed to retrieve message from Slack API: {data['error']}")

                return data
            
    async def _fetch_message_data(self, channel_id, message_ts, message_type):
        params = self._build_api_params(channel_id, message_ts, message_type)
        headers = {'Authorization': f'Bearer {self.SLACK_BOT_USER_TOKEN}'}
        
        endpoint = "conversations.replies" if message_type == "thread" else "conversations.history"
        url = f"{self.SLACK_API_URL}{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_message = (await response.json()).get('error', 'Unknown error')
                    raise ValueError(f"Failed to retrieve message from Slack API: {error_message}")

                data = await response.json()
                if not data['ok']:
                    raise ValueError(f"Failed to retrieve message from Slack API: {data['error']}")

                return data

    def _build_api_params(self, channel_id, message_ts, message_type):
        params = {
            'channel': channel_id,
            'limit': 100
        }
        if message_type == "thread":
            params['ts'] = message_ts
        else:
            params['latest'] = message_ts
            params['inclusive'] = True
            params['limit'] = 1
        return params

    def _extract_messages(self, response):
        return response.get('messages', [])

    async def get_bot_info(self, bot_id):
        try:
            response = await self.async_client.bots_info(bot=bot_id)
            if response['ok']:
                bot_info = response.get('bot', {})
                bot_name = bot_info.get('name', 'Unknown Bot')
                return bot_name
            else:
                self.logger.error(f"Failed to fetch bot info: {response.get('error', 'Unknown error')}")
        except Exception as e:
            self.logger.error(f"Error fetching bot info: {e}")
        return 'Unknown Bot'

    async def _format_message_content(self, messages):
        formatted_messages = []
        for message in messages:
            if message is None:
                continue

            # Extract user_id and check if it's a bot message
            user_id = message.get('user', 'Unknown')
            subtype = message.get('subtype', '')

            # Handle bot message case
            if subtype == 'bot_message':
                bot_id = message.get('bot_id', 'Unknown')
                if bot_id != 'Unknown':
                    # Fetch bot info using bot_id
                    bot_name = await self.get_bot_info(bot_id)
                    username = bot_name
                    user_email = 'Bot/App (No email)'
                else:
                    username = 'Unknown Bot'
                    user_email = 'Unknown'
            else:
                username, user_email, _ = await self.get_user_info(user_id)
                
            # Format the message timestamp
            timestamp = await self.format_slack_timestamp(message.get('ts', ''))

            # Check if the message directly mentions the bot
            is_mention = f"<@{self.SLACK_BOT_USER_ID}>" in message.get('text', '')

            # Extract text content
            text = message.get('text', '')
            if 'blocks' in message:
                block = message["blocks"]
                slack_block_processor = SlackBlockProcessor()
                text = slack_block_processor.extract_text_from_blocks(blocks=block)

            # Format the message content
            formatted_message = (
                f"Timestamp: {timestamp}\n"
                f"[Slack username]: {username}\n"
                f"[Slack user id]: {user_id if subtype != 'bot_message' else bot_id}\n"
                f"[Slack user email]: {user_email}\n"
                f"[Directly mentioning you]: {is_mention}\n"
                f"[Message]: {text}\n"
            )
            formatted_messages.append(formatted_message)

        return "\n".join(formatted_messages)
    
    async def download_image_as_byte_array(self, image_url):
        slack_token = os.environ.get('SLACK_BOT_TOKEN')
        headers = {'Authorization': f'Bearer {slack_token}'}
        response = requests.get(image_url, headers=headers, stream=True)
        if response.status_code == 200:
            return response.content  # Return bytes object
        else:
            print(f"Failed to download image: {response.status_code}, {response.text}")
            return None

    async def download_file_content(self, file_url):
        headers = {'Authorization': 'Bearer ' + self.SLACK_BOT_TOKEN}
        response = requests.get(file_url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            self.logger.error(f"Error downloading file: {response.status_code}")
            return None

    async def search_message_in_thread(self, query):
        try:
            userclient = WebClient(token=self.SLACK_BOT_USER_TOKEN)
            response = userclient.search_messages(query=query)
            messages = response['messages']['matches']

            for message in messages:
                channel_id = message['channel']['id']
                thread_id = message.get('ts')  # Not all messages will have a thread_id

                if thread_id:  # If the message has a thread_id, return it
                    return thread_id

        except Exception as e:
            self.logger.error(f"Error searching for message: {e}", exc_info=True)

        return None

    async def get_message_permalink_and_text(self, channel_id, message_ts):
        try:
            response = await self.async_client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
            if response['ok']:
                permalink = response['permalink']

                # Extract the linked message's ts from the permalink
                path_elements = permalink.split('/')
                channel = path_elements[4]

                if 'thread_id' in permalink:
                    # Threaded message, use conversations.replies endpoint
                    ts = path_elements[5].split('?')[0]
                    ts = ts[:len(ts)-6] + '.' + ts[len(ts)-6:]

                    latest = path_elements[5].split('thread_id=')[1].split('&')[0]

                    message_response = await self.async_client.conversations_replies(channel=channel, ts=ts, latest=latest, inclusive=True, limit=1)
                else:
                    # Non-threaded message, use conversations.history endpoint
                    latest = path_elements[5][1:]
                    if '?' in latest:
                        latest = latest.split('?')[0]

                    # Convert the timestamp to the correct format
                    latest = str(float(latest) / 1000000)

                    message_response = await self.async_client.conversations_history(channel=channel, latest=latest, inclusive=True, limit=1)

                messages = message_response.get('messages')
                
                if messages:
                    # Get the user's name
                    if "user" in messages[0] and (self.SLACK_AUTHORIZED_APPS[0] == "" or not any(str(app_id) in str(messages) for app_id in self.SLACK_AUTHORIZED_APPS)):
                        self.logger.info(f"user:{messages} ")
                        user_id = messages[0]['user']
                        user_info_response = await self.async_client.users_info(user=user_id)
                        if user_info_response['ok']:
                            user_name = user_info_response['user']['name']
                            message_text = f"*{user_name}*: _{messages[0]['text']}_"  # Prepend the user's name to the message and format it
                            return permalink, message_text
                    if "username" in messages[0]:
                        self.logger.info(f"app:{messages} ")
                        username = messages[0]['username']
                        message_text = f"*{username}*: _{messages[0]['text']}_"  # Prepend the app's name to the message and format it
                        return permalink, message_text
                    return permalink, messages[0].get('text', '')

            self.logger.error(f"Error getting permalink: {response.get('error')}")
            return None, None
        except Exception as e:
            self.logger.error(f"Exception in get_message_permalink_and_text: {e}")
            return None, None