# test_internal_data_processing_base.py

from unittest.mock import AsyncMock

import pytest

from core.backend.internal_data_processing_base import InternalDataProcessingBase


class MockInternalDataProcessing(InternalDataProcessingBase):    
    def __init__(self):
        self._data = {
            "sessions": [],
            "messages": [],
            "feedbacks": [],
            "concatenate": [],
            "prompts": [],
            "costs": [],
            "abort": False,
            "processing": [],
            "vectors": [],
            "subprompts": []  # Ajout de la propriété subprompts
        }
        self._plugin_name = "MockInternalDataProcessor"

    # Propriétés avec implémentation de getters
    @property
    def sessions(self):
        return self._data["sessions"]

    @property
    def messages(self):
        return self._data["messages"]

    @property
    def feedbacks(self):
        return self._data["feedbacks"]

    @property
    def concatenate(self):
        return self._data["concatenate"]

    @property
    def prompts(self):
        return self._data["prompts"]

    @property
    def costs(self):
        return self._data["costs"]

    @property
    def abort(self):
        return self._data["abort"]

    @property
    def processing(self):
        return self._data["processing"]

    @property
    def vectors(self):
        return self._data["vectors"]

    @property
    def subprompts(self):  # Ajout du getter pour subprompts
        return self._data["subprompts"]

    # Méthodes abstraites avec implémentations simples ou retours de mock
    def append_data(self, data_identifier, data):
        self._data[data_identifier].append(data)

    async def read_data_content(self, data_container, data_file):
        return "data"

    async def write_data_content(self, data_container, data_file, data):
        pass

    async def store_unmentioned_messages(self, channel_id, thread_id, message):
        pass

    async def retrieve_unmentioned_messages(self, channel_id, thread_id):
        return ["message"]

    async def update_pricing(self, container_name, datafile_name, pricing_data):
        pass

    async def update_prompt_system_message(self, channel_id, thread_id, message):
        pass

    async def update_session(self, data_container, data_file, role, content):
        pass

    async def remove_data_content(self, data_container, data_file):
        pass

    async def list_container_files(self, container_name):
        return ["file1", "file2"]

    @property
    def plugin_name(self):
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        self._plugin_name = value

    def initialize(self):
        # Initialisation peut être vide ou logique simple si nécessaire
        pass

@pytest.fixture
def mock_processor():
    return MockInternalDataProcessing()

# Test for properties
@pytest.mark.parametrize("prop", ["sessions", "messages", "feedbacks", "concatenate", "prompts", "costs", "abort", "processing", "vectors"])
def test_properties(mock_processor, prop):
    assert hasattr(mock_processor, prop), f"Property {prop} is missing"

def test_append_data(mock_processor):
    mock_processor.append_data("messages", "Test message")
    assert "Test message" in mock_processor.messages, "Message should be appended"

@pytest.mark.asyncio
async def test_read_data_content(mock_processor):
    result = await mock_processor.read_data_content("dummy_container", "dummy_file")
    assert result == "data", "Should return 'data'"

@pytest.mark.asyncio
async def test_write_data_content(mock_processor):
    mock_write = AsyncMock(return_value=None)
    mock_processor.write_data_content = mock_write
    await mock_processor.write_data_content("dummy_container", "dummy_file", "Some data")
    mock_write.assert_called_once_with("dummy_container", "dummy_file", "Some data")

@pytest.mark.asyncio
async def test_store_unmentioned_messages(mock_processor):
    mock_store = AsyncMock(return_value=None)
    mock_processor.store_unmentioned_messages = mock_store
    await mock_processor.store_unmentioned_messages("channel_id", "thread_id", "message")
    mock_store.assert_called_once_with("channel_id", "thread_id", "message")

@pytest.mark.asyncio
async def test_retrieve_unmentioned_messages(mock_processor):
    mock_retrieve = AsyncMock(return_value=["message"])
    mock_processor.retrieve_unmentioned_messages = mock_retrieve
    result = await mock_processor.retrieve_unmentioned_messages("channel_id", "thread_id")
    assert result == ["message"], "Should retrieve messages"

@pytest.mark.asyncio
async def test_update_pricing(mock_processor):
    mock_update_pricing = AsyncMock(return_value=None)
    mock_processor.update_pricing = mock_update_pricing
    await mock_processor.update_pricing("container_name", "datafile_name", "pricing_data")
    mock_update_pricing.assert_called_once_with("container_name", "datafile_name", "pricing_data")

@pytest.mark.asyncio
async def test_update_prompt_system_message(mock_processor):
    mock_update = AsyncMock(return_value=None)
    mock_processor.update_prompt_system_message = mock_update
    await mock_processor.update_prompt_system_message("channel_id", "thread_id", "message")
    mock_update.assert_called_once_with("channel_id", "thread_id", "message")

@pytest.mark.asyncio
async def test_update_session(mock_processor):
    mock_update_session = AsyncMock(return_value=None)
    mock_processor.update_session = mock_update_session
    await mock_processor.update_session("data_container", "data_file", "role", "content")
    mock_update_session.assert_called_once_with("data_container", "data_file", "role", "content")

@pytest.mark.asyncio
async def test_remove_data_content(mock_processor):
    mock_remove = AsyncMock(return_value=None)
    mock_processor.remove_data_content = mock_remove
    await mock_processor.remove_data_content("data_container", "data_file")
    mock_remove.assert_called_once_with("data_container", "data_file")

@pytest.mark.asyncio
async def test_list_container_files(mock_processor):
    mock_list = AsyncMock(return_value=["file1", "file2"])
    mock_processor.list_container_files = mock_list
    result = await mock_processor.list_container_files("container_name")
    assert result == ["file1", "file2"], "Should list container files"
