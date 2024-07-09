import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


@pytest.fixture
def sample_data():
    return {
        'timestamp': '2023-06-20T12:00:00Z',
        'converted_timestamp': '2023-06-20T12:00:00+00:00',
        'event_label': 'Test Event',
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
        'origin_plugin_name': 'test_plugin'
    }

def test_incoming_notification_data_base_initialization(sample_data):
    # Test initialization of IncomingNotificationDataBase
    notification = IncomingNotificationDataBase(**sample_data)
    assert notification.timestamp == sample_data['timestamp']
    assert notification.converted_timestamp == sample_data['converted_timestamp']
    assert notification.event_label == sample_data['event_label']
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

def test_incoming_notification_data_base_to_dict(sample_data):
    # Test conversion of IncomingNotificationDataBase to dictionary
    notification = IncomingNotificationDataBase(**sample_data)
    notification_dict = notification.to_dict()
    assert notification_dict == sample_data

def test_incoming_notification_data_base_from_dict(sample_data):
    # Test creation of IncomingNotificationDataBase from dictionary
    notification = IncomingNotificationDataBase.from_dict(sample_data)
    assert notification.timestamp == sample_data['timestamp']
    assert notification.converted_timestamp == sample_data['converted_timestamp']
    assert notification.event_label == sample_data['event_label']
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
