from typing import List, Dict, Optional, Tuple
from core.backend.internal_data_processing_base import InternalDataProcessingBase

class MockInternalDataProcessing(InternalDataProcessingBase):
    def __init__(self):
        self._sessions = {}
        self._messages = {}
        self._feedbacks = {}
        self._concatenate = {}
        self._prompts = {}
        self._costs = {}
        self._abort = {}
        self._processing = {}
        self._vectors = {}
        self._subprompts = {}
        self._custom_actions = {}
        self._messages_queue = []

    @property
    def sessions(self):
        return self._sessions

    @property
    def messages(self):
        return self._messages

    @property
    def feedbacks(self):
        return self._feedbacks

    @property
    def concatenate(self):
        return self._concatenate

    @property
    def prompts(self):
        return self._prompts

    @property
    def costs(self):
        return self._costs

    @property
    def abort(self):
        return self._abort

    @property
    def processing(self):
        return self._processing

    @property
    def vectors(self):
        return self._vectors

    @property
    def subprompts(self):
        return self._subprompts

    @property
    def custom_actions(self):
        return self._custom_actions

    @property
    def messages_queue(self):
        return self._messages_queue

    def append_data(self, container_name: str, data_identifier: str, data: str) -> None:
        if container_name not in self._messages:
            self._messages[container_name] = {}
        self._messages[container_name][data_identifier] = data

    async def read_data_content(self, data_container, data_file):
        return self._messages.get(data_container, {}).get(data_file, "")

    async def write_data_content(self, data_container, data_file, data):
        if data_container not in self._messages:
            self._messages[data_container] = {}
        self._messages[data_container][data_file] = data

    async def update_pricing(self, container_name, datafile_name, pricing_data):
        if container_name not in self._costs:
            self._costs[container_name] = {}
        self._costs[container_name][datafile_name] = pricing_data

    async def update_prompt_system_message(self, channel_id, thread_id, message):
        if channel_id not in self._prompts:
            self._prompts[channel_id] = {}
        self._prompts[channel_id][thread_id] = message

    async def update_session(self, data_container, data_file, role, content):
        if data_container not in self._sessions:
            self._sessions[data_container] = {}
        self._sessions[data_container][data_file] = {"role": role, "content": content}

    async def remove_data_content(self, data_container, data_file):
        if data_container in self._messages and data_file in self._messages[data_container]:
            del self._messages[data_container][data_file]

    async def list_container_files(self, container_name):
        return list(self._messages.get(container_name, {}).keys())

    async def enqueue_message(self, channel_id: str, thread_id: str, message: str) -> None:
        self._messages_queue.append((channel_id, thread_id, message))

    async def dequeue_message(self, channel_id: str, thread_id: str, message_id: str) -> None:
        self._messages_queue = [msg for msg in self._messages_queue if msg[2] != message_id]

    async def get_next_message(self, channel_id: str, thread_id: str) -> Tuple[Optional[str], Optional[str]]:
        for msg in self._messages_queue:
            if msg[0] == channel_id and msg[1] == thread_id:
                return msg[2], msg[2]
        return None, None

    async def has_older_messages(self, channel_id: str, thread_id: str) -> bool:
        return any(msg for msg in self._messages_queue if msg[0] == channel_id and msg[1] == thread_id)