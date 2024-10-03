import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from plugins.genai_interactions.image.openai_dalle.openai_dalle import OpenaiDallePlugin


@pytest.fixture
def mock_config():
    # Ensure all required fields for OpenAI Dalle are included and the structure matches the real config
    return {
        "PLUGIN_NAME": "openai_dalle",  # Plugin name
        "OPENAI_DALLE_INPUT_TOKEN_PRICE": 0.01,
        "OPENAI_DALLE_OUTPUT_TOKEN_PRICE": 0.02,
        "OPENAI_DALLE_API_KEY": "fake_api_key",
        "OPENAI_DALLE_MODEL_NAME": "dall-e-3",
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    # Make sure the mock configuration matches the structure in the real configuration
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.IMAGE = {
        "OPENAI_DALLE": mock_config
    }
    return mock_global_manager

@pytest.fixture
def openai_dalle_plugin(extended_mock_global_manager):
    # Initialize the plugin
    plugin = OpenaiDallePlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(openai_dalle_plugin):
    # Ensure that all config values are correctly set during initialization
    assert openai_dalle_plugin.openai_api_key == "fake_api_key"
    assert openai_dalle_plugin.model_name == "dall-e-3"
    assert openai_dalle_plugin.plugin_name == "openai_dalle"  # Check the actual plugin name

@pytest.mark.asyncio
async def test_handle_action(openai_dalle_plugin):
    # Mock the OpenAI image generation process
    with patch.object(openai_dalle_plugin.client.images, 'generate', new_callable=AsyncMock) as mock_generate:
        # Mock the result of generate to return a MagicMock with model_dump_json returning the expected JSON string
        mock_result = MagicMock()
        mock_result.model_dump_json.return_value = json.dumps({
            'data': [{'url': 'http://fake_url.com/image.png'}]
        })
        mock_generate.return_value = mock_result

        action_input = ActionInput(action_name='generate_image', parameters={'prompt': 'test prompt', 'size': '256x256'})
        result = await openai_dalle_plugin.handle_action(action_input)
        assert result == 'http://fake_url.com/image.png'
        mock_generate.assert_called_once_with(
            model="dall-e-3",
            prompt="test prompt",
            n=1,
            size="256x256"
        )
