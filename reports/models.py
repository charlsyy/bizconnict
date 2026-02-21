from django.db import models
from django.contrib.auth.models import User

TARGET_TYPES = [
    ('buyer',    'Buyer'),
    ('seller',   'Seller'),
    ('product',  'Product'),
    ('post',     'Feed Post'),
    ('question', 'Community Question'),
]

REPORT_STATUS = [
    ('pending',   'Pending'),
    ('reviewing', 'Reviewing'),
    ('resolved',  'Resolved'),
    ('rejected',  'Rejected'),
]

REPORT_REASONS = [
    ('spam',      'Spam'),
    ('fake',      'Fake / Misleading'),
    ('offensive', 'Offensive Content'),
    ('scam',      'Scam / Fraud'),
    ('other',     'Other'),
]


class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_filed')
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField()
    evidence = models.ImageField(upload_to='reports/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report #{self.id} — {self.target_type} #{self.target_id}"