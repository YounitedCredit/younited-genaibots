# tests/plugins/action_interactions/default/main_actions/actions/test_submit_feedback.py

from unittest.mock import AsyncMock

import pytest

from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from plugins.action_interactions.default.main_actions.actions.submit_feedback import (
    SubmitFeedback,
)


@pytest.mark.asyncio
async def test_submit_feedback_execute(mock_global_manager):
    # Setup
    submit_feedback_action = SubmitFeedback(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='submit_feedback', parameters={
        'Category': 'TestCategory',
        'SubCategory': 'TestSubCategory',
        'Summary': 'Test feedback summary'
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name="origin_plugin_name"
    )

    # Mock methods
    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks = "mock_feedbacks_container"
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    # Execute the action
    await submit_feedback_action.execute(action_input, event)

    # Assert that read_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt"
    )

    # Assert that write_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt",
        data="Test feedback summary\n"
    )

@pytest.mark.asyncio
async def test_submit_feedback_execute_with_existing_content(mock_global_manager):
    # Setup
    submit_feedback_action = SubmitFeedback(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='submit_feedback', parameters={
        'Category': 'TestCategory',
        'SubCategory': 'TestSubCategory',
        'Summary': 'Additional feedback'
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods
    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks = "mock_feedbacks_container"
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Existing feedback\n")
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    # Execute the action
    await submit_feedback_action.execute(action_input, event)

    # Assert that read_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt"
    )

    # Assert that write_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt",
        data="Existing feedback\nAdditional feedback\n"
    )

@pytest.mark.asyncio
async def test_submit_feedback_execute_with_missing_parameters(mock_global_manager):
    # Setup
    submit_feedback_action = SubmitFeedback(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='submit_feedback', parameters={
        'Category': 'TestCategory'
        # Missing 'SubCategory' and 'Summary'
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods
    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks = "mock_feedbacks_container"
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock()

    # Execute the action
    await submit_feedback_action.execute(action_input, event)

    # Assert that read_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_.txt"  # SubCategory is missing
    )

    # Assert that write_data_content was called correctly with default summary
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_.txt",
        data="\n"  # Summary is missing, so it defaults to an empty string followed by a newline
    )

@pytest.mark.asyncio
async def test_submit_feedback_execute_with_special_characters(mock_global_manager):
    # Setup
    special_characters_summary = 'Test feedback with special characters: \n\t🚀✨'
    submit_feedback_action = SubmitFeedback(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='submit_feedback', parameters={
        'Category': 'SpecialCategory',
        'SubCategory': 'SpecialSubCategory',
        'Summary': special_characters_summary
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods
    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks

@pytest.mark.asyncio
async def test_submit_feedback_execute_with_write_exception(mock_global_manager):
    # Setup
    submit_feedback_action = SubmitFeedback(global_manager=mock_global_manager)
    action_input = ActionInput(action_name='submit_feedback', parameters={
        'Category': 'TestCategory',
        'SubCategory': 'TestSubCategory',
        'Summary': 'Test feedback summary'
    })
    event = IncomingNotificationDataBase(
        timestamp='123456',
        event_label='test_event',
        channel_id='channel_1',
        thread_id='thread_123',
        response_id='response_123',
        user_name='test_user',
        user_email='test_user@example.com',
        user_id='user_123',
        is_mention=False,
        text='',
        origin='test_origin',
        images=[],
        files_content=[],
        origin_plugin_name='test_plugin'
    )

    # Mock methods and simulate an exception during write
    mock_global_manager.backend_internal_data_processing_dispatcher.feedbacks = "mock_feedbacks_container"
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content = AsyncMock(side_effect=Exception("Write error"))

    # Add a flag to check if the exception is handled
    exception_handled = False

    # Override the logger's error method to set the flag
    def mock_logger_error(message):
        nonlocal exception_handled
        exception_handled = True

    mock_global_manager.logger.error = mock_logger_error

    # Execute the action
    await submit_feedback_action.execute(action_input, event)

    # Assert that read_data_content was called correctly
    mock_global_manager.backend_internal_data_processing_dispatcher.read_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt"
    )

    # Assert that write_data_content was called and raised an exception
    mock_global_manager.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once_with(
        data_container="mock_feedbacks_container",
        data_file="TestCategory_TestSubCategory.txt",
        data="Test feedback summary\n"
    )

    # Assert that the exception was handled
    assert exception_handled, "The exception was not handled within the function"


