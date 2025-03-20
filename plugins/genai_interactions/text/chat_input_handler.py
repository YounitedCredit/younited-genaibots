import asyncio
import datetime
import json
import traceback
import uuid
from datetime import datetime, timezone

import yaml

from core.backend.pricing_data import PricingData
from core.genai_interactions.genai_cost_base import GenAICostBase
from core.genai_interactions.genai_interactions_text_plugin_base import (
    GenAIInteractionsTextPluginBase,
)
from core.global_manager import GlobalManager
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from utils.config_manager.config_model import BotConfig
from utils.plugin_manager.plugin_manager import PluginManager


class ChatInputHandler():
    def __init__(self, global_manager: GlobalManager, chat_plugin: GenAIInteractionsTextPluginBase):
        self.global_manager: GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugin_manager: PluginManager = global_manager.plugin_manager
        self.chat_plugin: GenAIInteractionsTextPluginBase = chat_plugin
        self.bot_config = self.global_manager.bot_config
        # Dispatchers
        self.user_interaction_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher
        self.session_manager_dispatcher = self.global_manager.session_manager_dispatcher

    def initialize(self):
        self.genai_client = {}
        self.bot_config: BotConfig = self.global_manager.bot_config
        self.conversion_format = self.bot_config.LLM_CONVERSION_FORMAT

    async def handle_event_data(self, event_data: IncomingNotificationDataBase):
        try:
            if event_data.event_label == 'message':
                return await self.handle_message_event(event_data)
            elif event_data.event_label == 'thread_message':
                return await self.handle_thread_message_event(event_data)
            else:
                raise ValueError(f"Unknown event label: {event_data.event_label}")
        except Exception as e:
            self.logger.error(f"Error while handling event data: {e}")
            raise

    def format_timestamp(self, timestamp: str) -> str:
        # Convert timestamp to UTC datetime
        timestamp_float = float(timestamp)
        utc_dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
        formatted_time = utc_dt.strftime('%Y-%m-%d %H:%M:%S')
        return formatted_time

    async def handle_message_event(self, event_data: IncomingNotificationDataBase):
        try:
            # Récupérer ou créer la session
            session = await self.global_manager.session_manager_dispatcher.get_or_create_session(
                channel_id=event_data.channel_id,
                thread_id=event_data.thread_id or event_data.timestamp,  # Utiliser timestamp si thread_id est None
                enriched=True
            )

            # Récupérer les messages de la session
            messages = session.messages

            # Si la session n'a pas de messages, l'initialiser avec un message système enrichi
            if not messages:
                # Obtenir le core prompt et le main prompt du prompt manager
                feedbacks_container = self.backend_internal_data_processing_dispatcher.feedbacks
                general_behavior_content = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    feedbacks_container, self.bot_config.FEEDBACK_GENERAL_BEHAVIOR
                )
                await self.global_manager.prompt_manager.initialize()

                # Récupérer les noms et contenus des prompts
                core_prompt_name = self.global_manager.bot_config.CORE_PROMPT
                core_prompt = self.global_manager.prompt_manager.core_prompt
                main_prompt_name = self.global_manager.bot_config.MAIN_PROMPT
                main_prompt = self.global_manager.prompt_manager.main_prompt

                # Extraire les versions des prompts
                core_prompt_version = self.extract_version(core_prompt)
                main_prompt_version = self.extract_version(main_prompt)

                # Construire le contenu du message système avec les prompts dans l'ordre souhaité
                system_content = f"{core_prompt}\n{main_prompt}"

                if general_behavior_content:
                    system_content += f"\nAlso take into account these previous general behavior feedbacks: {str(general_behavior_content)}"

                # Créer le message système avec les nouvelles données de prompt et les versions
                system_message = {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_content
                        }
                    ],
                    "core_prompt_name": core_prompt_name,
                    "core_prompt": core_prompt,
                    "core_prompt_version": core_prompt_version,
                    "main_prompt_name": main_prompt_name,
                    "main_prompt": main_prompt,
                    "main_prompt_version": main_prompt_version,
                    "timestamp": datetime.now().isoformat()  # Ajout d'un timestamp pour le message système
                }

                # Ajouter le message système aux messages de la session
                self.session_manager_dispatcher.append_messages(messages, system_message, session.session_id)

            # Construire le message utilisateur
            constructed_message = self.construct_message(event_data)
            self.session_manager_dispatcher.append_messages(messages, constructed_message, session.session_id)

            # Mettre à jour les messages de la session et sauvegarder la session
            session.messages = messages
            await self.global_manager.session_manager_dispatcher.save_session(session)

            return await self.generate_response(event_data, session)
        except Exception as e:
            self.logger.error(f"Error while handling message event: {e}")
            raise

    def extract_version(self, prompt: str) -> str:
        """
        Extrait la version d'un prompt à partir de sa première ligne formatée comme '# VERSION 3c7REARE'.
        Si le format n'est pas respecté, retourne 'Unknown'.
        """
        try:
            first_line = prompt.split('\n')[0].strip()
            if first_line.startswith("# VERSION"):
                return first_line.split("# VERSION")[-1].strip()
            else:
                return "Unknown"
        except Exception as e:
            self.logger.error(f"Error extracting version from prompt: {e}")
            return "Unknown"

    async def handle_thread_message_event(self, event_data: IncomingNotificationDataBase):
        try:
            # Récupérer ou créer la session
            session = await self.global_manager.session_manager_dispatcher.get_or_create_session(
                channel_id=event_data.channel_id,
                thread_id=event_data.thread_id,
                enriched=True
            )

            # Récupérer l'historique des messages de la session
            messages = session.messages
            was_messages_empty = not messages

            # Si l'utilisateur n'est pas le bot, traiter l'historique de la conversation
            if event_data.user_id != "AUTOMATED_RESPONSE":
                await self.process_conversation_history(event_data, session)

            # Si les messages étaient initialement vides, ajouter le message système initial
            if was_messages_empty:
                feedbacks_container = self.backend_internal_data_processing_dispatcher.feedbacks
                general_behavior_content = await self.backend_internal_data_processing_dispatcher.read_data_content(
                    feedbacks_container, self.bot_config.FEEDBACK_GENERAL_BEHAVIOR
                )
                await self.global_manager.prompt_manager.initialize()

                core_prompt = self.global_manager.prompt_manager.core_prompt
                main_prompt = self.global_manager.prompt_manager.main_prompt
                init_prompt = f"{core_prompt}\n{main_prompt}"

                if general_behavior_content:
                    init_prompt += f"\nAlso take into account these previous general behavior feedbacks: {str(general_behavior_content)}"

                # Ajouter le message système aux messages
                system_message = {"role": "system", "content": [
                    {
                        "type": "text",
                        "text": init_prompt
                    }
                ]}
                messages.insert(0, system_message)

            # Construire le message utilisateur
            constructed_message = self.construct_message(event_data)
            self.session_manager_dispatcher.append_messages(messages, constructed_message, session.session_id)

            # Mettre à jour les messages de la session et sauvegarder la session
            session.messages = messages
            await self.global_manager.session_manager_dispatcher.save_session(session)

            return await self.generate_response(event_data, session)
        except Exception as e:
            self.logger.error(f"Error while handling thread message event: {e}")
            raise

    async def process_conversation_history(self, event_data: IncomingNotificationDataBase, session):
        try:
            # Récupérer et traiter l'historique de la conversation
            relevant_events = []
            current_event_timestamp = datetime.fromtimestamp(float(event_data.timestamp), tz=timezone.utc)

            try:
                conversation_history = await self.user_interaction_dispatcher.fetch_conversation_history(
                    event=event_data)
            except Exception as e:
                self.logger.error(f"Error fetching conversation history: {e}")
                return

            if not conversation_history:
                self.logger.warning(
                    f"No conversation history found for channel {event_data.channel_id}, thread {event_data.thread_id}")
                return

            try:
                if not session.messages:
                    self.logger.info("No messages found, taking all conversation history as relevant events.")
                    relevant_events.extend(conversation_history)
                else:
                    last_message_timestamp_str = self.get_last_user_message_timestamp(session.messages)
                    if last_message_timestamp_str is None:
                        last_message_timestamp = datetime.fromtimestamp(0, tz=timezone.utc)
                    else:
                        last_message_timestamp = datetime.fromtimestamp(float(last_message_timestamp_str),
                                                                        tz=timezone.utc)
                    if last_message_timestamp.tzinfo is None:
                        last_message_timestamp = last_message_timestamp.replace(tzinfo=timezone.utc)

                    bot_id = self.user_interaction_dispatcher.get_bot_id(plugin_name=event_data.origin_plugin_name)

                    for past_event in conversation_history:
                        try:
                            past_event_timestamp = datetime.fromtimestamp(float(past_event.timestamp), tz=timezone.utc)
                            if last_message_timestamp < past_event_timestamp < current_event_timestamp:
                                if past_event_timestamp != current_event_timestamp and past_event.user_id != bot_id and "AUTOMATED_RESPONSE" not in past_event.text:
                                    self.logger.info(
                                        f"Processing past event: channel_id={past_event.channel_id}, "
                                        f"thread_id={past_event.thread_id}, timestamp={past_event.timestamp}"
                                    )
                                    relevant_events.append(past_event)
                        except Exception as e:
                            self.logger.error(f"Error processing past event: {e}")
            except Exception as e:
                self.logger.error(f"Error getting last user message timestamp: {e}")
                return

            # Convertir les événements pertinents en messages et les ajouter aux messages de la session
            try:
                converted_messages = self.convert_events_to_messages(relevant_events, session.session_id)
                # Trier les messages par timestamp
                converted_messages.sort(key=lambda x: float(x.get('timestamp', datetime.now().timestamp())))
                # Ajouter aux messages de la session
                for message in converted_messages:
                    self.global_manager.session_manager_dispatcher.append_messages(session.messages, message,
                                                                                   session.session_id)
                await self.global_manager.session_manager_dispatcher.save_session(session)
            except Exception as e:
                self.logger.error(f"Error converting events to messages: {e}")

        except Exception as e:
            self.logger.error(f"Unexpected error in process_conversation_history: {e}")

    def get_last_user_message_timestamp(self, messages):
        # Obtenir le timestamp du dernier message utilisateur dans les messages stockés
        for message in reversed(messages):
            if message["role"] == "user":
                return message.get("timestamp")
        return None

    def convert_events_to_messages(self, events, session_id):
        # Convertir les événements de l'historique de conversation en format de message approprié
        messages = []
        for event in events:
            self.session_manager_dispatcher.append_messages(messages, self.construct_message(event), session_id)
        return messages

    def construct_message(self, event_data):
        # Construire le message utilisateur à partir de event_data
        format_timestamp = str(event_data.timestamp)
        constructed_message_content = f"Timestamp: {str(format_timestamp)}, [Human readable date]:{str(datetime.fromtimestamp(float(event_data.timestamp)))}, [username]: {str(event_data.user_name)}, [user id]: {str(event_data.user_id)}, [user email]: {event_data.user_email}, [Directly mentioning you]: {str(event_data)}, [message]: {str(event_data.text)}"

        # Formater le contenu avec des images et des fichiers supplémentaires si applicable
        user_content_text = [{"type": "text", "text": constructed_message_content}]
        user_content_images = []

        if event_data.images:
            for base64_image in event_data.images:
                user_content_images.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                })

        if event_data.files_content:
            for file_content in event_data.files_content:
                user_content_text.append({"type": "text", "text": file_content})

        # Ajouter le champ is_automated basé sur user_name
        is_automated = True if event_data.user_id == "AUTOMATED_RESPONSE" else False

        # Inclure event_data sous forme de JSON
        event_data_json = event_data.to_dict()

        return {
            "role": "user",
            "content": user_content_text + user_content_images,
            "timestamp": event_data.timestamp,
            "event_data": event_data_json,
            "is_automated": is_automated  # Nouveau champ ajouté
        }

    async def generate_response(self, event_data: IncomingNotificationDataBase, session):
        completion = None  # Initialiser à None
        try:
            original_msg_ts = event_data.thread_id if event_data.thread_id else event_data.timestamp
            messages = session.messages

            # Traiter l'événement
            self.logger.info("GENAI CALL: Calling Generative AI completion for user input..")
            await self.global_manager.user_interactions_behavior_dispatcher.begin_genai_completion(
                event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp)

            # Enregistrer le temps de début
            start_time = datetime.now()

            completion = await self.call_completion(
                event_data.channel_id, original_msg_ts, messages, event_data, session)

            await self.global_manager.user_interactions_behavior_dispatcher.end_genai_completion(
                event=event_data, channel_id=event_data.channel_id, timestamp=event_data.timestamp)

            # Enregistrer le temps de fin
            end_time = datetime.now()

            # Calculer le temps de génération en millisecondes
            generation_time_ms = (end_time - start_time).total_seconds() * 1000

            # Ajouter le temps de génération au total de la session
            if not hasattr(session, 'total_time_ms'):
                session.total_time_ms = 0.0
            session.total_time_ms += generation_time_ms

            # Sauvegarder la session après mise à jour du temps total
            await self.global_manager.session_manager_dispatcher.save_session(session)

            return completion
        except Exception as e:
            self.logger.error(f"Error while generating response: {e}\n{traceback.format_exc()}")
            raise

    async def filter_messages(self, messages):
        filtered_messages = []
        for message in messages:
            # Si le message provient de l'utilisateur et que son contenu est une liste, nous filtrons le contenu 'image_url'
            if message['role'] == 'user' and isinstance(message['content'], list):
                filtered_content = [content for content in message['content'] if content['type'] != 'image_url']
                message['content'] = filtered_content
            filtered_messages.append(message)
        return filtered_messages

    async def call_completion(self, channel_id, thread_id, messages, event_data: IncomingNotificationDataBase, session):
        try:
            # Enregistrer le temps de début
            start_time = datetime.now()

            # Appeler le modèle génératif AI pour obtenir la complétion
            completion, genai_cost_base = await self.chat_plugin.generate_completion(messages, event_data)

            # Enregistrer le temps de fin
            end_time = datetime.now()

            # Calculer le temps de génération en secondes
            generation_time = (end_time - start_time).total_seconds()

            # Convertir le temps de génération en millisecondes
            generation_time_ms = generation_time * 1000

        except asyncio.exceptions.CancelledError:
            await self.user_interaction_dispatcher.send_message(event=event_data, message="Task was cancelled",
                                                                message_type=MessageType.COMMENT, is_internal=True)
            self.logger.error("Task was cancelled")
            return None
        except Exception as e:
            return await self.handle_completion_errors(event_data, e)

        self.logger.info("Completion from generative AI received")

        # Extraire la réponse de GenAI
        costs_container = self.backend_internal_data_processing_dispatcher.costs

        await self.calculate_and_update_costs(genai_cost_base, costs_container, session.session_id, event_data, session)

        # Étape 1 : Supprimer les marqueurs
        gpt_response = completion.replace("[BEGINIMDETECT]", "").replace("[ENDIMDETECT]", "")

        # Étape 2 : Enregistrer la réponse brute de GenAI pour le débogage
        await self.user_interaction_dispatcher.upload_file(event=event_data, file_content=gpt_response,
                                                           filename="Genai_response_raw.yaml",
                                                           title="Genai response file", is_internal=True)

        try:
            # Étape 3 : Gestion de la conversion JSON ou YAML
            if self.conversion_format == "json":
                # Supprimer les sauts de ligne initiaux/finals
                gpt_response = gpt_response.strip("\n")

                # Tenter de parser la réponse en JSON
                response_json = json.loads(gpt_response)

            elif self.conversion_format == "yaml":
                sanitized_yaml = self.adjust_yaml_structure(gpt_response)
                response_json = await self.yaml_to_json(event_data=event_data, yaml_string=sanitized_yaml)

            else:
                # Enregistrer un avertissement et retourner None
                self.logger.error(f"Invalid conversion format: {self.conversion_format}, cannot parse the response.")
                return None

        except json.JSONDecodeError as e:
            # Étape 5 : Gérer et signaler les erreurs de décodage JSON
            await self.user_interaction_dispatcher.send_message(event=event_data,
                                                                message=f"An error occurred while converting the completion: {e}",
                                                                message_type=MessageType.COMMENT, is_internal=True)
            await self.user_interaction_dispatcher.send_message(event=event_data,
                                                                message="Oops something went wrong, try again or contact the bot owner",
                                                                message_type=MessageType.COMMENT)
            self.logger.error(f"Failed to parse JSON: {e}")
            return None

        # Calculer les coûts
        input_cost = (genai_cost_base.prompt_tk / 1000) * genai_cost_base.input_token_price
        output_cost = (genai_cost_base.completion_tk / 1000) * genai_cost_base.output_token_price
        total_cost = input_cost + output_cost

        # Mettre à jour les messages de la session avec la réponse de l'assistant
        assistant_message = {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": completion
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "actions": self.extract_actions(response_json),
            "cost": {
                "total_tokens": genai_cost_base.total_tk,
                "prompt_tokens": genai_cost_base.prompt_tk,
                "completion_tokens": genai_cost_base.completion_tk,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost
            },
            "plugin_name": self.chat_plugin.plugin_name,
            "model_name": self.chat_plugin.model_name,
            "generation_time_ms": generation_time_ms,
            "from_action": False,
            "assistant_message_guid": str(uuid.uuid4())
        }

        self.session_manager_dispatcher.append_messages(session.messages, assistant_message, session.session_id)

        # Mettre à jour le temps total de génération dans la session
        if not hasattr(session, 'total_ms'):
            session.total_ms = 0.0
        session.total_ms += generation_time_ms

        # Sauvegarder la session mise à jour
        await self.global_manager.session_manager_dispatcher.save_session(session)

        return response_json

    def extract_actions(self, response_json):
        """
        Extrait les actions de la réponse JSON en s'assurant que les paramètres sont correctement dissociés.
        """
        actions = response_json.get('response', [])
        extracted_actions = []
        for action_item in actions:
            action = action_item.get('Action', {})
            action_name = action.get('ActionName', '')
            parameters = action.get('Parameters', {})
            # Assurer que les paramètres sont un dictionnaire avec des noms de paramètres distincts
            if isinstance(parameters, dict):
                extracted_parameters = parameters
            else:
                extracted_parameters = {}
            extracted_actions.append({
                "ActionName": action_name,
                "Parameters": extracted_parameters
            })
        return extracted_actions

    async def handle_completion_errors(self, event_data, e):
        await self.user_interaction_dispatcher.send_message(event=event_data,
                                                            message=f"An error occurred while calling the completion: {e}",
                                                            message_type=MessageType.COMMENT, is_internal=True)
        error_message = str(e)
        start = error_message.find('\'message\': "') + 12
        end = error_message.find('", \'param\':', start)
        sanitized_message = error_message[start:end]
        sanitized_message = sanitized_message.replace('\\r\\n', ' ')
        await self.user_interaction_dispatcher.send_message(event=event_data,
                                                            message=f":warning: Sorry, I was unable to analyze the content you provided: {sanitized_message}",
                                                            message_type=MessageType.COMMENT, is_internal=False)
        self.logger.error(f"Failed to create completion: {e}")
        return None

    def adjust_yaml_structure(self, yaml_content):
        lines = yaml_content.split('\n')
        adjusted_lines = []
        inside_parameters_block = False
        multiline_literal_indentation = 0
        current_indentation_level = 0

        for line in lines:
            # Si nous sommes à l'intérieur d'un bloc multiligne, nous vérifions le niveau d'indentation
            if multiline_literal_indentation > 0 and not line.startswith(' ' * multiline_literal_indentation):
                # Nous avons atteint la fin du bloc multiligne
                multiline_literal_indentation = 0

            stripped_line = line.strip()

            # Échapper les astérisques dans la chaîne YAML (uniquement en dehors des blocs multiligne)
            if multiline_literal_indentation == 0:
                stripped_line = stripped_line.replace('*', '\\*')

            # Pas d'espaces en début pour 'response:'
            if stripped_line.startswith('response:'):
                adjusted_lines.append(stripped_line)
                inside_parameters_block = False
                current_indentation_level = 0

            # 2 espaces avant '- Action:'
            elif stripped_line.startswith('- Action:'):
                adjusted_lines.append('  ' + stripped_line)
                inside_parameters_block = False
                current_indentation_level = 2

            # 6 espaces avant 'ActionName:' ou 'Parameters:'
            elif stripped_line.startswith('ActionName:') or stripped_line.startswith('Parameters:'):
                adjusted_lines.append('      ' + stripped_line)
                inside_parameters_block = stripped_line.startswith('Parameters:')
                current_indentation_level = 6

            # Commence une valeur multiligne
            elif inside_parameters_block and stripped_line.endswith(': |'):
                adjusted_lines.append(' ' * (current_indentation_level + 2) + stripped_line)
                multiline_literal_indentation = current_indentation_level + 4  # Augmenter l'indentation pour le contenu multiligne

            # Gérer les lignes à l'intérieur d'un bloc multiligne
            elif multiline_literal_indentation > 0:
                adjusted_lines.append(line)

            # Lignes de valeur de paramètre régulières sous 'Parameters:'
            elif inside_parameters_block and ':' in stripped_line:
                adjusted_lines.append(' ' * (current_indentation_level + 2) + stripped_line)
                if stripped_line.endswith(':'):
                    # Augmenter le niveau d'indentation pour les dictionnaires imbriqués
                    current_indentation_level += 2

            # Diminuer l'indentation en quittant un bloc imbriqué
            elif inside_parameters_block and not stripped_line:
                current_indentation_level = max(current_indentation_level - 2, 6)
                adjusted_lines.append(line)

            # Garder l'indentation originale pour tout le reste
            else:
                adjusted_lines.append(line)

        # Reconstruire le contenu YAML ajusté
        adjusted_yaml_content = '\n'.join(adjusted_lines)
        return adjusted_yaml_content

    async def yaml_to_json(self, event_data, yaml_string):
        try:
            # Charger la chaîne YAML dans un dictionnaire Python
            python_dict = yaml.safe_load(yaml_string)

            # Vérifier si 'value' contient une chaîne YAML et la charger
            for action in python_dict.get('response', []):
                if 'value' in action['Action']['Parameters']:
                    value_str = action['Action']['Parameters']['value']

                    # Traiter uniquement si value_str est une chaîne et formatée en YAML
                    if isinstance(value_str, str) and value_str.strip().startswith(
                            '```yaml') and value_str.strip().endswith('```'):
                        # Supprimer la syntaxe du bloc de code markdown
                        yaml_str = value_str.strip()[7:-3].strip()
                        # Parser le contenu YAML
                        action['Action']['Parameters']['value'] = yaml.safe_load(yaml_str)

            return python_dict
        except Exception as e:
            self.logger.error(f"An error occurred while processing the YAML string: {str(e)}")
            self.logger.error(traceback.format_exc())
            await self.user_interaction_dispatcher.send_message(
                event=event_data,
                message=f"An error occurred while processing the YAML string: {str(e)}\nTraceback:\n{traceback.format_exc()}",
                message_type=MessageType.COMMENT,
                is_internal=True
            )
            await self.user_interaction_dispatcher.send_message(
                event=event_data,
                message="😓 Sorry something went wrong with this thread formatting. Create a new thread and try again! (consult logs for deeper infos)",
                message_type=MessageType.TEXT,
                is_internal=False
            )
            return None

    async def calculate_and_update_costs(self, cost_params: GenAICostBase, costs_blob_container_name, blob_name,
                                         event: IncomingNotificationDataBase, session):
        # Initialiser total_cost, input_cost et output_cost à 0
        total_cost = input_cost = output_cost = 0

        try:
            # Extraire les détails d'utilisation des tokens de la réponse GPT
            total_tk = cost_params.total_tk
            prompt_tk = cost_params.prompt_tk
            completion_tk = cost_params.completion_tk

            # S'assurer que prompt_tk et input_token_price sont des flottants
            prompt_tk = float(prompt_tk)
            input_token_price = float(cost_params.input_token_price)
            output_token_price = float(cost_params.output_token_price)

            # Calculer les coûts
            input_cost = (prompt_tk / 1000) * input_token_price
            output_cost = (completion_tk / 1000) * output_token_price
            total_cost = input_cost + output_cost

            # Créer un objet pricing data
            pricing_data = PricingData(
                total_tokens=total_tk,
                prompt_tokens=prompt_tk,
                completion_tokens=completion_tk,
                total_cost=total_cost,
                input_cost=input_cost,
                output_cost=output_cost
            )

            # Mettre à jour le coût cumulatif dans le backend
            updated_pricing_data = await self.backend_internal_data_processing_dispatcher.update_pricing(
                container_name=costs_blob_container_name,
                datafile_name=blob_name,
                pricing_data=pricing_data
            )

            # Accumuler le coût dans la session
            session.accumulate_cost({
                "total_tokens": total_tk,
                "total_cost": total_cost
            })

            # Sauvegarder la session pour mettre à jour total_cost
            await self.global_manager.session_manager_dispatcher.save_session(session)

            cost_update_msg = (
                f"🔹 Last: {total_tk} tk {total_cost:.4f}$ "
                f"[🔼 {input_cost:.4f}$ {prompt_tk} tk "
                f"🔽 {output_cost:.4f}$/{completion_tk} tk] | "
                f"💰 Total: {session.total_cost['total_cost']:.4f}$ "
                f"[🔼 cumulative tokens: {session.total_cost['total_tokens']}]"
            )

            if self.global_manager.bot_config.SHOW_COST_IN_THREAD:
                await self.user_interaction_dispatcher.send_message(
                    event=event,
                    message=cost_update_msg,
                    message_type=MessageType.COMMENT,
                    is_internal=False
                )
            else:
                await self.user_interaction_dispatcher.send_message(
                    event=event,
                    message=cost_update_msg,
                    message_type=MessageType.COMMENT,
                    is_internal=True
                )

        except Exception as e:
            self.logger.error(f"An error occurred in method 'calculate_and_update_costs': {type(e).__name__}: {e}")

        return total_cost, input_cost, output_cost
