import io
import logging
from decimal import Decimal

from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def create_order_from_cart(user, cart_items, shipping_address, notes=''):
    """
    Creates order. Does NOT deduct stock at this point.
    Stock is deducted only when seller marks item as delivered.
    """
    from .models import Order, OrderItem, Product, OrderStatusLog
    from django.db import transaction

    if not cart_items:
        return None, ['Cart is empty.']

    shipping_address = (shipping_address or '').strip()
    if not shipping_address:
        return None, ['Shipping address required.']

    errors = []
    valid_items = []
    total = Decimal('0')

    for ci in cart_items:
        # Accept different keys: product_id / id / pk
        pid = ci.get('product_id') or ci.get('id') or ci.get('pk')
        try:
            product = Product.objects.get(pk=pid, is_active=True)
        except Exception:
            errors.append(f"Product #{pid} not found.")
            continue

        qty = max(int(ci.get('quantity', 1) or 1), 1)

        # Still validate stock (so buyer can’t order beyond available),
        # but do NOT deduct here.
        if product.stock < qty:
            if product.stock == 0:
                errors.append(f"'{product.name}' is out of stock.")
            else:
                errors.append(f"'{product.name}' only has {product.stock} left.")
            continue

        valid_items.append((product, qty))
        total += (product.price * qty)

    if errors:
        return None, errors

    if not valid_items:
        return None, ['No valid products in cart.']

    with transaction.atomic():
        order = Order.objects.create(
            buyer=user,
            shipping_address=shipping_address,
            notes=notes or '',
            total_amount=total,
            status='pending',
        )

        for product, qty in valid_items:
            OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller,
                quantity=qty,
                unit_price=product.price,
                product_name=product.name,
                status='pending',
            )

        # ✅ Correct log fields
        OrderStatusLog.objects.create(
            order=order,
            changed_by=user,
            old_status=None,
            new_status='pending',
            note='Order placed by buyer.',
        )

    # ✅ IMPORTANT: return values so checkout_submit works correctly
    return order, []


def update_order_item_status(order_item, new_status, changed_by):
    """
    Updates item status. When DELIVERED, deducts stock from product.
    """
    from .models import OrderStatusLog

    valid = [s[0] for s in order_item._meta.get_field('status').choices]
    if new_status not in valid:
        return False, 'Invalid status.'

    if order_item.seller != changed_by:
        return False, 'You do not own this order item.'

    old_status = order_item.status
    order_item.status = new_status

    # These fields must exist in your OrderItem model, otherwise remove these lines
    if new_status == 'shipped' and hasattr(order_item, 'shipped_at'):
        order_item.shipped_at = timezone.now()

    if new_status == 'delivered':
        if hasattr(order_item, 'delivered_at'):
            order_item.delivered_at = timezone.now()

        # ✅ Deduct stock on delivery only
        if order_item.product:
            product = order_item.product
            product.stock = max(0, product.stock - order_item.quantity)
            product.save(update_fields=['stock'])

    order_item.save()

    # ✅ Log the item update on the order timeline
    OrderStatusLog.objects.create(
        order=order_item.order,
        changed_by=changed_by,
        old_status=old_status,
        new_status=new_status,
        note=f'Item "{order_item.product_name}" updated to {new_status}.',
    )

    # ✅ Update parent order to most advanced item status
    STATUS_RANK = {
        'pending': 0,
        'confirmed': 1,
        'packed': 2,
        'shipped': 3,
        'delivered': 4,
        'cancelled': 5,
        'refunded': 6,
    }

    order = order_item.order
    all_statuses = list(order.items.values_list('status', flat=True))

    if all_statuses:
        most_advanced = max(all_statuses, key=lambda s: STATUS_RANK.get(s, 0))
        if order.status != most_advanced:
            old_order_status = order.status
            order.status = most_advanced

            if most_advanced == 'shipped' and hasattr(order, 'shipped_at') and not getattr(order, 'shipped_at', None):
                order.shipped_at = timezone.now()

            if most_advanced == 'delivered' and hasattr(order, 'delivered_at') and not getattr(order, 'delivered_at', None):
                order.delivered_at = timezone.now()

            order.save()

            # ✅ Log order-level change too (optional but good)
            OrderStatusLog.objects.create(
                order=order,
                changed_by=changed_by,
                old_status=old_order_status,
                new_status=most_advanced,
                note=f'Order status updated based on items (now {most_advanced}).',
            )

    return True, None


def send_invoice_email(user, order):
    try:
        _send_invoice(user, order)
    except Exception as e:
        logger.warning(f"Invoice email failed for order {order.id}: {e}")


def send_order_update_email(order, new_status):
    try:
        user = order.buyer
        if not user.email:
            return

        status_display = dict(order._meta.get_field('status').choices).get(new_status, new_status)
        subject = f"BizConnect — Order {order.order_number} is now {status_display}"

        text_body = (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Your order {order.order_number} has been updated.\n"
            f"New Status: {status_display}\n\n"
            f"Total: PHP {order.total_amount:,.2f}\n\n"
            f"— BizConnect Team"
        )

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#FAF8F4;font-family:sans-serif;">
  <div style="max-width:560px;margin:40px auto;background:#fff;border-radius:12px;
              overflow:hidden;border:1px solid rgba(0,0,0,0.08);">
    <div style="background:#1C1C1E;padding:28px 32px;">
      <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;color:#C9A96E;">
        BizConnect
      </span>
    </div>
    <div style="padding:32px;">
      <h2 style="font-family:Georgia,serif;color:#1C1C1E;margin:0 0 16px;">Order Update</h2>
      <p style="color:#6E6E73;margin:0 0 24px;">Hi {user.get_full_name() or user.username},</p>
      <div style="background:#FAF8F4;border-radius:8px;padding:20px;margin-bottom:24px;">
        <div style="margin-bottom:8px;">
          <span style="font-size:12px;color:#6E6E73;text-transform:uppercase;">Order</span><br/>
          <strong>{order.order_number}</strong>
        </div>
        <div style="margin-bottom:8px;">
          <span style="font-size:12px;color:#6E6E73;text-transform:uppercase;">Status</span><br/>
          <strong style="color:#C9A96E;font-size:16px;">{status_display}</strong>
        </div>
        <div>
          <span style="font-size:12px;color:#6E6E73;text-transform:uppercase;">Total</span><br/>
          <strong>PHP {order.total_amount:,.2f}</strong>
        </div>
      </div>
      <a href="{site_url}/shop/order/{order.id}/"
         style="display:inline-block;background:#C9A96E;color:#1C1C1E;
                padding:12px 28px;border-radius:100px;font-weight:600;
                text-decoration:none;font-size:14px;">
        Track My Order
      </a>
    </div>
    <div style="padding:16px 32px;border-top:1px solid rgba(0,0,0,0.06);
                color:#AEAEB2;font-size:12px;">
      BizConnect — Premium Philippine Marketplace
    </div>
  </div>
</body></html>"""

        msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send()

    except Exception as e:
        logger.warning(f"Order update email failed: {e}")


def _send_invoice(user, order):
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=54, bottomMargin=54,
        leftMargin=54, rightMargin=54
    )
    styles = getSampleStyleSheet()
    el = []

    el.append(Paragraph("BIZCONNECT", styles['Title']))
    el.append(Paragraph("Premium Philippine Marketplace", styles['Normal']))
    el.append(Spacer(1, 16))
    el.append(Paragraph(f"<b>Invoice — Order {order.order_number}</b>", styles['Heading2']))
    el.append(Paragraph(f"Date: {order.created_at.strftime('%B %d, %Y')}", styles['Normal']))
    el.append(Paragraph(f"Buyer: {user.get_full_name() or user.username}", styles['Normal']))
    el.append(Paragraph(f"Email: {user.email}", styles['Normal']))
    if order.shipping_address:
        el.append(Paragraph(f"Ship to: {order.shipping_address}", styles['Normal']))
    el.append(Spacer(1, 16))

    data = [['Product', 'Qty', 'Unit Price', 'Subtotal']]
    for item in order.items.all():
        data.append([
            item.product_name,
            str(item.quantity),
            f"PHP {item.unit_price:,.2f}",
            f"PHP {item.subtotal:,.2f}",
        ])
    data.append(['', '', 'TOTAL', f"PHP {order.total_amount:,.2f}"])

    t = Table(data, colWidths=[240, 60, 110, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),  (-1, 0),  colors.HexColor('#1C1C1E')),
        ('TEXTCOLOR',      (0, 0),  (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0),  (-1, 0),  'Helvetica-Bold'),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND',     (0, -1), (-1, -1), colors.HexColor('#F0EDE6')),
        ('ROWBACKGROUNDS', (0, 1),  (-1, -2), [colors.white, colors.HexColor('#FAF8F4')]),
        ('GRID',           (0, 0),  (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
        ('ALIGN',          (1, 0),  (-1, -1), 'CENTER'),
        ('TOPPADDING',     (0, 0),  (-1, -1), 8),
        ('BOTTOMPADDING',  (0, 0),  (-1, -1), 8),
        ('LEFTPADDING',    (0, 0),  (-1, -1), 10),
    ]))
    el.append(t)
    el.append(Spacer(1, 20))
    el.append(Paragraph(
        "Salamat sa iyong pagbili! Thank you for shopping with BizConnect.",
        styles['Normal']
    ))

    doc.build(el)
    pdf = buf.getvalue()
    buf.close()

    if not user.email:
        return

    msg = EmailMultiAlternatives(
        subject=f"BizConnect Invoice — Order {order.order_number}",
        body=(
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Thank you for your order {order.order_number}.\n"
            f"Total: PHP {order.total_amount:,.2f}\n\n"
            f"— BizConnect Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach(f"invoice_{order.order_number}.pdf", pdf, 'application/pdf')
    msg.send()