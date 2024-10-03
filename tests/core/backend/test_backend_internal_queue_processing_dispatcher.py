import pytest
from core.backend.internal_queue_processing_base import InternalQueueProcessingBase
from core.backend.backend_internal_queue_processing_dispatcher import BackendInternalQueueProcessingDispatcher

@pytest.fixture
def mock_plugin():
    class MockPlugin(InternalQueueProcessingBase):
        def __init__(self, plugin_name):
            self._plugin_name = plugin_name
            self._messages_queue = []
            self._messages_queue_ttl = 60
            self._internal_events_queue = []
            self._internal_events_queue_ttl = 60
            self._external_events_queue = []
            self._external_events_queue_ttl = 60
            self._wait_queue = []
            self._wait_queue_ttl = 60

        def initialize(self):
            pass

        @property
        def plugin_name(self):
            return self._plugin_name

        @plugin_name.setter
        def plugin_name(self, value):
            self._plugin_name = value

        @property
        def messages_queue(self):
            return self._messages_queue

        @property
        def messages_queue_ttl(self):
            return self._messages_queue_ttl

        @property
        def internal_events_queue(self):
            return self._internal_events_queue

        @property
        def internal_events_queue_ttl(self):
            return self._internal_events_queue_ttl

        @property
        def external_events_queue(self):
            return self._external_events_queue

        @property
        def external_events_queue_ttl(self):
            return self._external_events_queue_ttl

        @property
        def wait_queue(self):
            return self._wait_queue

        @property
        def wait_queue_ttl(self):
            return self._wait_queue_ttl
        
        @property
        def messages_queue(self):
            return self._messages_queue

        @messages_queue.setter
        def messages_queue(self, value):
            self._messages_queue = value

        async def enqueue_message(self, *args, **kwargs):
            # Instead of adding 'message', track by 'message_id' for consistency
            self._messages_queue.append(kwargs['message_id'])

        async def dequeue_message(self, *args, **kwargs):
            # Remove by 'message_id', which is how messages are tracked
            self._messages_queue.remove(kwargs['message_id'])

        async def get_next_message(self, *args, **kwargs):
            return None, None

        async def has_older_messages(self, *args, **kwargs):
            return False

        async def cleanup_expired_messages(self, *args, **kwargs):
            self._messages_queue.clear()

        async def clear_messages_queue(self, *args, **kwargs):
            self._messages_queue.clear()

        async def clear_all_queues(self):
            self._messages_queue.clear()
            self._internal_events_queue.clear()
            self._external_events_queue.clear()
            self._wait_queue.clear()

        async def clean_all_queues(self):
            # Mock implementation for abstract method
            self._messages_queue.clear()
            self._internal_events_queue.clear()
            self._external_events_queue.clear()
            self._wait_queue.clear()

        async def get_all_messages(self, *args, **kwargs):
            return self._messages_queue

    return MockPlugin("mock_plugin")

@pytest.fixture
def dispatcher(mock_config_manager, mock_global_manager):
    return BackendInternalQueueProcessingDispatcher(mock_global_manager)

@pytest.fixture
def mock_config_manager(mocker):
    mock_config = mocker.Mock()
    # Mocking the bot_config to return the default plugin name
    mock_config.bot_config.INTERNAL_QUEUE_PROCESSING_DEFAULT_PLUGIN_NAME = "mock_plugin"
    return mock_config


@pytest.fixture
def mock_global_manager(mock_config_manager, mocker):
    mock_global_manager = mocker.Mock()
    mock_global_manager.bot_config = mock_config_manager.bot_config
    mock_global_manager.logger = mocker.Mock()  # Mocking the logger
    return mock_global_manager

def test_initialize_dispatcher_without_plugins(dispatcher, mock_config_manager, mocker):
    # Test if no plugins are provided, the error is logged
    mocker.patch.object(dispatcher.logger, "error")
    dispatcher.initialize(plugins=None)
    dispatcher.logger.error.assert_called_with("No plugins provided for BackendInternalQueueProcessingDispatcher")

def test_initialize_dispatcher_with_plugins(dispatcher, mock_plugin, mock_config_manager):
    # Test initialization with plugins
    plugins = [mock_plugin]
    dispatcher.initialize(plugins=plugins)
    assert dispatcher.plugins == plugins
    assert dispatcher.default_plugin == mock_plugin

def test_get_plugin_without_default(dispatcher, mock_plugin, mocker):
    # Test getting a plugin when no default is set
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = None
    with pytest.raises(ValueError, match="No default plugin configured"):
        dispatcher.get_plugin()

def test_get_plugin_by_name(dispatcher, mock_plugin):
    # Test getting a plugin by name
    dispatcher.initialize([mock_plugin])
    plugin = dispatcher.get_plugin("mock_plugin")
    assert plugin == mock_plugin

def test_get_plugin_not_found(dispatcher, mock_plugin, mocker):
    # Test behavior when a plugin name is not found
    dispatcher.initialize([mock_plugin])
    dispatcher.default_plugin = None  # Ensure no default plugin is set
    mocker.patch.object(dispatcher.logger, "error")
    with pytest.raises(ValueError, match="Plugin 'invalid_plugin' not found"):
        dispatcher.get_plugin("invalid_plugin")

@pytest.mark.asyncio
async def test_enqueue_message(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.enqueue_message("container", "channel", "thread", "message_id", "message", "guid")
    # Check for message_id in the queue since that is what is being tracked
    assert "message_id" in mock_plugin.messages_queue


@pytest.mark.asyncio
async def test_dequeue_message(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.enqueue_message("container", "channel", "thread", "message_id", "message", "guid")
    await dispatcher.dequeue_message("container", "channel", "thread", "message_id", "guid")
    assert "message" not in mock_plugin.messages_queue

async def get_next_message(self, *args, **kwargs):
    current_message_id = kwargs['current_message_id']
    # Simulate getting the next message after the current_message_id
    if current_message_id in self._messages_queue:
        idx = self._messages_queue.index(current_message_id)
        if idx + 1 < len(self._messages_queue):
            next_message_id = self._messages_queue[idx + 1]
            return next_message_id, f"Message content for {next_message_id}"
    return None, None


@pytest.mark.asyncio
async def test_cleanup_expired_messages(dispatcher, mock_plugin):
    dispatcher.initialize([mock_plugin])
    await dispatcher.cleanup_expired_messages("container", "channel", "thread", 60, "mock_plugin")
    assert mock_plugin.messages_queue == []

# Additional tests for other async methods such as clear_messages_queue, get_all_messages, etc.
