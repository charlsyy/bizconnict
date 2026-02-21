import json

from django.contrib.auth.models import User
from django.db import models as db_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import login_required_custom
from notifications.utils import create_notification
from .models import Conversation, Message


@login_required_custom
def conversation_list(request):
    conversations = Conversation.objects.filter(
        db_models.Q(buyer=request.user) | db_models.Q(seller=request.user)
    ).order_by('-updated_at')

    conv_data = []
    for conv in conversations:
        other = conv.seller if request.user == conv.buyer else conv.buyer
        unread = conv.messages.filter(is_read=False).exclude(sender=request.user).count()
        conv_data.append({
            'conv': conv,
            'other': other,
            'unread': unread,
            'last_msg': conv.messages.last(),
        })

    return render(request, 'chat/conversation_list.html', {'conv_data': conv_data})


@login_required_custom
def chat_room(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    user = request.user
    if user not in (conv.buyer, conv.seller):
        return redirect('conversation_list')

    conv.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
    other = conv.seller if user == conv.buyer else conv.buyer
    messages_qs = conv.messages.all()

    return render(request, 'chat/chat_room.html', {
        'conv': conv,
        'other': other,
        'messages': messages_qs,
    })


@login_required_custom
def start_chat(request, seller_id):
    buyer = request.user
    seller = get_object_or_404(User, pk=seller_id)

    try:
        if buyer.profile.role != 'buyer':
            from django.contrib import messages as dj_messages
            dj_messages.error(request, "Only buyers can start chats with sellers.")
            return redirect('product_list')
    except Exception:
        pass

    conv, _ = Conversation.objects.get_or_create(buyer=buyer, seller=seller)
    return redirect('chat_room', conv_id=conv.id)


@login_required_custom
def fetch_messages(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    if request.user not in (conv.buyer, conv.seller):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    since = request.GET.get('since', 0)
    msgs = conv.messages.filter(id__gt=since).select_related('sender').order_by('created_at')

    # Mark incoming messages as read
    msgs.exclude(sender=request.user).update(is_read=True)

    data = []
    for m in msgs:
        data.append({
            'id': m.id,
            'body': m.body,
            'is_mine': m.sender == request.user,
            'sender': m.sender.username,
            'time': m.created_at.strftime('%H:%M'),
            'is_read': m.is_read,
        })

    return JsonResponse({'messages': data})


@login_required_custom
@require_POST
def send_message(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    if request.user not in (conv.buyer, conv.seller):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        data = json.loads(request.body)
        body = (data.get('body') or '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not body:
        return JsonResponse({'error': 'Empty message'}, status=400)

    m = Message.objects.create(
        conversation=conv,
        sender=request.user,
        body=body,
        is_read=False,
    )

    # bump updated_at for ordering
    conv.save()

    other = conv.seller if request.user == conv.buyer else conv.buyer
    create_notification(
        recipient=other,
        notif_type='message',
        message=f"{request.user.username}: {body[:80]}",
        link=f"/chat/{conv.id}/",
    )

    return JsonResponse({
        'id': m.id,
        'body': m.body,
        'is_mine': True,
        'sender': request.user.username,
        'time': m.created_at.strftime('%H:%M'),
        'is_read': False,
    })