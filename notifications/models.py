from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models

actor = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='acted_notifications'
)

class Notification(models.Model):
    TYPE_CHOICES = [
        ('message', 'Chat Message'),
        ('order',   'Order Update'),
        ('system',  'System'),
        ('report',  'Report'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications_sent')
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    message = models.CharField(max_length=400)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"-> {self.recipient.username}: {self.message[:60]}"