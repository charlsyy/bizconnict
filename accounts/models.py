from django.db import models
from django.contrib.auth.models import User

ROLE_CHOICES = [('buyer', 'Buyer'), ('seller', 'Seller')]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    firebase_uid = models.CharField(max_length=128, blank=True, null=True, unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_seller(self):
        return self.role == 'seller'

    @property
    def is_buyer(self):
        return self.role == 'buyer'

@property
def reaction_summary(self):
    return self._reaction_summary()

    def get_avatar_initial(self):
        return self.user.username[0].upper() if self.user.username else 'U'