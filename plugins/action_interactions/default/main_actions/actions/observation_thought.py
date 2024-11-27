from core.action_interactions.action_base import ActionBase
from core.action_interactions.action_input import ActionInput
from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType


class ObservationThought(ActionBase):
    REQUIRED_PARAMETERS = ['observation', 'thought', 'plan', 'nextstep']

    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager: GlobalManager = global_manager
        self.user_interactions_text_plugin = None

        # Dispatchers
        self.user_interactions_dispatcher = self.global_manager.user_interactions_dispatcher
        self.genai_interactions_text_dispatcher = self.global_manager.genai_interactions_text_dispatcher
        self.backend_internal_data_processing_dispatcher = self.global_manager.backend_internal_data_processing_dispatcher

    async def execute(self, action_input: ActionInput, event: IncomingNotificationDataBase):
        parameters = action_input.parameters
        observation = parameters.get('observation', 'No Observation')
        autoeval = parameters.get('autoeval', 'No Autoeval')
        autoevaljustification = parameters.get('autoevaljustification', 'No Autoeval Justification')
        user_mood = parameters.get('usermood', 'No User Mood')
        thought = parameters.get('thought', 'No Thought')
        plan = parameters.get('plan', 'No Plan')
        nextstep = parameters.get('nextstep', 'No Next Step')
        # Implement the execution of the OBSERVATION_THOUGHT action
        message = f":mag: *Observation*: {observation} \n\n :brain: *Thought*: {thought} \n\n :clipboard: *Plan*: {plan} \n\n :rocket: *Next Step*: {nextstep} \n\n :bar_chart: *Autoeval*: {autoeval} \n\n :straight_ruler: *Autoeval Justification*: {autoevaljustification} \n\n :smiley: *User Mood*: {user_mood}"

        try:
            await self.user_interactions_dispatcher.send_message(event=event, message=message,
                                                                 message_type=MessageType.TEXT, title=None,
                                                                 is_internal=True)
        except Exception as e:
            print(f"An error occurred while sending the message: {e}")
