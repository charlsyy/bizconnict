from django.db import models
from django.contrib.auth.models import User

REACTION_TYPES = [
    ('like',  'Like'),
    ('heart', 'Heart'),
    ('wow',   'Wow'),
    ('sad',   'Sad'),
    ('angry', 'Angry'),
]

REACTION_ICONS = {
    'like':  '👍',
    'heart': '❤️',
    'wow':   '😮',
    'sad':   '😢',
    'angry': '😡',
}


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    video = models.FileField(upload_to='posts/videos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username}: {self.text[:50]}"

def _reaction_summary(self):
    return PostReaction.objects.filter(post=self).values('reaction_type').annotate(count=models.Count('id'))


class PostReaction(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')