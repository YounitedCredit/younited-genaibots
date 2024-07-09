import pytest

from plugins.user_interactions.instant_messaging.slack.utils.slack_block_processor import (
    SlackBlockProcessor,
)


@pytest.fixture
def slack_block_processor():
    return SlackBlockProcessor()

def test_extract_text_from_blocks_with_header_and_section(slack_block_processor):
    blocks = [
        {'type': 'header', 'text': {'text': 'Header Text'}},
        {'type': 'section', 'text': {'text': 'Section Text'}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == 'Header Text Section Text'

def test_extract_text_from_blocks_with_context(slack_block_processor):
    blocks = [
        {'type': 'context', 'elements': [{'type': 'mrkdwn', 'text': 'Markdown Text'}, {'type': 'plain_text', 'text': 'Plain Text'}]}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == 'Markdown Text Plain Text'

def test_extract_text_from_blocks_with_rich_text(slack_block_processor):
    blocks = [
        {'type': 'rich_text', 'elements': [{'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Rich Text'}]}]}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == 'Rich Text'

def test_extract_text_from_blocks_with_input(slack_block_processor):
    blocks = [
        {'type': 'input', 'label': {'text': 'Label Text'}, 'element': {'placeholder': {'text': 'Placeholder Text'}}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == 'Label Text Placeholder Text'

def test_process_header_or_section_block(slack_block_processor):
    block = {'text': {'text': 'Header or Section Text'}}
    result = slack_block_processor.process_header_or_section_block(block)
    assert result == 'Header or Section Text'

def test_process_context_block(slack_block_processor):
    block = {'elements': [{'type': 'mrkdwn', 'text': 'Markdown Text'}, {'type': 'plain_text', 'text': 'Plain Text'}]}
    result = slack_block_processor.process_context_block(block)
    assert result == 'Markdown Text Plain Text'

def test_process_input_block(slack_block_processor):
    block = {'label': {'text': 'Label Text'}, 'element': {'placeholder': {'text': 'Placeholder Text'}}}
    result = slack_block_processor.process_input_block(block)
    assert result == 'Label Text Placeholder Text'

def test_process_rich_text_list(slack_block_processor):
    element = {'elements': [{'type': 'text', 'text': 'Text Content'}, {'type': 'link', 'url': 'http://example.com', 'text': 'Example'}]}
    result = slack_block_processor.process_rich_text_list(element)
    assert result == 'Text Content <http://example.com|Example>'

def test_process_rich_text_section_or_preformatted(slack_block_processor):
    element = {'elements': [{'type': 'text', 'text': 'Text Content'}, {'type': 'link', 'url': 'http://example.com', 'text': 'Example'}]}
    result = slack_block_processor.process_rich_text_section_or_preformatted(element)
    assert result == 'Text Content <http://example.com|Example>'

def test_process_rich_text_block(slack_block_processor):
    block = {'elements': [{'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Rich Text Content'}]}]}
    result = slack_block_processor.process_rich_text_block(block)
    assert result == 'Rich Text Content'

def test_extract_text_from_mixed_blocks(slack_block_processor):
    blocks = [
        {'type': 'header', 'text': {'text': 'Header'}},
        {'type': 'context', 'elements': [{'type': 'mrkdwn', 'text': 'Context'}]},
        {'type': 'rich_text', 'elements': [{'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Rich Text'}]}]},
        {'type': 'input', 'label': {'text': 'Label'}, 'element': {'placeholder': {'text': 'Placeholder'}}}
    ]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == 'Header Context Rich Text Label Placeholder'

def test_extract_text_from_unknown_block(slack_block_processor):
    blocks = [{'type': 'unknown', 'text': 'Unknown Block'}]
    result = slack_block_processor.extract_text_from_blocks(blocks)
    assert result == "{'type': 'unknown', 'text': 'Unknown Block'}"

def test_process_rich_text_list_with_various_elements(slack_block_processor):
    element = {
        'elements': [
            {'type': 'text', 'text': 'Text'},
            {'type': 'link', 'url': 'http://example.com', 'text': 'Link'},
            {'type': 'user', 'user_id': 'U123'},
            {'type': 'team', 'team_id': 'T123'},
            {'type': 'channel', 'channel_id': 'C123'},
            {'type': 'emoji', 'name': 'smile'},
            {'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Nested'}]}
        ]
    }
    result = slack_block_processor.process_rich_text_list(element)
    expected = 'Text <http://example.com|Link> User Mention: <@U123> Team Mention: <!subteam^T123> Channel Mention: <#C123> :smile: Nested'
    assert result == expected

def test_process_rich_text_section_with_various_elements(slack_block_processor):
    element = {
        'elements': [
            {'type': 'text', 'text': 'Text'},
            {'type': 'link', 'url': 'http://example.com', 'text': 'Link'},
            {'type': 'user', 'user_id': 'U123'},
            {'type': 'team', 'team_id': 'T123'},
            {'type': 'channel', 'channel_id': 'C123'},
            {'type': 'emoji', 'name': 'smile'},
            {'type': 'broadcast', 'range': 'here'}
        ]
    }
    result = slack_block_processor.process_rich_text_section_or_preformatted(element)
    expected = 'Text <http://example.com|Link> User Mention: <@U123> Team Mention: <!subteam^T123> Channel Mention: <#C123> :smile: Broadcast: <here>'
    assert result == expected

def test_process_rich_text_list_with_link_without_text(slack_block_processor):
    element = {'elements': [{'type': 'link', 'url': 'http://example.com'}]}
    result = slack_block_processor.process_rich_text_list(element)
    assert result == '<http://example.com|http://example.com>'

def test_process_rich_text_block_with_multiple_elements(slack_block_processor):
    block = {
        'elements': [
            {'type': 'rich_text_section', 'elements': [{'type': 'text', 'text': 'Section 1'}]},
            {'type': 'rich_text_list', 'elements': [{'type': 'text', 'text': 'List Item'}]},
            {'type': 'rich_text_preformatted', 'elements': [{'type': 'text', 'text': 'Preformatted'}]}
        ]
    }
    result = slack_block_processor.process_rich_text_block(block)
    assert result == 'Section 1 List Item Preformatted'
