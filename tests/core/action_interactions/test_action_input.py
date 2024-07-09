# tests/core/action_interactions/test_action_input.py

import pytest

from core.action_interactions.action_input import ActionInput, CaseInsensitiveDict


def test_case_insensitive_dict_initialization():
    data = {'Key1': 'value1', 'KEY2': 'value2'}
    cid = CaseInsensitiveDict(data)
    assert cid['key1'] == 'value1'
    assert cid['key2'] == 'value2'

def test_case_insensitive_dict_methods():
    cid = CaseInsensitiveDict({'Key': 'value'})
    assert cid['key'] == 'value'
    cid['KEY'] = 'new_value'
    assert cid['key'] == 'new_value'
    cid['anotherKey'] = 'another_value'
    assert cid['anotherkey'] == 'another_value'
    assert 'anotherkey' in cid
    cid.pop('ANOTHERKEY')
    assert 'anotherkey' not in cid
    assert cid.get('key') == 'new_value'
    assert cid.get('nonexistent', 'default') == 'default'

def test_action_input_initialization():
    ai = ActionInput('test_action', {'param1': 'value1'})
    assert ai.action_name == 'test_action'
    assert ai.parameters['param1'] == 'value1'

def test_action_input_initialization_with_none_parameters():
    ai = ActionInput('test_action')
    assert ai.action_name == 'test_action'
    assert ai.parameters == {}

def test_action_input_initialization_with_invalid_parameters():
    with pytest.raises(TypeError):
        ActionInput('test_action', ['invalid', 'parameters'])

def test_action_input_to_dict():
    ai = ActionInput('test_action', {'param1': 'value1'})
    expected_dict = {
        'action_name': 'test_action',
        'parameters': {'param1': 'value1'}
    }
    assert ai.to_dict() == expected_dict

def test_action_input_to_dict_function():
    ai = ActionInput('test_action', {'param1': 'value1'})
    expected_dict = {
        'action_name': 'test_action',
        'parameters': {'param1': 'value1'}
    }
    assert ActionInput.action_input_to_dict(ai) == expected_dict
