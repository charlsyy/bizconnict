from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from accounts.decorators import login_required_custom
from .models import Notification


@login_required_custom
def notification_list(request):
    notifs = Notification.objects.filter(recipient=request.user)[:50]
    # Count separately to avoid slicing bug
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return render(request, 'notifications/notifications.html', {
        'notifs': notifs,
        'unread_count': unread_count,
    })


@login_required_custom
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required_custom
def unread_count(request):
    # Count computed independently — no slicing bug
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})