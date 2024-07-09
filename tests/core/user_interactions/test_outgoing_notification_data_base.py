import pytest

from core.user_interactions.outgoing_notification_content_type import (
    OutgoingNotificationContentType,
)
from core.user_interactions.outgoing_notification_data_base import (
    OutgoingNotificationDataBase,
)
from core.user_interactions.outgoing_notification_event_types import (
    OutgoingNotificationEventTypes,
)


@pytest.fixture
def sample_data():
    return {
        'timestamp': '2023-06-20T12:00:00Z',
        'event_type': OutgoingNotificationEventTypes.MESSAGE,
        'channel_id': '123456',
        'thread_id': '654321',
        'response_id': '111111',
        'user_name': 'test_user',
        'user_email': 'test_user@example.com',
        'user_id': 'user123',
        'is_mention': True,
        'text': 'This is a test message.',
        'origin': 'test_origin',
        'images': ['image1.png', 'image2.png'],
        'files_content': ['file1.txt', 'file2.txt'],
        'raw_data': {'key': 'value'},
        'origin_plugin_name': 'test_plugin',
        'message_type': OutgoingNotificationContentType.TEXT,
        'reaction_name': None
    }

def test_outgoing_notification_data_base_initialization(sample_data):
    # Test initialization of OutgoingNotificationDataBase
    notification = OutgoingNotificationDataBase(**sample_data)
    assert notification.timestamp == sample_data['timestamp']
    assert notification.event_type == sample_data['event_type']
    assert notification.channel_id == sample_data['channel_id']
    assert notification.thread_id == sample_data['thread_id']
    assert notification.response_id == sample_data['response_id']
    assert notification.user_name == sample_data['user_name']
    assert notification.user_email == sample_data['user_email']
    assert notification.user_id == sample_data['user_id']
    assert notification.is_mention == sample_data['is_mention']
    assert notification.text == sample_data['text']
    assert notification.origin == sample_data['origin']
    assert notification.images == sample_data['images']
    assert notification.files_content == sample_data['files_content']
    assert notification.raw_data == sample_data['raw_data']
    assert notification.origin_plugin_name == sample_data['origin_plugin_name']
    assert notification.message_type == sample_data['message_type']
    assert notification.reaction_name == sample_data['reaction_name']

def test_outgoing_notification_data_base_to_dict(sample_data):
    # Test conversion of OutgoingNotificationDataBase to dictionary
    notification = OutgoingNotificationDataBase(**sample_data)
    notification_dict = notification.to_dict()
    expected_dict = {
        'timestamp': sample_data['timestamp'],
        'event_type': sample_data['event_type'].name,
        'channel_id': sample_data['channel_id'],
        'thread_id': sample_data['thread_id'],
        'response_id': sample_data['response_id'],
        'user_name': sample_data['user_name'],
        'user_email': sample_data['user_email'],
        'user_id': sample_data['user_id'],
        'is_mention': sample_data['is_mention'],
        'text': sample_data['text'],
        'origin': sample_data['origin'],
        'images': sample_data['images'],
        'files_content': sample_data['files_content'],
        'raw_data': sample_data['raw_data'],
        'origin_plugin_name': sample_data['origin_plugin_name'],
        'message_type': sample_data['message_type'].name,
        'reaction_name': sample_data['reaction_name']
    }
    assert notification_dict == expected_dict

def test_outgoing_notification_data_base_from_dict(sample_data):
    # Test creation of OutgoingNotificationDataBase from dictionary
    sample_dict = {
        'timestamp': sample_data['timestamp'],
        'event_type': sample_data['event_type'].value,
        'channel_id': sample_data['channel_id'],
        'thread_id': sample_data['thread_id'],
        'response_id': sample_data['response_id'],
        'user_name': sample_data['user_name'],
        'user_email': sample_data['user_email'],
        'user_id': sample_data['user_id'],
        'is_mention': sample_data['is_mention'],
        'text': sample_data['text'],
        'origin': sample_data['origin'],
        'images': sample_data['images'],
        'files_content': sample_data['files_content'],
        'raw_data': sample_data['raw_data'],
        'origin_plugin_name': sample_data['origin_plugin_name'],
        'message_type': sample_data['message_type'].value,
        'reaction_name': sample_data['reaction_name']
    }
    notification = OutgoingNotificationDataBase.from_dict(sample_dict)
    assert notification.timestamp == sample_data['timestamp']
    assert notification.event_type == "message"
    assert notification.channel_id == sample_dict['channel_id']
    assert notification.thread_id == sample_dict['thread_id']
    assert notification.response_id == sample_dict['response_id']
    assert notification.user_name == sample_dict['user_name']
    assert notification.user_email == sample_dict['user_email']
    assert notification.user_id == sample_dict['user_id']
    assert notification.is_mention == sample_dict['is_mention']
    assert notification.text == sample_dict['text']
    assert notification.origin == sample_dict['origin']
    assert notification.images == sample_dict['images']
    assert notification.files_content == sample_dict['files_content']
    assert notification.raw_data == sample_dict['raw_data']
    assert notification.origin_plugin_name == sample_dict['origin_plugin_name']
    assert notification.message_type == "text"
    assert notification.reaction_name == sample_dict['reaction_name']
