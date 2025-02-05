# -*- coding: utf-8 -*-
import pytest

from plugins.user_interactions.instant_messaging.slack.utils.slack_block_processor import (
    SlackBlockProcessor,
)


@pytest.fixture
def slack_block_processor():
    """Fixture to initialize SlackBlockProcessor."""
    return SlackBlockProcessor()


# 1. Test for processing header and section blocks (positive case)
def test_process_header_or_section_block(slack_block_processor):
    block = {"text": {"text": "Header or Section Text"}}
    result = slack_block_processor.process_header_or_section_block(block)
    assert result == "Header or Section Text"


# 2. Test for empty block in header/section (edge case)
def test_process_header_or_section_block_empty(slack_block_processor):
    block = {"text": {}}
    result = slack_block_processor.process_header_or_section_block(block)
    assert result == ""


# 3. Test for context block processing (mixed types)
def test_process_context_block(slack_block_processor):
    block = {
        "elements": [
            {"type": "mrkdwn", "text": "Markdown Text"},
            {"type": "plain_text", "text": "Plain Text"},
        ]
    }
    result = slack_block_processor.process_context_block(block)
    assert result == "Markdown Text Plain Text"


# 4. Test for empty context block (edge case)
def test_process_context_block_empty(slack_block_processor):
    block = {"elements": []}
    result = slack_block_processor.process_context_block(block)
    assert result == ""


# 5. Test input block with label and placeholder (normal case)
def test_process_input_block_with_label_and_placeholder(slack_block_processor):
    block = {
        "label": {"text": "Label Text"},
        "element": {"placeholder": {"text": "Placeholder Text"}},
    }
    result = slack_block_processor.process_input_block(block)
    assert result == "Label Text Placeholder Text"


# 6. Test input block with missing label (edge case)
def test_process_input_block_with_missing_label(slack_block_processor):
    block = {
        "element": {"placeholder": {"text": "Placeholder Text"}},
    }
    result = slack_block_processor.process_input_block(block)
    # .strip() removes leading spaces, hence the expected result without a leading space.
    assert result == "Placeholder Text"


# 7. Test rich text list processing with text and link (normal case)
def test_process_rich_text_list(slack_block_processor):
    element = {
        "elements": [
            {"type": "text", "text": "Item 1"},
            {"type": "link", "url": "https://example.com", "text": "Example Link"},
        ]
    }
    result = slack_block_processor.process_rich_text_list(element)
    assert result == "Item 1 <https://example.com|Example Link>"


# 8. Test rich text section processing with user mentions (normal case)
def test_process_rich_text_section_or_preformatted_with_user(slack_block_processor):
    element = {
        "elements": [
            {"type": "text", "text": "Some Text"},
            {"type": "user", "user_id": "U123456"},
        ]
    }
    result = slack_block_processor.process_rich_text_section_or_preformatted(element)
    # The current behavior does not add "User Mention:" before the user mention.
    assert result == "Some Text <@U123456>"


# 9. Test rich text section with multiple types (edge case)
def test_process_rich_text_section_or_preformatted_complex(slack_block_processor):
    element = {
        "elements": [
            {"type": "text", "text": "Text part"},
            {"type": "emoji", "name": "smile"},
            {"type": "link", "url": "https://example.com", "text": "Example"},
        ]
    }
    result = slack_block_processor.process_rich_text_section_or_preformatted(element)
    assert result == "Text part :smile: <https://example.com|Example>"


# 10. Test extract text with mixed blocks (complex case)
def test_extract_text_from_blocks_complex(slack_block_processor):
    blocks = [
        {"type": "header", "text": {"text": "Header"}},
        {"type": "section", "text": {"text": "Section Text"}},
        {"type": "context", "elements": [{"type": "plain_text", "text": "Context Text"}]},
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {"type": "text", "text": "Rich Text"},
                        {"type": "emoji", "name": "star"},
                    ],
                }
            ],
        },
        {
            "type": "input",
            "label": {"text": "Label Text"},
            "element": {"placeholder": {"text": "Input Placeholder"}},
        },
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    expected = (
        "Header Section Text Context Text Rich Text :star: "
        "Label Text Input Placeholder"
    )
    assert result == expected


# 11. Test extract text with unsupported block type (fallback)
def test_extract_text_from_blocks_unsupported_block_type(slack_block_processor):
    blocks = [
        {"type": "unsupported_block", "content": "Unsupported content"}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "{'type': 'unsupported_block', 'content': 'Unsupported content'}"


# 12. Test extract text from blocks with empty elements (boundary case)
def test_extract_text_from_blocks_empty_blocks(slack_block_processor):
    blocks = []
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == ""


# 13. Test fallback for missing text in header or section block
def test_extract_text_from_blocks_missing_text_field(slack_block_processor):
    blocks = [
        {"type": "header", "text": {}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == ""
