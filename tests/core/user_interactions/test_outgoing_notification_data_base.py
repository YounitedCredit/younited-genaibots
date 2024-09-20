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
        'images': ['image1.png', 'image2.png'],
        'files_content': ['file1.txt', 'file2.txt'],
        'raw_data': {'key': 'value'},
        'origin_plugin_name': 'test_plugin',
        'message_type': OutgoingNotificationContentType.TEXT,
        'reaction_name': None,
        'is_internal': False  # Assurer que 'is_internal' est bien défini
    }


def test_outgoing_notification_data_base_initialization(sample_data):
    # Créer l'objet en utilisant les bons types pour event_type et message_type
    sample_data['event_type'] = OutgoingNotificationEventTypes.MESSAGE  # Utiliser l'enum directement
    sample_data['message_type'] = OutgoingNotificationContentType.TEXT  # Utiliser l'enum directement
    
    # Test initialization of OutgoingNotificationDataBase
    notification = OutgoingNotificationDataBase(**sample_data)
    
    # Assertions pour vérifier que chaque champ est correctement initialisé
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
    assert notification.images == sample_data['images']
    assert notification.files_content == sample_data['files_content']
    assert notification.raw_data == sample_data['raw_data']
    assert notification.origin_plugin_name == sample_data['origin_plugin_name']
    assert notification.message_type == sample_data['message_type']
    assert notification.reaction_name == sample_data['reaction_name']
    assert notification.is_internal == sample_data['is_internal']  # Vérifier le nouvel attribut



def test_outgoing_notification_data_base_to_dict(sample_data):
    # Test conversion of OutgoingNotificationDataBase to dictionary
    notification = OutgoingNotificationDataBase(**sample_data)
    notification_dict = notification.to_dict()
    
    expected_dict = {
        'timestamp': sample_data['timestamp'],
        'event_type': sample_data['event_type'].name,  # Conversion en nom
        'channel_id': sample_data['channel_id'],
        'thread_id': sample_data['thread_id'],
        'response_id': sample_data['response_id'],
        'user_name': sample_data['user_name'],
        'user_email': sample_data['user_email'],
        'user_id': sample_data['user_id'],
        'is_mention': sample_data['is_mention'],
        'text': sample_data['text'],
        'images': sample_data['images'],
        'files_content': sample_data['files_content'],
        'raw_data': sample_data['raw_data'],
        'origin_plugin_name': sample_data['origin_plugin_name'],
        'message_type': sample_data['message_type'].name,  # Conversion en nom
        'reaction_name': sample_data['reaction_name'],
        'is_internal': sample_data['is_internal']  # Ajouter le nouvel attribut
    }
    
    assert notification_dict == expected_dict


def test_outgoing_notification_data_base_from_dict(sample_data):
    # Test creation of OutgoingNotificationDataBase from dictionary
    sample_dict = {
        'timestamp': sample_data['timestamp'],
        'event_type': sample_data['event_type'].value,  # Utiliser la valeur (value) pour l'enum
        'channel_id': sample_data['channel_id'],
        'thread_id': sample_data['thread_id'],
        'response_id': sample_data['response_id'],
        'user_name': sample_data['user_name'],
        'user_email': sample_data['user_email'],
        'user_id': sample_data['user_id'],
        'is_mention': sample_data['is_mention'],
        'text': sample_data['text'],
        'images': sample_data['images'],
        'files_content': sample_data['files_content'],
        'raw_data': sample_data['raw_data'],
        'origin_plugin_name': sample_data['origin_plugin_name'],
        'message_type': sample_data['message_type'].value,  # Utiliser la valeur (value) pour l'enum
        'reaction_name': sample_data['reaction_name'],
        'is_internal': sample_data['is_internal']  # Ajouter le nouvel attribut
    }
    
    notification = OutgoingNotificationDataBase.from_dict(sample_dict)
    
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
    assert notification.images == sample_data['images']
    assert notification.files_content == sample_data['files_content']
    assert notification.raw_data == sample_data['raw_data']
    assert notification.origin_plugin_name == sample_data['origin_plugin_name']
    assert notification.message_type == sample_data['message_type']
    assert notification.reaction_name == sample_data['reaction_name']
    assert notification.is_internal == sample_data['is_internal']  # Vérifier le nouvel attribut

