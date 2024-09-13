import json
from unittest.mock import MagicMock, patch

import pytest

from tools.vectorization.aisearch_import import (
    create_index_if_not_exists,
    import_data,
    load_index_definition,
    validate_document,
    main
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

    # Document missing non-nullable field
    missing_field_document = {'id': 1}
    assert validate_document(missing_field_document, non_nullable_fields) is True  # As per current code

    # Document with extra fields
    extra_field_document = {'id': 1, 'content': 'Test content', 'extra': 'Extra data'}
    assert validate_document(extra_field_document, non_nullable_fields) is True

    # Document with null value in nullable field
    nullable_field_document = {'id': 1, 'content': 'Test content', 'optional': None}
    assert validate_document(nullable_field_document, non_nullable_fields) is True


# Test for load_index_definition
@patch("builtins.open", new_callable=MagicMock)
def test_load_index_definition(mock_open):
    # Mock file content
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"name": "test-index"})

    # Test loading index definition
    result = load_index_definition("/path/to/index_definition.json")
    assert result["name"] == "test-index"
    mock_open.assert_called_once_with("/path/to/index_definition.json", 'r', encoding='utf-8')

    # Test exception handling - file error
    mock_open.side_effect = Exception("File error")
    with pytest.raises(Exception, match="Error loading index definition"):
        load_index_definition("/path/to/index_definition.json")

# Test for create_index_if_not_exists
def test_create_index_if_not_exists():
    # Mock index client and method behaviors
    mock_client = MagicMock()
    mock_client.list_index_names.return_value = ["existing-index"]

    # Case 1: Index already exists
    index_definition = {"name": "existing-index"}
    result = create_index_if_not_exists(mock_client, index_definition)
    assert result == "existing-index"
    mock_client.list_index_names.assert_called_once()

    # Case 2: Index does not exist, create new one
    mock_client.reset_mock()
    mock_client.list_index_names.return_value = []
    mock_client.create_index.return_value = MagicMock()
    index_definition = {"name": "new-index"}
    result = create_index_if_not_exists(mock_client, index_definition)
    assert result == "new-index"
    mock_client.create_index.assert_called_once()

    # Case 3: Index creation fails
    mock_client.reset_mock()
    mock_client.list_index_names.return_value = []
    mock_client.create_index.side_effect = Exception("Index creation error")
    index_definition = {"name": "error-index"}
    with pytest.raises(Exception, match="Index creation error"):
        create_index_if_not_exists(mock_client, index_definition)


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
    mock_search_client.upload_documents.assert_called_once_with(documents=[
        {'id': 1, 'content': 'test content'},
        {'id': 2, 'content': 'another test content'}
    ])


@patch("tools.vectorization.aisearch_import.SearchClient")
@patch("builtins.open", new_callable=MagicMock)
def test_import_data_with_invalid_document(mock_open, mock_search_client):
    # Mock file content with invalid document
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
        "value": [
            {"id": 1, "content": "test content"},
            {"id": 2, "content": None}  # Invalid document
        ]
    })

    non_nullable_fields = ['id', 'content']
    mock_search_client.upload_documents.return_value = MagicMock()

    # Run import_data function
    import_data(mock_search_client, "/path/to/data.json", non_nullable_fields)

    # Verify that the valid document was uploaded, invalid was skipped
    mock_open.assert_called_once_with("/path/to/data.json", 'r', encoding='utf-8')
    mock_search_client.upload_documents.assert_called_once_with(documents=[
        {'id': 1, 'content': 'test content'}
    ])


@patch("tools.vectorization.aisearch_import.SearchClient")
@patch("builtins.open", new_callable=MagicMock)
def test_import_data_with_large_number_of_documents(mock_open, mock_search_client):
    # Mock file content with more than 100 documents
    documents = [{"id": i, "content": f"content {i}"} for i in range(1, 201)]
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"value": documents})

    non_nullable_fields = ['id', 'content']
    mock_search_client.upload_documents.return_value = MagicMock()

    # Run import_data function
    import_data(mock_search_client, "/path/to/data.json", non_nullable_fields)

    # Verify that upload_documents was called multiple times
    mock_open.assert_called_once_with("/path/to/data.json", 'r', encoding='utf-8')
    assert mock_search_client.upload_documents.call_count == 2

    # Get call arguments for each batch
    first_call_args = mock_search_client.upload_documents.call_args_list[0][1]
    second_call_args = mock_search_client.upload_documents.call_args_list[1][1]

    assert len(first_call_args['documents']) == 100
    assert len(second_call_args['documents']) == 100


@patch("tools.vectorization.aisearch_import.SearchClient")
@patch("builtins.open", new_callable=MagicMock)
def test_import_data_with_upload_exception(mock_open, mock_search_client):
    # Mock file content
    documents = [{"id": 1, "content": "test content"}]
    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"value": documents})

    non_nullable_fields = ['id', 'content']
    mock_search_client.upload_documents.side_effect = Exception("Upload error")

    # Run import_data function and expect exception
    with pytest.raises(Exception, match="Upload error"):
        import_data(mock_search_client, "/path/to/data.json", non_nullable_fields)


# Test for main function
@patch("tools.vectorization.aisearch_import.argparse.ArgumentParser")
@patch("tools.vectorization.aisearch_import.AzureKeyCredential")
@patch("tools.vectorization.aisearch_import.SearchIndexClient")
@patch("tools.vectorization.aisearch_import.SearchClient")
def test_main(mock_search_client_class, mock_search_index_client_class, mock_azure_key_credential, mock_argparse):
    # Mock arguments
    mock_args = MagicMock()
    mock_args.service_endpoint = "https://test.search.windows.net"
    mock_args.admin_key = "test-admin-key"
    mock_args.index_definition = "/path/to/index_definition.json"
    mock_args.data = "/path/to/data.json"
    mock_argparse.return_value.parse_args.return_value = mock_args

    # Mock clients
    mock_search_index_client = MagicMock()
    mock_search_index_client_class.return_value = mock_search_index_client

    mock_search_client = MagicMock()
    mock_search_client_class.return_value = mock_search_client

    # Mock functions
    with patch("tools.vectorization.aisearch_import.load_index_definition") as mock_load_index_definition, \
         patch("tools.vectorization.aisearch_import.create_index_if_not_exists") as mock_create_index_if_not_exists, \
         patch("tools.vectorization.aisearch_import.import_data") as mock_import_data:

        mock_load_index_definition.return_value = {"name": "test-index"}
        mock_create_index_if_not_exists.return_value = "test-index"

        # Run main function
        main()

        # Check that the functions were called
        mock_load_index_definition.assert_called_once_with("/path/to/index_definition.json")
        mock_create_index_if_not_exists.assert_called_once_with(mock_search_index_client, {"name": "test-index"})

        mock_import_data.assert_called_once_with(
            mock_search_client,
            "/path/to/data.json",
            ['id', 'content', 'filepath', 'title', 'chunk', 'vector']
        )

