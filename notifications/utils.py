from .models import Notification


def create_notification(recipient, notif_type, message, link='', actor=None):
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notif_type=notif_type,
        message=message,
        link=link,
    )