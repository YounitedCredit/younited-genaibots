import pytest

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


@pytest.fixture
def sample_data_user():
    return {
        'timestamp': '2023-06-20T12:00:00Z',
        'event_label': 'Test Event',
        'channel_id': '123456',
        'thread_id': '654321',
        'response_id': '111111',
        'user_name': 'test_user',
        'user_email': 'test_user@example.com',
        'user_id': 'user123',
        'app_id': None,
        'api_app_id': None,
        'username': None,
        'is_mention': True,
        'text': 'This is a test message.',
        'images': ['image1.png', 'image2.png'],
        'files_content': ['file1.txt', 'file2.txt'],
        'raw_data': {'key': 'value'},
        'origin_plugin_name': 'test_plugin'
    }

@pytest.fixture
def sample_data_app():
    return {
        'timestamp': '2023-06-20T12:00:00Z',
        'event_label': 'Test Event',
        'channel_id': '123456',
        'thread_id': '654321',
        'response_id': '111111',
        'user_name': None,
        'user_email': None,
        'user_id': None,
        'username': 'test_app',
        'app_id': 'app123',
        'api_app_id': None,
        'is_mention': True,
        'text': 'This is a test message.',
        'images': ['image1.png', 'image2.png'],
        'files_content': ['file1.txt', 'file2.txt'],
        'raw_data': {'key': 'value'},
        'origin_plugin_name': 'test_plugin'
    }

@pytest.fixture
def sample_data_api_app():
    return {
        'timestamp': '2023-06-20T12:00:00Z',
        'event_label': 'Test Event',
        'channel_id': '123456',
        'thread_id': '654321',
        'response_id': '111111',
        'user_name': None,
        'user_email': None,
        'user_id': None,
        'username': 'test_api_app',
        'app_id': None,
        'api_app_id': 'api_app123',
        'is_mention': True,
        'text': 'This is a test message.',
        'images': ['image1.png', 'image2.png'],
        'files_content': ['file1.txt', 'file2.txt'],
        'raw_data': {'key': 'value'},
        'origin_plugin_name': 'test_plugin'
    }

def test_incoming_notification_data_base_initialization(sample_data_user):
    # Test initialization of IncomingNotificationDataBase
    notification = IncomingNotificationDataBase(**sample_data_user)
    assert notification.timestamp == sample_data_user['timestamp']
    assert notification.event_label == sample_data_user['event_label']
    assert notification.channel_id == sample_data_user['channel_id']
    assert notification.thread_id == sample_data_user['thread_id']
    assert notification.response_id == sample_data_user['response_id']
    assert notification.user_name == sample_data_user['user_name']
    assert notification.user_email == sample_data_user['user_email']
    assert notification.user_id == sample_data_user['user_id']
    assert notification.app_id if notification.app_id!="" else None  == sample_data_user["app_id"]
    assert notification.api_app_id if notification.api_app_id!="" else None  == sample_data_user["api_app_id"]
    assert notification.username  if notification.username!="" else None  == sample_data_user["username"]
    assert notification.is_mention == sample_data_user['is_mention']
    assert notification.text == sample_data_user['text']
    assert notification.images == sample_data_user['images']
    assert notification.files_content == sample_data_user['files_content']
    assert notification.raw_data == sample_data_user['raw_data']
    assert notification.origin_plugin_name == sample_data_user['origin_plugin_name']

def test_incoming_notification_data_base_to_dict(sample_data_user):
    # Test conversion of IncomingNotificationDataBase to dictionary
    notification = IncomingNotificationDataBase(**sample_data_user)
    notification.app_id = sample_data_user["app_id"] if sample_data_user["app_id"]!="" else None
    notification.api_app_id = sample_data_user["api_app_id"] if sample_data_user["api_app_id"]!="" else None
    notification.username = sample_data_user["username"] if sample_data_user["username"]!="" else None
    notification_dict = notification.to_dict()
    assert notification_dict == sample_data_user

def test_incoming_notification_data_base_from_dict(sample_data_user):
    # Test creation of IncomingNotificationDataBase from dictionary
    notification = IncomingNotificationDataBase.from_dict(sample_data_user)
    assert notification.timestamp == sample_data_user['timestamp']
    assert notification.event_label == sample_data_user['event_label']
    assert notification.channel_id == sample_data_user['channel_id']
    assert notification.thread_id == sample_data_user['thread_id']
    assert notification.response_id == sample_data_user['response_id']
    assert notification.user_name == sample_data_user['user_name']
    assert notification.user_email == sample_data_user['user_email']
    assert notification.user_id == sample_data_user['user_id']
    assert notification.username if notification.username!="" else None  == sample_data_user["username"]
    assert notification.app_id if notification.app_id!="" else None == sample_data_user["app_id"]
    assert notification.api_app_id if notification.api_app_id!="" else None == sample_data_user["api_app_id"]
    assert notification.is_mention == sample_data_user['is_mention']
    assert notification.text == sample_data_user['text']
    assert notification.images == sample_data_user['images']
    assert notification.files_content == sample_data_user['files_content']
    assert notification.raw_data == sample_data_user['raw_data']
    assert notification.origin_plugin_name == sample_data_user['origin_plugin_name']

def test_incoming_notification_data_base_initialization_app(sample_data_app):
    # Test initialization of IncomingNotificationDataBase
    notification = IncomingNotificationDataBase(**sample_data_app)
    print(notification.user_name)
    assert notification.timestamp == sample_data_app['timestamp']
    assert notification.event_label == sample_data_app['event_label']
    assert notification.channel_id == sample_data_app['channel_id']
    assert notification.thread_id == sample_data_app['thread_id']
    assert notification.response_id == sample_data_app['response_id']
    assert notification.username == sample_data_app["username"]
    assert notification.app_id == sample_data_app["app_id"]
    assert notification.api_app_id if notification.api_app_id!="" else None == sample_data_app["api_app_id"]
    assert notification.user_name if notification.user_name!="" else None == sample_data_app['user_name']
    assert notification.user_email if notification.user_email!="" else None == sample_data_app['user_email']
    assert notification.user_id if notification.user_id!="" else None == sample_data_app['user_id']
    assert notification.is_mention == sample_data_app['is_mention']
    assert notification.text == sample_data_app['text']
    assert notification.images == sample_data_app['images']
    assert notification.files_content == sample_data_app['files_content']
    assert notification.raw_data == sample_data_app['raw_data']
    assert notification.origin_plugin_name == sample_data_app['origin_plugin_name']

def test_incoming_notification_data_base_initialization_api_app(sample_data_api_app):
    # Test initialization of IncomingNotificationDataBase
    notification = IncomingNotificationDataBase(**sample_data_api_app)
    print(notification.user_name)
    assert notification.timestamp == sample_data_api_app['timestamp']
    assert notification.event_label == sample_data_api_app['event_label']
    assert notification.channel_id == sample_data_api_app['channel_id']
    assert notification.thread_id == sample_data_api_app['thread_id']
    assert notification.response_id == sample_data_api_app['response_id']
    assert notification.username == sample_data_api_app["username"]
    assert notification.api_app_id == sample_data_api_app["api_app_id"]
    assert notification.app_id if notification.app_id!="" else None == sample_data_api_app["app_id"]
    assert notification.user_name if notification.user_name!="" else None == sample_data_api_app['user_name']
    assert notification.user_email if notification.user_email!="" else None == sample_data_api_app['user_email']
    assert notification.user_id if notification.user_id!="" else None == sample_data_api_app['user_id']
    assert notification.is_mention == sample_data_api_app['is_mention']
    assert notification.text == sample_data_api_app['text']
    assert notification.images == sample_data_api_app['images']
    assert notification.files_content == sample_data_api_app['files_content']
    assert notification.raw_data == sample_data_api_app['raw_data']
    assert notification.origin_plugin_name == sample_data_api_app['origin_plugin_name']

def test_incoming_notification_data_base_to_dict_app(sample_data_app):
    # Test conversion of IncomingNotificationDataBase to dictionary
    notification = IncomingNotificationDataBase(**sample_data_app)
    notification.user_name = sample_data_app['user_name'] if sample_data_app['user_name']!="" else None
    notification.user_email = sample_data_app['user_email'] if sample_data_app['user_email']!="" else None
    notification.user_id = sample_data_app['user_id'] if sample_data_app['user_id']!="" else None
    notification.api_app_id = sample_data_app['api_app_id'] if sample_data_app['api_app_id']!="" else None
    notification_dict = notification.to_dict()
    assert notification_dict == sample_data_app

def test_incoming_notification_data_base_to_dict_api_app(sample_data_api_app):
    # Test conversion of IncomingNotificationDataBase to dictionary
    notification = IncomingNotificationDataBase(**sample_data_api_app)
    notification.user_name = sample_data_api_app['user_name'] if sample_data_api_app['user_name']!="" else None
    notification.user_email = sample_data_api_app['user_email'] if sample_data_api_app['user_email']!="" else None
    notification.user_id = sample_data_api_app['user_id'] if sample_data_api_app['user_id']!="" else None
    notification.app_id = sample_data_api_app['app_id'] if sample_data_api_app['app_id']!="" else None
    notification_dict = notification.to_dict()
    assert notification_dict == sample_data_api_app


def test_incoming_notification_data_base_from_dict_app(sample_data_app):
    # Test creation of IncomingNotificationDataBase from dictionary
    notification = IncomingNotificationDataBase.from_dict(sample_data_app)
    assert notification.timestamp == sample_data_app['timestamp']
    assert notification.event_label == sample_data_app['event_label']
    assert notification.channel_id == sample_data_app['channel_id']
    assert notification.thread_id == sample_data_app['thread_id']
    assert notification.response_id == sample_data_app['response_id']
    assert notification.user_name if notification.user_name!="" else None == sample_data_app['user_name']
    assert notification.user_email if notification.user_email!="" else None == sample_data_app['user_email']
    assert notification.user_id if notification.user_id!="" else None == sample_data_app['user_id']
    assert notification.api_app_id if notification.api_app_id!="" else None == sample_data_app['api_app_id']
    assert notification.username == sample_data_app['username']
    assert notification.app_id == sample_data_app['app_id']
    assert notification.is_mention == sample_data_app['is_mention']
    assert notification.text == sample_data_app['text']
    assert notification.images == sample_data_app['images']
    assert notification.files_content == sample_data_app['files_content']
    assert notification.raw_data == sample_data_app['raw_data']
    assert notification.origin_plugin_name == sample_data_app['origin_plugin_name']

def test_incoming_notification_data_base_from_dict_app(sample_data_api_app):
    # Test creation of IncomingNotificationDataBase from dictionary
    notification = IncomingNotificationDataBase.from_dict(sample_data_api_app)
    assert notification.timestamp == sample_data_api_app['timestamp']
    assert notification.event_label == sample_data_api_app['event_label']
    assert notification.channel_id == sample_data_api_app['channel_id']
    assert notification.thread_id == sample_data_api_app['thread_id']
    assert notification.response_id == sample_data_api_app['response_id']
    assert notification.user_name if notification.user_name!="" else None == sample_data_api_app['user_name']
    assert notification.user_email if notification.user_email!="" else None == sample_data_api_app['user_email']
    assert notification.user_id if notification.user_id!="" else None == sample_data_api_app['user_id']
    assert notification.app_id if notification.app_id!="" else None == sample_data_api_app['app_id']
    assert notification.username == sample_data_api_app['username']
    assert notification.api_app_id == sample_data_api_app['api_app_id']
    assert notification.is_mention == sample_data_api_app['is_mention']
    assert notification.text == sample_data_api_app['text']
    assert notification.images == sample_data_api_app['images']
    assert notification.files_content == sample_data_api_app['files_content']
    assert notification.raw_data == sample_data_api_app['raw_data']
    assert notification.origin_plugin_name == sample_data_api_app['origin_plugin_name']
