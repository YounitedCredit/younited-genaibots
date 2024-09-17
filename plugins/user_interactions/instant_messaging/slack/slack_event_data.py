from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)


class SlackEventData(IncomingNotificationDataBase):
    def __init__(self, timestamp, event_label, channel_id, thread_id, response_id,
                 is_mention, text, origin, app_id=None, api_app_id=None, username=None, user_name=None,
                 user_email=None, user_id=None, images=None, files_content=None, raw_data=None,
                 origin_plugin_name=None, **kwargs):
        super().__init__(
            timestamp=timestamp,
            event_label=event_label,
            channel_id=channel_id,
            thread_id=thread_id,
            response_id=response_id,
            is_mention=is_mention,
            text=text,
            origin=origin,
            app_id=app_id,
            api_app_id=api_app_id,
            username=username,
            user_name=user_name,
            user_email=user_email,
            user_id=user_id,
            images=images,
            files_content=files_content,
            raw_data=raw_data,
            origin_plugin_name=origin_plugin_name
        )

        # Pour conserver la flexibilité, on peut ajouter d'autres attributs dynamiquement
        for key, value in kwargs.items():
            setattr(self, key, value)
