from django.db import models
from django.contrib.auth.models import User
import uuid


class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


ORDER_STATUS_CHOICES = [
    ('pending',   'Pending'),
    ('confirmed', 'Confirmed'),
    ('packed',    'Packed'),
    ('shipped',   'Shipped'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled'),
    ('refunded',  'Refunded'),
]

PAYMENT_METHOD_CHOICES = [
    ('cod',           'Cash on Delivery'),
    ('gcash',         'GCash (Manual)'),
    ('bank_transfer', 'Bank Transfer'),
    ('stripe',        'Stripe / Card'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending',   'Pending'),
    ('submitted', 'Proof Submitted'),
    ('confirmed', 'Confirmed'),
    ('failed',    'Failed'),
    ('refunded',  'Refunded'),
]


class Order(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = 'BC-' + str(uuid.uuid4()).upper()[:8]
        super().save(*args, **kwargs)

    def get_status_choices(self):
        return self._meta.get_field('status').choices

    def __str__(self):
        return f"Order {self.order_number} by {self.buyer.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sold_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_name = models.CharField(max_length=200, default='')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def get_status_choices(self):
        return self._meta.get_field('status').choices

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


from django.conf import settings
from django.db import models

class OrderStatusLog(models.Model):
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='status_logs'
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='order_status_changes'
    )

    old_status = models.CharField(max_length=32, null=True, blank=True)
    new_status = models.CharField(max_length=32)

    note = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Order Status Log"
        verbose_name_plural = "Order Status Logs"

    def __str__(self):
        return f"{self.order_id}: {self.old_status} -> {self.new_status}"




class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proof_image = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True)
    sender_name = models.CharField(max_length=100, blank=True)
    stripe_session_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.order.order_number} — {self.method} — {self.status}"