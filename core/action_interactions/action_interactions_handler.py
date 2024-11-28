from collections import defaultdict

from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.genai_interactions.genai_response import GenAIResponse
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.user_interactions_dispatcher import (
    UserInteractionsDispatcher,
)


class ActionInteractionsHandler:
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        # Initialize any necessary variables or dependencies here
        if not isinstance(global_manager, GlobalManager):
            raise TypeError("global_manager must be an instance of GlobalManager")

        self.global_manager: GlobalManager = global_manager
        self.plugin_manager = global_manager.plugin_manager
        self.logger = global_manager.logger
        self.im_dispatcher: UserInteractionsDispatcher = self.global_manager.user_interactions_dispatcher
        self.available_actions = {}

    async def handle_action(self, action, event):
        action_input = ActionInput(action_name=action.ActionName, parameters=action.Parameters)
        action_plugin: ActionBase = self.global_manager.get_action(action.ActionName)

        if action_plugin is not None:
            try:
                self.logger.info(f'calling execute on action: [{action.ActionName}]')
                result = await action_plugin.execute(action_input, event=event)
                return result
            except Exception as e:
                self.logger.error(f"An error occurred while executing the action {action.ActionName}: {e}")
                await self.im_dispatcher.send_message(event,
                                                      f"An error occurred while executing the action {action.ActionName}: {e}",
                                                      is_internal=True)
                await self.im_dispatcher.send_message(event,
                                                      "There was a technical issue while processing your query, try again or ask for help to the bot admin !",
                                                      is_internal=False)
        return None

    async def handle_request(self, genai_response: GenAIResponse, event: IncomingNotificationDataBase):
        # Separate actions by type
        actions_by_type = defaultdict(list)
        for action in genai_response.response:
            actions_by_type[action.ActionName].append(action)

        # Process ObservationThought actions first
        for action in actions_by_type['ObservationThought']:
            await self.handle_action(action, event)

        # Then process UserInteraction actions
        for action in actions_by_type['UserInteraction']:
            await self.handle_action(action, event)

        # Process remaining actions
        for action_type, actions in actions_by_type.items():
            if action_type not in ['ObservationThought', 'UserInteraction']:
                for action in actions:
                    await self.handle_action(action, event)
