"""
AdminNotificationHandler
"""
from firebase_admin import messaging

from portal.libs.decorators.sentry_tracer import distributed_trace


class AdminNotificationHandler:
    """AdminNotificationHandler"""

    def __init__(self):
        pass


    @distributed_trace()
    async def send_message(self):
        """

        :return:
        """

        multicast_message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=instance.title,
                body=instance.message,
            ),
            data={
                "notification_id": str(instance.id),
                "type": str(instance.type)
            },
            tokens=tokens
        )
        result = messaging.send_each_for_multicast(multicast_message=multicast_message)
        messaging.send()
