import pytest
from unittest.mock import patch, MagicMock
import os
import pandas as pd
from your_script_name import (
    clean_text, clean_title, split_document_by_structure, split_document_into_passages,
    get_text_embedding, convert_to_azure_search_json, sanitize_document_id,
    generate_index_definition, main
)

@pytest.fixture
def sample_text():
    return """# Sample Markdown

This is a sample text with some **bold** and *italic* formatting.

## Section 1

- List item 1
- List item 2

## Section 2

1. Numbered item 1
2. Numbered item 2

[A link](https://example.com)

![An image](https://example.com/image.jpg)
"""

def test_clean_text(sample_text):
    cleaned = clean_text(sample_text)
    assert "# Sample Markdown" not in cleaned
    assert "**bold**" not in cleaned
    assert "*italic*" not in cleaned
    assert "- List item" not in cleaned
    assert "[A link]" not in cleaned
    assert "![An image]" not in cleaned
    assert "Sample Markdown" in cleaned
    assert "bold" in cleaned
    assert "italic" in cleaned
    assert "List item" in cleaned
    assert "A link" in cleaned

def test_clean_title():
    assert clean_title("test-title") == "test title"
    assert clean_title("test_title") == "test title"
    assert clean_title("test%20title") == "test title"

def test_split_document_by_structure(sample_text):
    tokenizer = tiktoken.get_encoding("cl100k_base")
    chunks = split_document_by_structure(sample_text, max_tokens=50, overlap_tokens=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(tokenizer.encode(chunk)) <= 50

def test_split_document_into_passages(sample_text):
    passages = split_document_into_passages(sample_text, max_tokens=50)
    assert len(passages) > 1
    for passage in passages:
        assert len(passage) > 0

@patch('your_script_name.openai_client')
def test_get_text_embedding(mock_openai):
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_openai.embeddings.create.return_value = mock_response
    
    embedding = get_text_embedding("test text")
    assert embedding == [0.1, 0.2, 0.3]
    mock_openai.embeddings.create.assert_called_once()

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

def test_sanitize_document_id():
    assert sanitize_document_id('valid_id') == 'valid_id'
    assert sanitize_document_id('_invalid_id') == 'invalid_id'
    assert sanitize_document_id('invalid@id') == 'invalid_id'

def test_generate_index_definition():
    index_def = generate_index_definition('test_index', 1536)
    assert index_def['name'] == 'test_index'
    assert len(index_def['fields']) > 0
    assert any(field['name'] == 'vector' for field in index_def['fields'])

@patch('your_script_name.get_text_embedding')
@patch('your_script_name.os.path.isfile')
@patch('your_script_name.open', new_callable=MagicMock)
def test_main(mock_open, mock_isfile, mock_get_embedding):
    mock_isfile.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = "Sample text"
    mock_get_embedding.return_value = [0.1, 0.2, 0.3]
    
    class Args:
        input = 'test.txt'
        output = 'output'
        output_format = 'csv'
        max_tokens = None
        index_name = None
        openai_key = 'test_key'
        openai_endpoint = 'test_endpoint'
        openai_api_version = '2023-05-15'
        dynamic_chunking = False
        overlap_tokens = 50
        model_name = 'test_model'
        source_type = 'filesystem'
        wiki_url = None
    
    df, output_file, index_file = main(Args())
    
    assert isinstance(df, pd.DataFrame)
    assert output_file == 'output.csv'
    assert index_file is None

if __name__ == "__main__":
    pytest.main()