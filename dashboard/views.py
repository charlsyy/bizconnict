from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count
from django.contrib.auth.models import User

from accounts.decorators import staff_required
from accounts.models import Profile
from shop.models import Product, Order, OrderItem
from community.models import Question
from reports.models import Report
from notifications.utils import create_notification


@staff_required
def overview(request):
    total_users = User.objects.count()
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(t=Sum('total_amount'))['t'] or 0
    pending_reports = Report.objects.filter(status='pending').count()
    recent_orders = Order.objects.select_related('buyer').order_by('-created_at')[:8]
    top_sellers = (
        OrderItem.objects
        .values('seller__username')
        .annotate(revenue=Sum('unit_price'), orders=Count('order', distinct=True))
        .order_by('-revenue')[:5]
    )
    return render(request, 'dashboard/overview.html', {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_reports': pending_reports,
        'recent_orders': recent_orders,
        'top_sellers': top_sellers,
    })


@staff_required
def manage_users(request):
    users = User.objects.select_related('profile').order_by('-date_joined')
    return render(request, 'dashboard/users.html', {'users': users})


@staff_required
@require_POST
def toggle_user_active(request, user_id):
    u = get_object_or_404(User, pk=user_id)
    if u == request.user:
        messages.error(request, "You cannot deactivate yourself.")
        return redirect('admin_users')
    u.is_active = not u.is_active
    u.save()
    state = "activated" if u.is_active else "deactivated"
    messages.success(request, f"User {u.username} has been {state}.")
    return redirect('admin_users')


@staff_required
def manage_shop(request):
    products = Product.objects.select_related('seller').order_by('-created_at')
    return render(request, 'dashboard/shop.html', {'products': products})


@staff_required
@require_POST
def admin_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save()
    messages.success(request, f"Product '{product.name}' hidden.")
    return redirect('admin_shop')


@staff_required
def manage_orders(request):
    orders = Order.objects.select_related('buyer').prefetch_related('items').order_by('-created_at')
    return render(request, 'dashboard/orders.html', {'orders': orders})


@staff_required
@require_POST
def admin_update_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    new_status = request.POST.get('status')
    valid_statuses = ['pending','confirmed','packed','shipped','delivered','cancelled','refunded']
    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        messages.success(request, f"Order {order.order_number} updated to {new_status}.")
    return redirect('admin_orders')


@staff_required
def manage_community(request):
    from community.models import Question
    questions = Question.objects.select_related('author').order_by('-created_at')
    return render(request, 'dashboard/community.html', {'questions': questions})


@staff_required
@require_POST
def admin_delete_question(request, pk):
    from community.models import Question
    q = get_object_or_404(Question, pk=pk)
    q.is_active = False
    q.save()
    messages.success(request, "Post removed.")
    return redirect('admin_community')


@staff_required
def manage_reports(request):
    reports = Report.objects.select_related('reporter').order_by('-created_at')
    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_note', '')
        report = get_object_or_404(Report, pk=report_id)
        report.status = new_status
        report.admin_note = admin_note
        report.save()
        messages.success(request, f"Report #{report_id} updated.")
        return redirect('admin_reports')
    return render(request, 'dashboard/reports.html', {'reports': reports})