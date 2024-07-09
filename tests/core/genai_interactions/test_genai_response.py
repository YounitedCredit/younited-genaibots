import json

import pytest

from core.genai_interactions.genai_response import GenAIResponse, normalize_keys


# Test for normalizing keys function
def test_normalize_keys():
    data = [
        {'action': {'actionname': 'TestAction', 'parameters': {'param1': 'value1'}}},
        {'parameters': {'actionname': 'AnotherAction', 'parameters': {'param2': 'value2'}}}
    ]
    expected_output = [
        {'Action': {'ActionName': 'TestAction', 'Parameters': {'param1': 'value1'}}},
        {'Parameters': {'ActionName': 'AnotherAction', 'Parameters': {'param2': 'value2'}}}
    ]
    assert normalize_keys(data) == expected_output

# Test for creating GenAIResponse from JSON string
@pytest.mark.asyncio
async def test_genai_response_from_json_string():
    json_data = json.dumps({
        'response': [
            {'Action': {'ActionName': 'TestAction', 'Parameters': {'param1': 'value1'}}}
        ]
    })
    genai_response = await GenAIResponse.from_json(json_data)
    assert isinstance(genai_response, GenAIResponse)
    assert len(genai_response.response) == 1
    assert genai_response.response[0].ActionName == 'TestAction'
    assert genai_response.response[0].Parameters == {'param1': 'value1'}

# Test for creating GenAIResponse from dictionary
@pytest.mark.asyncio
async def test_genai_response_from_dict():
    data = {
        'response': [
            {'Action': {'ActionName': 'TestAction', 'Parameters': {'param1': 'value1'}}}
        ]
    }
    genai_response = await GenAIResponse.from_json(data)
    assert isinstance(genai_response, GenAIResponse)
    assert len(genai_response.response) == 1
    assert genai_response.response[0].ActionName == 'TestAction'
    assert genai_response.response[0].Parameters == {'param1': 'value1'}

# Test for missing 'response' field in JSON data
@pytest.mark.asyncio
async def test_genai_response_missing_response_field():
    json_data = json.dumps({})
    with pytest.raises(ValueError, match="'response' field is missing in the data"):
        await GenAIResponse.from_json(json_data)

# Test for missing 'Action' field in actions
@pytest.mark.asyncio
async def test_genai_response_missing_action_field():
    json_data = json.dumps({
        'response': [
            {'NotAction': {'ActionName': 'TestAction', 'Parameters': {'param1': 'value1'}}}
        ]
    })
    with pytest.raises(ValueError, match="'Action' field is missing in the action"):
        await GenAIResponse.from_json(json_data)
