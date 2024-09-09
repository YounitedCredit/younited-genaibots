import pytest
import json
from unittest.mock import patch, MagicMock
from tools.vectorization.aisearch_import import (
    validate_document,
    load_index_definition,
    create_index_if_not_exists,
    import_data
)

# Test for validate_document
def test_validate_document():
    # Non-nullable fields
    non_nullable_fields = ['id', 'content']

    # Valid document
    valid_document = {'id': 1, 'content': 'Test content'}
    assert validate_document(valid_document, non_nullable_fields) is True

    # Invalid document (null value in non-nullable field)
    invalid_document = {'id': 1, 'content': None}
    assert validate_document(invalid_document, non_nullable_fields) is False


# Test for load_index_definition
@patch("builtins.open", new_callable=MagicMock)
def test_load_index_definition(mock_open):
    # Mock file content
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"name": "test-index"})
    
    # Test loading index definition
    result = load_index_definition("/path/to/index_definition.json")
    assert result["name"] == "test-index"
    mock_open.assert_called_once_with("/path/to/index_definition.json", 'r', encoding='utf-8')

    # Test exception handling
    mock_open.side_effect = Exception("File error")
    with pytest.raises(Exception, match="File error"):
        load_index_definition("/path/to/index_definition.json")


# Test for create_index_if_not_exists
@patch("tools.vectorization.aisearch_import.SearchIndexClient")
def test_create_index_if_not_exists(mock_search_index_client):
    # Mock index client and method behaviors
    mock_client = MagicMock()
    mock_client.list_index_names.return_value = ["existing-index"]

    # Case 1: Index already exists
    index_definition = {"name": "existing-index"}
    result = create_index_if_not_exists(mock_client, index_definition)
    assert result == "existing-index"
    mock_client.list_index_names.assert_called_once()

    # Case 2: Index does not exist, create new one
    mock_client.list_index_names.return_value = []
    mock_client.create_index.return_value = MagicMock()
    index_definition = {"name": "new-index"}
    result = create_index_if_not_exists(mock_client, index_definition)
    assert result == "new-index"
    mock_client.create_index.assert_called_once()

# Test for import_data
@patch("tools.vectorization.aisearch_import.SearchClient")
@patch("builtins.open", new_callable=MagicMock)
def test_import_data(mock_open, mock_search_client):
    # Mock file content and search client behavior
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
        "value": [
            {"id": 1, "content": "test content"},
            {"id": 2, "content": "another test content"}
        ]
    })
    
    non_nullable_fields = ['id', 'content']
    mock_search_client.upload_documents.return_value = MagicMock()

    # Run import_data function
    import_data(mock_search_client, "/path/to/data.json", non_nullable_fields)

    # Verify that the data was processed and uploaded correctly
    mock_open.assert_called_once_with("/path/to/data.json", 'r', encoding='utf-8')
    mock_search_client.upload_documents.assert_called()