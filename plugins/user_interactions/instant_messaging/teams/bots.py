# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import json
import os
from typing import List

from botbuilder.core import CardFactory, MessageFactory, TurnContext
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import (
    Activity,
    Attachment,
    CardAction,
    ConversationParameters,
    HeroCard,
    Mention,
)
from botbuilder.schema._connector_client_enums import ActionTypes
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"

class TeamsConversationBot(TeamsActivityHandler):
    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password

    async def on_teams_members_added(  # pylint: disable=unused-argument
        self,
        teams_members_added: [TeamsChannelAccount],
        team_info: TeamInfo,
        turn_context: TurnContext,
    ):
        for member in teams_members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    f"Welcome to the team { member.given_name } { member.surname }. "
                )

    async def on_message_activity(self, turn_context: TurnContext,):
        #TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip().lower()
        if text.startswith("special action"):
            # Extract the string after "special action"
            emoji = text[len("special action"):].strip()

            # Call the method with the extracted string as an additional parameter
            if emoji == "👀":
                await turn_context.send_activity(emoji)
            #await self.send_special_action_card(turn_context, emoji)
        else:
            # Otherwise, process normally
            text = f"{turn_context.activity.text.strip()}"
            await turn_context.send_activity(text)

        return

    async def send_special_action_card(self, turn_context: TurnContext, text):
        # Define the Adaptive Card content
        card_content = {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": text,
                    "horizontalAlignment": "Center",
                    "size": "Default",
                    "weight": "Lighter",
                    "color": "Default",
                    "wrap": True
                }
            ],
            "version": "1.3",
            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json"
        }

        # Create the attachment for the Adaptive Card
        attachment = Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=card_content
        )

        # Prepare the activity with the adaptive card
        message = MessageFactory.attachment(attachment)

        # Send the adaptive card to the user
        await turn_context.send_activity(message)

    async def _mention_adaptive_card_activity(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
                return
            else:
                raise

        card_path = os.path.join(os.getcwd(), ADAPTIVECARDTEMPLATE)
        with open(card_path, "rb") as in_file:
            template_json = json.load(in_file)
        
        USERNAME_PLACEHOLDER = "${userName}"
        for t in template_json["body"]:
            t["text"] = t["text"].replace(USERNAME_PLACEHOLDER, member.name)
        for e in template_json["msteams"]["entities"]:
            e["text"] = e["text"].replace(USERNAME_PLACEHOLDER, member.name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userUPN}", member.user_principal_name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userAAD}", member.additional_properties["aadObjectId"])
            e["mentioned"]["name"] = e["mentioned"]["name"].replace(USERNAME_PLACEHOLDER, member.name)

        adaptive_card_attachment = Activity(
            attachments=[CardFactory.adaptive_card(template_json)]
        )
        await turn_context.send_activity(adaptive_card_attachment)

    async def _mention_activity(self, turn_context: TurnContext):
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{turn_context.activity.from_property.name}</at>",
            type="mention",
        )

        reply_activity = MessageFactory.text(f"Hello {mention.text}")
        reply_activity.entities = [Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity)

    async def _send_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.message_back,
                title="Message all members",
                text="messageallmembers",
            ),
            CardAction(type=ActionTypes.message_back, title="Who am I?", text="whoami"),
            CardAction(type=ActionTypes.message_back, title="Find me in Adaptive Card", text="mention me"),
            CardAction(
                type=ActionTypes.message_back, title="Delete card", text="deletecard"
            ),
        ]
        if isUpdate:
            await self._send_update_card(turn_context, buttons)
        else:
            await self._send_welcome_card(turn_context, buttons)

    async def _send_welcome_card(self, turn_context: TurnContext, buttons):
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value={"count": 0},
            )
        )
        card = HeroCard(
            title="Welcome Card", text="Click the buttons.", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _send_update_card(self, turn_context: TurnContext, buttons):
        data = turn_context.activity.value
        data["count"] += 1
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value=data,
            )
        )
        card = HeroCard(
            title="Updated card", text=f"Update count {data['count']}", buttons=buttons
        )

        updated_activity = MessageFactory.attachment(CardFactory.hero_card(card))
        updated_activity.id = turn_context.activity.reply_to_id
        await turn_context.update_activity(updated_activity)

    async def _get_member(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
            else:
                raise
        else:
            await turn_context.send_activity(f"You are: {member.name}")

    async def _message_all_members(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)

        for member in team_members:
            conversation_reference = TurnContext.get_conversation_reference(
                turn_context.activity
            )

            conversation_parameters = ConversationParameters(
                is_group=False,
                bot=turn_context.activity.recipient,
                members=[member],
                tenant_id=turn_context.activity.conversation.tenant_id,
            )

            async def get_ref(tc1):
                conversation_reference_inner = TurnContext.get_conversation_reference(
                    tc1.activity
                )
                return await tc1.adapter.continue_conversation(
                    conversation_reference_inner, send_message, self._app_id
                )

            async def send_message(tc2: TurnContext):
                return await tc2.send_activity(
                    f"Hello {member.name}. I'm a Teams conversation bot."
                )  # pylint: disable=cell-var-from-loop

            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

        await turn_context.send_activity(
            MessageFactory.text("All messages have been sent")
        )

    async def _get_paged_members(
        self, turn_context: TurnContext
    ) -> List[TeamsChannelAccount]:
        paged_members = []
        continuation_token = None

        while True:
            current_page = await TeamsInfo.get_paged_members(
                turn_context, continuation_token, 100
            )
            continuation_token = current_page.continuation_token
            paged_members.extend(current_page.members)

            if continuation_token is None:
                break

        return paged_members

    async def _delete_card_activity(self, turn_context: TurnContext):
        await turn_context.delete_activity(turn_context.activity.reply_to_id)
