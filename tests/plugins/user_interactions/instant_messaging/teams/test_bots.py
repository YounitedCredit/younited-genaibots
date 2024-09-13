from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botbuilder.core import TurnContext
from botbuilder.schema import (
    Activity,
    CardAction,
    ChannelAccount,
    ConversationAccount,
    HeroCard,
)
from botbuilder.schema._connector_client_enums import ActionTypes

from plugins.user_interactions.instant_messaging.teams.bots import (
    MessageFactory,
    TeamInfo,
    TeamsChannelAccount,
    TeamsConversationBot,
)


@pytest.fixture
def turn_context():
    context = MagicMock(spec=TurnContext)
    context.activity = Activity(
        type="message",
        text="Hello",
        from_property=ChannelAccount(id="user_id", name="User Name"),
        conversation=ConversationAccount(id="conversation_id", tenant_id="tenant_id"),
        recipient=ChannelAccount(id="bot_id"),
        service_url="https://service.url"
    )
    context.adapter = AsyncMock()
    context.send_activity = AsyncMock()
    return context

@pytest.fixture
def bot():
    return TeamsConversationBot(app_id="app_id", app_password="app_password")

@pytest.mark.asyncio
async def test_on_message_activity_special_action(bot, turn_context):
    turn_context.activity.text = "special action 👀"
    await bot.on_message_activity(turn_context)
    turn_context.send_activity.assert_called_once_with("👀")

@pytest.mark.asyncio
async def test_on_teams_members_added(bot, turn_context):
    members_added = [TeamsChannelAccount(id="1", given_name="John", surname="Doe")]
    team_info = MagicMock(spec=TeamInfo)

    await bot.on_teams_members_added(members_added, team_info, turn_context)
    turn_context.send_activity.assert_called_once_with("Welcome to the team John Doe. ")

@pytest.mark.asyncio
async def test_send_special_action_card(bot, turn_context):
    with patch('botbuilder.core.MessageFactory.attachment') as mock_message_factory:
        await bot.send_special_action_card(turn_context, "Test action")
        mock_message_factory.assert_called_once()
        turn_context.send_activity.assert_called_once()


@pytest.mark.asyncio
async def test_mention_activity(bot, turn_context):
    await bot._mention_activity(turn_context)
    turn_context.send_activity.assert_called_once()

@pytest.mark.asyncio
async def test_send_card(bot, turn_context):
    with patch.object(bot, '_send_welcome_card') as mock_welcome_card:
        await bot._send_card(turn_context, False)
        mock_welcome_card.assert_called_once()

    with patch.object(bot, '_send_update_card') as mock_update_card:
        await bot._send_card(turn_context, True)
        mock_update_card.assert_called_once()

@pytest.mark.asyncio
async def test_get_member(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_member') as mock_get_member:
        mock_get_member.return_value = TeamsChannelAccount(name="Test User")
        await bot._get_member(turn_context)
        turn_context.send_activity.assert_called_once_with("You are: Test User")

@pytest.mark.asyncio
async def test_message_all_members(bot, turn_context):
    with patch.object(bot, '_get_paged_members') as mock_get_paged_members:
        mock_get_paged_members.return_value = [TeamsChannelAccount(name="Test User")]
        with patch('botbuilder.core.TurnContext.get_conversation_reference'):
            with patch.object(turn_context.adapter, 'create_conversation'):
                await bot._message_all_members(turn_context)
                turn_context.send_activity.assert_called_with(MessageFactory.text("All messages have been sent"))

@pytest.mark.asyncio
async def test_delete_card_activity(bot, turn_context):
    await bot._delete_card_activity(turn_context)
    turn_context.delete_activity.assert_called_once_with(turn_context.activity.reply_to_id)

@pytest.mark.asyncio
async def test_get_member_not_found(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_member') as mock_get_member:
        mock_get_member.side_effect = Exception("MemberNotFoundInConversation")
        await bot._get_member(turn_context)
        turn_context.send_activity.assert_called_once_with("Member not found.")

@pytest.mark.asyncio
async def test_get_member_other_exception(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_member') as mock_get_member:
        mock_get_member.side_effect = Exception("Other error")
        with pytest.raises(Exception):
            await bot._get_member(turn_context)


@pytest.mark.asyncio
async def test_get_paged_members(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_paged_members') as mock_get_paged_members:
        mock_get_paged_members.side_effect = [
            AsyncMock(members=[TeamsChannelAccount(id="1")], continuation_token="token"),
            AsyncMock(members=[TeamsChannelAccount(id="2")], continuation_token=None)
        ]
        result = await bot._get_paged_members(turn_context)
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"

@pytest.mark.asyncio
async def test_on_message_activity_normal(bot, turn_context):
    turn_context.activity.text = "Hello, bot!"
    await bot.on_message_activity(turn_context)
    turn_context.send_activity.assert_called_once_with("Hello, bot!")

@pytest.mark.asyncio
async def test_mention_adaptive_card_activity(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_member') as mock_get_member, \
         patch('json.load') as mock_json_load, \
         patch('builtins.open', create=True) as mock_open, \
         patch('os.path.join') as mock_path_join:

        mock_member = TeamsChannelAccount(name="Test User", user_principal_name="test@example.com")
        mock_member.additional_properties = {"aadObjectId": "test_aad_id"}
        mock_get_member.return_value = mock_member

        mock_json_load.return_value = {
            "body": [{"text": "Hello ${userName}"}],
            "msteams": {
                "entities": [{
                    "text": "${userName}",
                    "mentioned": {
                        "id": "${userUPN}",
                        "name": "${userName}"
                    }
                }]
            }
        }
        mock_path_join.return_value = "fake_path"

        await bot._mention_adaptive_card_activity(turn_context)

        turn_context.send_activity.assert_called_once()

@pytest.mark.asyncio
async def test_send_welcome_card(bot, turn_context):
    buttons = [CardAction(type=ActionTypes.message_back, title="Test", text="test")]
    with patch('botbuilder.core.CardFactory.hero_card') as mock_card_factory:
        await bot._send_welcome_card(turn_context, buttons)

        mock_card_factory.assert_called_once()
        turn_context.send_activity.assert_called_once()

    # Vérifiez que les arguments passés à CardFactory.hero_card sont corrects
    call_args = mock_card_factory.call_args
    assert call_args is not None
    hero_card = call_args[0][0]
    assert isinstance(hero_card, HeroCard)
    assert hero_card.title == "Welcome Card"
    assert hero_card.text == "Click the buttons."
    assert len(hero_card.buttons) == len(buttons)  # Le bouton "Update Card" n'est pas ajouté

    # Vérifiez que les boutons originaux sont présents
    for original_button, card_button in zip(buttons, hero_card.buttons):
        assert original_button.title == card_button.title
        assert original_button.type == card_button.type
        assert original_button.text == card_button.text

@pytest.mark.asyncio
async def test_send_update_card(bot, turn_context):
    buttons = [CardAction(type=ActionTypes.message_back, title="Test", text="test")]
    turn_context.activity.value = {"count": 0}

    with patch('botbuilder.core.CardFactory.hero_card') as mock_card_factory:
        await bot._send_update_card(turn_context, buttons)

        mock_card_factory.assert_called_once()
        turn_context.update_activity.assert_called_once()

    # Vérifiez que les arguments passés à CardFactory.hero_card sont corrects
    call_args = mock_card_factory.call_args
    assert call_args is not None
    hero_card = call_args[0][0]
    assert isinstance(hero_card, HeroCard)
    assert hero_card.title == "Updated card"
    assert hero_card.text == "Update count 1"
    assert len(hero_card.buttons) == len(buttons)  # Le bouton "Update Card" n'est pas ajouté

    # Vérifiez que les boutons originaux sont présents
    for original_button, card_button in zip(buttons, hero_card.buttons):
        assert original_button.title == card_button.title
        assert original_button.type == card_button.type
        assert original_button.text == card_button.text

@pytest.mark.asyncio
async def test_get_paged_members_single_page(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_paged_members') as mock_get_paged_members:
        mock_get_paged_members.return_value = AsyncMock(members=[TeamsChannelAccount(id="1")], continuation_token=None)
        result = await bot._get_paged_members(turn_context)
        assert len(result) == 1
        assert result[0].id == "1"

@pytest.mark.asyncio
async def test_mention_adaptive_card_activity_member_not_found(bot, turn_context):
    with patch('botbuilder.core.teams.TeamsInfo.get_member') as mock_get_member:
        mock_get_member.side_effect = Exception("MemberNotFoundInConversation")
        await bot._mention_adaptive_card_activity(turn_context)
        turn_context.send_activity.assert_called_once_with("Member not found.")
