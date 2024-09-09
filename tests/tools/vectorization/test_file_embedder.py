import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

# Ajoutez le chemin du répertoire racine du projet au sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
sys.path.insert(0, project_root)

# Maintenant, importez le module
try:
    from tools.vectorization.file_embedder import (
        clean_text, clean_title, split_document_by_structure, split_document_into_passages,
        get_text_embedding, convert_to_azure_search_json, sanitize_document_id,
        generate_index_definition, main, get_file_path, create_wiki_url
    )
except ImportError as e:
    print(f"Error importing file_embedder: {e}")
    print(f"sys.path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Content of {os.path.join(project_root, 'tools')}: {os.listdir(os.path.join(project_root, 'tools'))}")
    raise

# Test pour clean_text
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

# Test pour main function
@patch('tools.vectorization.file_embedder.AzureOpenAI')
@patch('tools.vectorization.file_embedder.get_text_embedding')
@patch('tools.vectorization.file_embedder.os.path.isfile')
@patch('tools.vectorization.file_embedder.open', new_callable=MagicMock)
def test_main(mock_open, mock_isfile, mock_get_embedding, mock_azure_openai):
    mock_isfile.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = "This is a longer text used for testing the embedding function."
    mock_get_embedding.return_value = [0.1, 0.2, 0.3]
    mock_client = MagicMock()
    mock_azure_openai.return_value = mock_client

    class Args:
        input = 'test.txt'
        output = 'output'
        output_format = 'csv'
        max_tokens = 100  # Ensure segmentation occurs
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

    df, output_file, index_file = main(Args())

    assert isinstance(df, pd.DataFrame)
    assert output_file == 'output.csv'
    assert index_file is None
    mock_azure_openai.assert_called_once()
    mock_get_embedding.assert_called()  # Ensure embedding function is called
