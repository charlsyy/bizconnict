import json
import logging
import csv
from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import seller_required, login_required_custom
from notifications.utils import create_notification
from .models import Order, OrderItem, OrderStatusLog, Product, Payment
from .services import (
    create_order_from_cart, update_order_item_status,
    send_invoice_email, send_order_update_email
)
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.urls import reverse

logger = logging.getLogger(__name__)


# ── SHOP ──────────────────────────────────────────────────────────────────

def product_list(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_active=True).select_related('seller')
    if query:
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)
    products = products.order_by('-created_at')
    return render(request, 'shop/product_list.html', {'products': products, 'query': query})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, 'shop/product_detail.html', {'product': product})


@login_required_custom
def cart_page(request):
    return render(request, 'shop/cart.html')


@login_required_custom
def checkout_page(request):
    return render(request, 'shop/checkout.html')


@login_required_custom
def checkout_submit(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    cart_items = data.get('items', [])
    shipping = (data.get('shipping_address', '') or '').strip()
    notes = (data.get('notes', '') or '').strip()

    if not shipping:
        return JsonResponse({'success': False, 'error': 'Shipping address required.'}, status=400)

    order, errors = create_order_from_cart(request.user, cart_items, shipping, notes)
    if not order:
        return JsonResponse({'success': False, 'error': ' '.join(errors or ['Order failed'])}, status=400)

    # buyer notification
    create_notification(
        recipient=request.user,
        notif_type='order',
        message=f"Order {order.order_number} placed! Total: PHP {order.total_amount:,.2f}",
        link=f"/shop/order/{order.id}/",
    )

    # seller notification (one per seller)
    notified = set()
    for item in order.items.all():
        if item.seller and item.seller_id not in notified:
            notified.add(item.seller_id)
            create_notification(
                recipient=item.seller,
                notif_type='order',
                message=f"New order {order.order_number} from {request.user.username}.",
                link="/shop/seller/orders/",
            )

    # invoice email (safe)
    send_invoice_email(request.user, order)

    return JsonResponse({'success': True, 'order_id': order.id, 'order_number': order.order_number})


# ── ORDERS ────────────────────────────────────────────────────────────────

@login_required_custom
def my_orders(request):
    orders = Order.objects.filter(buyer=request.user).prefetch_related(
        'items', 'items__seller', 'status_logs'
    ).order_by('-created_at')
    return render(request, 'shop/my_orders.html', {'orders': orders})


@login_required_custom
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    seller_ids = list(order.items.values_list('seller_id', flat=True))
    if request.user != order.buyer and request.user.id not in seller_ids and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('product_list')

    logs = order.status_logs.all().order_by('created_at')
    return render(request, 'shop/order_detail.html', {'order': order, 'logs': logs})


# ── PAYMENT ───────────────────────────────────────────────────────────────

@login_required_custom
def payment_page(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    return render(request, 'shop/payment.html', {'order': order})


@login_required_custom
@require_POST
def payment_cod(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)

    Payment.objects.update_or_create(
        order=order,
        defaults={'method': 'cod', 'status': 'pending', 'amount': order.total_amount}
    )

    old = order.status
    order.status = 'confirmed'
    order.save(update_fields=['status'])

    OrderStatusLog.objects.create(
        order=order,
        changed_by=request.user,
        old_status=old,
        new_status='confirmed',
        note='Payment method: Cash on Delivery.',
    )

    messages.success(request, "Order confirmed! Pay the courier upon delivery.")
    return redirect('order_detail', order_id=order.id)


@login_required_custom
@require_POST
def payment_manual_submit(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    method = request.POST.get('method', 'gcash')
    reference = (request.POST.get('reference_number', '') or '').strip()
    sender_name = (request.POST.get('sender_name', '') or '').strip()
    proof = request.FILES.get('proof_image')

    if not reference:
        messages.error(request, "Reference number is required.")
        return redirect('payment_page', order_id=order.id)
    if not proof:
        messages.error(request, "Please upload your payment screenshot.")
        return redirect('payment_page', order_id=order.id)

    payment, _ = Payment.objects.update_or_create(
        order=order,
        defaults={
            'method': method,
            'status': 'submitted',
            'amount': order.total_amount,
            'reference_number': reference,
            'sender_name': sender_name,
        }
    )
    payment.proof_image = proof
    payment.save()

    messages.success(request, "Payment proof submitted! Waiting for seller to confirm.")
    return redirect('order_detail', order_id=order.id)


@login_required_custom
def payment_stripe_redirect(request, order_id):
    from .payment_handlers import create_stripe_session
    from django.conf import settings as s

    order = get_object_or_404(Order, pk=order_id, buyer=request.user)

    site_url = getattr(s, 'SITE_URL', 'http://127.0.0.1:8000')
    session_url, session_id, error = create_stripe_session(
        order,
        success_url=f"{site_url}/shop/order/{order.id}/payment/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{site_url}/shop/order/{order.id}/payment/",
    )

    if error:
        messages.error(request, f"Stripe error: {error}")
        return redirect('payment_page', order_id=order.id)

    Payment.objects.update_or_create(
        order=order,
        defaults={
            'method': 'stripe',
            'status': 'pending',
            'amount': order.total_amount,
            'stripe_session_id': session_id,
        }
    )
    return redirect(session_url)


@login_required_custom
def payment_stripe_success(request, order_id):
    from .payment_handlers import verify_stripe_session
    from django.utils import timezone as tz

    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    session_id = request.GET.get('session_id', '').strip()

    if not session_id:
        messages.error(request, "Invalid payment session.")
        return redirect('order_detail', order_id=order.id)

    status = verify_stripe_session(session_id)

    if status == 'paid':
        Payment.objects.update_or_create(
            order=order,
            defaults={
                'method': 'stripe',
                'status': 'confirmed',
                'amount': order.total_amount,
                'stripe_session_id': session_id,
                'paid_at': tz.now(),
            }
        )

        old = order.status
        order.status = 'confirmed'
        order.save(update_fields=['status'])

        OrderStatusLog.objects.create(
            order=order,
            changed_by=None,
            old_status=old,
            new_status='confirmed',
            note='Payment confirmed via Stripe.',
        )

        create_notification(
            recipient=request.user,
            notif_type='order',
            message=f"Stripe payment confirmed for order {order.order_number}!",
            link=f"/shop/order/{order.id}/",
        )

        messages.success(request, f"Payment confirmed! Order {order.order_number} is being processed.")
    else:
        messages.warning(request, "Payment not yet confirmed.")

    return redirect('order_detail', order_id=order.id)


@login_required_custom
def payment_stripe_cancel(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    messages.warning(request, "Stripe payment was cancelled.")
    return redirect('payment_page', order_id=order.id)


@seller_required
@require_POST
def confirm_payment_proof(request, order_id):
    from django.utils import timezone as tz

    order = get_object_or_404(Order, pk=order_id)

    # Seller can only confirm if they have items in this order
    if not order.items.filter(seller=request.user).exists():
        messages.error(request, "You don't have items in this order.")
        return redirect('seller_orders')

    try:
        payment = order.payment
    except Payment.DoesNotExist:
        messages.error(request, "No payment record found for this order.")
        return redirect('seller_orders')

    try:
        payment.status = 'confirmed'
        # only set paid_at if your model has it
        if hasattr(payment, 'paid_at'):
            payment.paid_at = tz.now()
        payment.save()

        old = order.status
        order.status = 'confirmed'
        order.save(update_fields=['status'])

        OrderStatusLog.objects.create(
            order=order,
            changed_by=request.user,
            old_status=old,
            new_status='confirmed',
            note='Payment proof verified by seller.',
        )

        create_notification(
            recipient=order.buyer,
            notif_type='order',
            message=f"Your payment for order {order.order_number} has been confirmed!",
            link=f"/shop/order/{order.id}/",
        )

        messages.success(request, f"Payment for order {order.order_number} confirmed.")
    except Exception as e:
        messages.error(request, f"Error: {e}")

    return redirect('seller_orders')

# ── SELLER ────────────────────────────────────────────────────────────────

@seller_required
def seller_dashboard(request):
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'shop/seller_dashboard.html', {'products': products})


@seller_required
def seller_orders(request):
    order_items = OrderItem.objects.filter(seller=request.user).select_related(
        'order', 'order__buyer', 'product'
    ).order_by('-order__created_at')
    return render(request, 'shop/seller_orders.html', {'order_items': order_items})


@seller_required
@require_POST
def update_item_status(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    new_status = request.POST.get('status')

    success, error = update_order_item_status(item, new_status, request.user)
    if not success:
        messages.error(request, error)
        return redirect('seller_orders')

    messages.success(request, f"Order item updated to {new_status}.")
    create_notification(
        recipient=item.order.buyer,
        notif_type='order',
        message=f"Order {item.order.order_number}: {item.product_name} is now {new_status}.",
        link=f"/shop/order/{item.order.id}/",
    )
    send_order_update_email(item.order, new_status)
    return redirect('seller_orders')


@seller_required
def seller_reports(request):
    items = OrderItem.objects.filter(seller=request.user).select_related('order', 'order__buyer')
    total_orders = items.values('order').distinct().count()
    total_items = sum(i.quantity for i in items)
    total_revenue = sum(i.subtotal for i in items)

    if request.GET.get('download') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order Number', 'Buyer', 'Product', 'Qty', 'Unit Price', 'Subtotal', 'Status', 'Date'])
        for item in items:
            writer.writerow([
                item.order.order_number, item.order.buyer.username,
                item.product_name, item.quantity,
                f"PHP {item.unit_price:,.2f}", f"PHP {item.subtotal:,.2f}",
                item.status, item.order.created_at.strftime('%Y-%m-%d'),
            ])
        return response

    return render(request, 'shop/seller_reports.html', {
        'items': items,
        'total_orders': total_orders,
        'total_items': total_items,
        'total_revenue': total_revenue,
    })

@seller_required
def product_create(request):
    if request.method == 'POST':
        name = (request.POST.get('name', '') or '').strip()
        description = (request.POST.get('description', '') or '').strip()
        price_str = (request.POST.get('price', '') or '').strip()
        stock_str = (request.POST.get('stock', '0') or '0').strip()

        errors = []
        if not name:
            errors.append("Product name required.")

        try:
            price = Decimal(price_str)
            if price <= 0:
                errors.append("Price must be positive.")
        except Exception:
            errors.append("Invalid price.")
            price = Decimal('0')

        try:
            stock = int(stock_str)
            if stock < 0:
                stock = 0
        except Exception:
            stock = 0

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'shop/product_form.html', {'action': 'Create'})

        p = Product(
            seller=request.user,
            name=name,
            description=description,
            price=price,
            stock=stock,
            is_active=True,
        )

        if request.FILES.get('image'):
            p.image = request.FILES['image']

        p.save()
        messages.success(request, "Product created.")
        return redirect('seller_dashboard')

    return render(request, 'shop/product_form.html', {'action': 'Create'})


@seller_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)

    if request.method == 'POST':
        product.name = (request.POST.get('name', '') or '').strip()
        product.description = (request.POST.get('description', '') or '').strip()

        try:
            product.price = Decimal((request.POST.get('price', '0') or '0').strip())
        except Exception:
            messages.error(request, "Invalid price.")
            return render(request, 'shop/product_form.html', {'action': 'Edit', 'product': product})

        try:
            product.stock = int((request.POST.get('stock', '0') or '0').strip())
            if product.stock < 0:
                product.stock = 0
        except Exception:
            product.stock = 0

        if request.FILES.get('image'):
            product.image = request.FILES['image']

        product.save()
        messages.success(request, "Product updated.")
        return redirect('seller_dashboard')

    return render(request, 'shop/product_form.html', {'action': 'Edit', 'product': product})


@seller_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    product.is_active = False
    product.save(update_fields=['is_active'])
    messages.success(request, "Product removed.")
    return redirect('seller_dashboard')

def _pick_redirect(user):
    # Admin / superuser goes to your CUSTOM admin dashboard (not /admin/)
    if user.is_superuser or user.is_staff:
        return reverse('admin_dashboard')

    # seller/buyer based on profile.role
    role = getattr(getattr(user, 'profile', None), 'role', None)
    if role == 'seller':
        return reverse('seller_dashboard')

    return reverse('product_list')


@require_POST
def firebase_auth(request):
    """
    Receives JSON from your login.html:
      { email: "...", id_token / idToken: "..." }

    Logs in the Django user by email, then returns redirect URL.
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    email = (body.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"success": False, "error": "Email required"}, status=400)

    User = get_user_model()

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)

    # ✅ login user into Django session
    login(request, user)

    return JsonResponse({
        "success": True,
        "redirect": _pick_redirect(user),
    })