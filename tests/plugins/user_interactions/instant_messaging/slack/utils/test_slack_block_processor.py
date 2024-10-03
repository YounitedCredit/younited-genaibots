import pytest
from plugins.user_interactions.instant_messaging.slack.utils.slack_block_processor import SlackBlockProcessor

@pytest.fixture
def slack_block_processor():
    """Fixture to initialize SlackBlockProcessor"""
    return SlackBlockProcessor()

def test_extract_text_from_blocks_header_section(slack_block_processor, mock_config_manager):
    # Test header and section block extraction
    blocks = [
        {"type": "header", "text": {"text": "Header Text"}},
        {"type": "section", "text": {"text": "Section Text"}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "Header Text Section Text"

def test_extract_text_from_blocks_context(slack_block_processor, mock_config_manager):
    # Test context block extraction with mixed types
    blocks = [
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": "Markdown Text"},
            {"type": "plain_text", "text": "Plain Text"}
        ]}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "Markdown Text Plain Text"

def test_extract_text_from_blocks_rich_text(slack_block_processor, mock_config_manager):
    # Test rich text block with lists, links, and mentions
    blocks = [
        {"type": "rich_text", "elements": [
            {"type": "rich_text_list", "elements": [
                {"type": "text", "text": "Item 1"},
                {"type": "link", "url": "https://example.com", "text": "Example"}
            ]},
            {"type": "rich_text_section", "elements": [
                {"type": "text", "text": "More text"},
                {"type": "user", "user_id": "U12345"}
            ]}
        ]}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    expected = "Item 1 <https://example.com|Example> More text User Mention: <@U12345>"
    assert result == expected

def test_extract_text_from_blocks_input(slack_block_processor, mock_config_manager):
    # Test input block with label and placeholder
    blocks = [
        {"type": "input", "label": {"text": "Label Text"}, "element": {"placeholder": {"text": "Placeholder Text"}}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "Label Text Placeholder Text"

def test_extract_text_from_blocks_fallback(slack_block_processor, mock_config_manager):
    # Test fallback for unknown block types
    blocks = [
        {"type": "unknown", "content": "Some unknown block"}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "{'type': 'unknown', 'content': 'Some unknown block'}"
