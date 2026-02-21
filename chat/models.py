from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='buyer_conversations')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('buyer', 'seller')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat: {self.buyer.username} ↔ {self.seller.username}"

    def other_user(self, user):
        return self.seller if user == self.buyer else self.buyer

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"
