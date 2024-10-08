import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from utils.prompt_manager.prompt_manager import PromptManager


# Ensure that loggers and handlers have proper levels
@pytest.fixture
def mock_logger():
    # Crée un vrai logger mais redirige sa sortie vers NullHandler pour éviter de polluer la sortie
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)  # Fixe le niveau de log à DEBUG
    handler = logging.NullHandler()  # Utilise un NullHandler pour ignorer les logs
    handler.setLevel(logging.DEBUG)  # Fixe le niveau de handler
    logger.addHandler(handler)
    return logger

@pytest.fixture(autouse=True)
def disable_logging():
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)

@pytest.fixture
def mock_global_manager_with_dispatcher(mock_global_manager):
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    return mock_global_manager


@pytest.mark.asyncio
async def test_initialize(mock_global_manager_with_dispatcher):
    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Mock methods that will be called during initialization
    prompt_manager.get_core_prompt = AsyncMock(return_value='core_prompt_content')
    prompt_manager.get_main_prompt = AsyncMock(return_value='main_prompt_content')

    # Call the initialize method
    await prompt_manager.initialize()

    # Assert prompts were set correctly
    assert prompt_manager.core_prompt == 'core_prompt_content'
    assert prompt_manager.main_prompt == 'main_prompt_content'
    assert hasattr(prompt_manager, 'prompt_container')


@pytest.mark.asyncio
async def test_get_sub_prompt(mock_global_manager_with_dispatcher):
    # Mock the configuration to return a folder name for sub-prompts
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.subprompts = 'subprompts_folder'

    # Mock backend dispatcher to return specific content
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(
        return_value='sub_prompt_content'
    )

    # Mock bot_config to set load_prompts_from_backend to True
    mock_global_manager_with_dispatcher.bot_config.LOAD_PROMPTS_FROM_BACKEND = True

    # Create an instance of the PromptManager
    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Call initialize method to set prompt_container
    await prompt_manager.initialize()

    message_type = 'test_message'

    # Call the get_sub_prompt method
    sub_prompt = await prompt_manager.get_sub_prompt(message_type)

    # Assert that the sub-prompt was retrieved correctly
    assert sub_prompt == 'sub_prompt_content'

    # Check that the correct folder and file were used in the backend dispatcher
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with(
        'subprompts_folder', f'{message_type}.txt'
    )

    # Ensure the subprompts folder was correctly accessed
    assert mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.subprompts == 'subprompts_folder'

@pytest.mark.asyncio
async def test_get_core_prompt(mock_global_manager_with_dispatcher):
    # Mock config manager to return a specific file name
    mock_global_manager_with_dispatcher.config_manager.get_config = MagicMock(return_value='core_prompt_file')
    # Mock backend dispatcher to return specific content
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(
        return_value='core_prompt_content'
    )
    # Mock bot_config to set load_prompts_from_backend to True
    mock_global_manager_with_dispatcher.bot_config.LOAD_PROMPTS_FROM_BACKEND = True

    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Call initialize method to set prompt_container
    await prompt_manager.initialize()

    # Call get_core_prompt method
    core_prompt = await prompt_manager.get_core_prompt()

    # Assert core prompt was retrieved correctly
    assert core_prompt == 'core_prompt_content'
    mock_global_manager_with_dispatcher.config_manager.get_config.assert_called_with(
        ['BOT_CONFIG', 'CORE_PROMPT']
    )
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with(
        prompt_manager.prompt_container, 'core_prompt_file.txt'
    )

@pytest.mark.asyncio
async def test_get_main_prompt(mock_global_manager, mock_logger):
    # Mocker le logger global pour utiliser le mock_logger
    logging.getLogger = MagicMock(return_value=mock_logger)

    # Mocker le config manager et backend dispatcher
    mock_global_manager.config_manager.get_config = MagicMock(return_value='main_prompt_file')
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(
        return_value='main_prompt_content'
    )
    # Mock bot_config to set load_prompts_from_backend to True
    mock_global_manager.bot_config.LOAD_PROMPTS_FROM_BACKEND = True

    prompt_manager = PromptManager(mock_global_manager)

    # Initialiser pour configurer le prompt_container
    await prompt_manager.initialize()

    # Appeler get_main_prompt et vérifier les résultats
    main_prompt = await prompt_manager.get_main_prompt()

    assert main_prompt == 'main_prompt_content'
    mock_global_manager.config_manager.get_config.assert_called_with(['BOT_CONFIG', 'MAIN_PROMPT'])
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with(
        prompt_manager.prompt_container, 'main_prompt_file.txt'
    )

@pytest.mark.asyncio
async def test_get_sub_prompt_local(mock_global_manager_with_dispatcher, tmp_path):
    # Set up a temporary directory for local prompts
    local_subprompts_path = tmp_path / "subprompts"
    local_subprompts_path.mkdir()
    test_subprompt = local_subprompts_path / "test_message.txt"
    test_subprompt.write_text("local sub prompt content")

    # Mock bot_config to set load_prompts_from_backend to False and set local path
    mock_global_manager_with_dispatcher.bot_config.LOAD_PROMPTS_FROM_BACKEND = False
    mock_global_manager_with_dispatcher.bot_config.LOCAL_SUBPROMPTS_PATH = str(local_subprompts_path)

    # Create an instance of the PromptManager
    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Call initialize method
    await prompt_manager.initialize()

    message_type = 'test_message'

    # Call the get_sub_prompt method
    sub_prompt = await prompt_manager.get_sub_prompt(message_type)

    # Assert that the sub-prompt was retrieved correctly from local file
    assert sub_prompt == "local sub prompt content"

    # Ensure the backend dispatcher was not called
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_not_called()
