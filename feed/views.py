import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages

from accounts.decorators import login_required_custom
from .models import Post, PostReaction, REACTION_ICONS


@login_required_custom
def feed(request):
    posts = Post.objects.filter(is_active=True).select_related(
        'author', 'author__profile'
    ).order_by('-created_at')

    user_reactions = {}
    if request.user.is_authenticated:
        for r in PostReaction.objects.filter(user=request.user, post__in=posts):
            user_reactions[r.post_id] = r.reaction_type

    return render(request, 'feed/feed.html', {
        'posts': posts,
        'user_reactions': user_reactions,
        'reaction_icons': REACTION_ICONS,
        'reaction_types': list(REACTION_ICONS.keys()),
    })


@login_required_custom
@require_POST
def create_post(request):
    text = request.POST.get('text', '').strip()
    if not text:
        messages.error(request, "Post text required.")
        return redirect('feed')

    post = Post(author=request.user, text=text)

    if request.FILES.get('image'):
        post.image = request.FILES['image']
    if request.FILES.get('video'):
        post.video = request.FILES['video']

    post.save()
    messages.success(request, "Posted!")
    return redirect('feed')


@login_required_custom
@require_POST
def react_post(request, pk):
    post = get_object_or_404(Post, pk=pk, is_active=True)

    try:
        data = json.loads(request.body)
        rtype = (data.get('reaction_type') or '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    valid = [r[0] for r in PostReaction._meta.get_field('reaction_type').choices]
    if rtype not in valid:
        return JsonResponse({'error': 'Invalid reaction'}, status=400)

    existing = PostReaction.objects.filter(post=post, user=request.user).first()

    if existing:
        if existing.reaction_type == rtype:
            existing.delete()
            action = 'removed'
        else:
            existing.reaction_type = rtype
            existing.save(update_fields=['reaction_type'])
            action = 'updated'
    else:
        PostReaction.objects.create(post=post, user=request.user, reaction_type=rtype)
        action = 'added'

    counts = {r['reaction_type']: r['count'] for r in post.reaction_summary}
    return JsonResponse({'action': action, 'counts': counts})


@login_required_custom
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if post.author != request.user and not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    post.is_active = False
    post.save(update_fields=['is_active'])

    messages.success(request, "Post deleted.")
    return redirect('feed')