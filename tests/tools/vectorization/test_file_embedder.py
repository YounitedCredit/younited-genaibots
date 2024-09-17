import logging
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
sys.path.insert(0, project_root)

try:
    from Tools.Vectorization.file_embedder import (
        clean_text,
        clean_title,
        convert_to_azure_search_json,
        create_wiki_url,
        generate_index_definition,
        get_file_path,
        get_text_embedding,
        main,
        sanitize_document_id,
        split_document_by_structure,
        split_document_into_passages,
    )

except ImportError as e:
    print(f"Error importing file_embedder: {e}")
    print(f"sys.path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Content of {os.path.join(project_root, 'tools')}: {os.listdir(os.path.join(project_root, 'tools'))}")
    raise

@pytest.fixture
def mock_azure_openai():
    with patch('tools.vectorization.file_embedder.AzureOpenAI') as mock:
        client = mock.return_value
        client.embeddings.create.return_value.data = [type('obj', (object,), {'embedding': [0.1, 0.2, 0.3]})()]
        yield mock

@pytest.fixture
def test_data():
    return "This is a test document.\nIt has multiple lines.\nAnd some content."

@pytest.fixture
def mock_file_system(test_data):
    def mock_open_file(*args, **kwargs):
        file_mock = MagicMock()
        file_mock.read.return_value = test_data
        return file_mock

    with patch('builtins.open', mock_open_file):
        with patch('os.path.isfile', return_value=True):
            with patch('os.path.isdir', return_value=True):
                with patch('os.walk', return_value=[('/fake/path', [], ['test_file.txt'])]):
                    yield

def test_clean_text():
    input_text = """
    # Markdown Title
    This is some **bold** and *italic* text.
    [A link](http://example.com)
    ![An image](http://example.com/image.jpg)
    - List item
    `inline code`
    ```
    block code
    ```
    """
    expected_output = "Markdown Title\nThis is some bold and italic text.\nhttp://example.com\nList item\ninline code"

    # Clean the markdown content
    cleaned_content = clean_text(input_text)

    # Verify that the cleaned output matches the expected output
    assert cleaned_content == expected_output

# Test pour clean_title
def test_clean_title():
    assert clean_title("test-title") == "test title"
    assert clean_title("test_title") == "test title"
    assert clean_title("test%20title") == "test title"

# Test pour split_document_by_structure
@patch('tools.vectorization.file_embedder.tokenizer')
def test_split_document_by_structure(mock_tokenizer):
    mock_tokenizer.encode.side_effect = lambda x: [0] * len(x.split())
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    chunks = split_document_by_structure(text, max_tokens=5, overlap_tokens=1)
    assert len(chunks) == 2
    assert chunks == ["Paragraph 1. Paragraph 2.", "Paragraph 2. Paragraph 3."]

# Test pour split_document_into_passages
@patch('tools.vectorization.file_embedder.tokenizer')
def test_split_document_into_passages(mock_tokenizer):
    mock_tokenizer.encode.return_value = [0] * 100
    document = "This is a test document. " * 100
    passages = split_document_into_passages(document, max_tokens=50)
    assert len(passages) == 2
    mock_tokenizer.encode.assert_called_once()

# Test pour get_text_embedding
@patch('tools.vectorization.file_embedder.AzureOpenAI')
def test_get_text_embedding(mock_azure_openai):
    mock_client = MagicMock()
    mock_azure_openai.return_value = mock_client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_client.embeddings.create.return_value = mock_response

    embedding = get_text_embedding("test text", mock_client)
    assert embedding == [0.1, 0.2, 0.3]
    mock_client.embeddings.create.assert_called_once()

# Test pour convert_to_azure_search_json
def test_convert_to_azure_search_json():
    df = pd.DataFrame({
        'document_id': ['doc1'],
        'passage_id': [1],
        'file_path': ['/path/to/file'],
        'passage_index': [1],
        'text': ['sample text'],
        'title': ['Sample Title'],
        'title_embedding': [[0.1, 0.2]],
        'embedding': [[0.3, 0.4]]
    })
    result = convert_to_azure_search_json(df)
    assert 'value' in result
    assert len(result['value']) == 1
    assert 'id' in result['value'][0]
    assert 'content' in result['value'][0]
    assert 'vector' in result['value'][0]

# Test pour sanitize_document_id
def test_sanitize_document_id():
    assert sanitize_document_id('valid_id') == 'valid_id'
    assert sanitize_document_id('_invalid_id') == 'invalid_id'
    assert sanitize_document_id('invalid@id') == 'invalid_id'

# Test pour generate_index_definition
def test_generate_index_definition():
    index_def = generate_index_definition('test_index', 1536)
    assert index_def['name'] == 'test_index'
    assert len(index_def['fields']) > 0
    assert any(field['name'] == 'vector' for field in index_def['fields'])

# Test pour get_file_path
def test_get_file_path():
    assert get_file_path('/local/path', 'filesystem', None, None) == '/local/path'
    with pytest.raises(ValueError):
        get_file_path('/local/path', 'invalid_type', None, None)

# Test pour create_wiki_url
def test_create_wiki_url():
    wiki_base_url = "https://dev.azure.com/org/project/_wiki/wikis/project.wiki"
    local_file_path = "/path/to/file.md"
    input_dir = "/path/to"
    expected_url = f"{wiki_base_url}?wikiVersion=GBwikiMaster&pagePath=/file"
    assert create_wiki_url(wiki_base_url, local_file_path, input_dir) == expected_url

def test_main(mock_azure_openai, mock_file_system, tmp_path, caplog):
    caplog.set_level(logging.DEBUG)

    # Prepare test arguments
    class Args:
        input = '/fake/path'
        output = os.path.join(str(tmp_path), 'output')  # Use os.path.join for path construction
        output_format = 'csv'
        max_tokens = 100
        index_name = None
        openai_key = 'test_key'
        openai_endpoint = 'test_endpoint'
        openai_api_version = '2023-05-15'
        dynamic_chunking = False
        overlap_tokens = 50
        model_name = 'test_model'
        source_type = 'filesystem'
        wiki_url = None
        wiki_subfolder = None

    # Run the main function
    m = mock_open(read_data="This is a test document.\nIt has multiple lines.\nAnd some content.")
    m.return_value.__enter__.return_value.write = MagicMock()
    with patch('tools.vectorization.file_embedder.get_text_embedding', return_value=[0.1, 0.2, 0.3]) as mock_get_embedding:
        with patch('builtins.open', m):
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                df, output_file, index_file = main(Args())

    # After running main, print the expected output file path
    print(f"Expected output file: {output_file}")

    # Check if the file exists in the temporary directory
    files_in_tmp = os.listdir(tmp_path)
    print(f"Files in tmp_path: {files_in_tmp}")

    # Print debug information
    print("=== Debug Info ===")
    print(f"DataFrame contents:\n{df}")
    print(f"DataFrame info:\n{df.info()}")
    print("Logs:")
    print(caplog.text)
    print("Mock get_text_embedding calls:")
    for call in mock_get_embedding.mock_calls:
        print(f"  {call}")
    print("Mock AzureOpenAI calls:")
    for call in mock_azure_openai.mock_calls:
        print(f"  {call}")
    print("Mock to_csv calls:")
    for call in mock_to_csv.mock_calls:
        print(f"  {call}")
    print("==================")

    # Assertions
    assert isinstance(df, pd.DataFrame), "The result should be a DataFrame"
    assert not df.empty, "The DataFrame should not be empty"
    assert len(df) >= 1, "The DataFrame should have at least one row"
    assert set(df.columns) == {'document_id', 'passage_id', 'file_path', 'passage_index', 'text', 'title', 'title_embedding', 'embedding'}, "The DataFrame should have the expected columns"

    # Check if AzureOpenAI was called correctly
    mock_azure_openai.assert_called_once_with(
        api_key='test_key',
        azure_endpoint='test_endpoint',
        api_version='2023-05-15'
    )

    # Check if get_text_embedding was called
    assert mock_get_embedding.called, "get_text_embedding should have been called"

    # Check if to_csv was called
    mock_to_csv.assert_called_once()

    # Instead of checking if the file exists (which it won't due to mocking),
    # we'll check if to_csv was called with the correct filename
    to_csv_args, to_csv_kwargs = mock_to_csv.call_args
    assert to_csv_args[0] == output_file, f"to_csv should have been called with {output_file}"

    assert index_file is None, "No index file should be generated in this test case"
