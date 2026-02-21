from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from accounts.decorators import login_required_custom
from .models import Question, Answer


@login_required_custom
def community_list(request):
    query = request.GET.get('q', '').strip()
    questions = Question.objects.filter(is_active=True).select_related('author')

    if query:
        questions = questions.filter(title__icontains=query) | \
                    questions.filter(body__icontains=query)

    questions = questions.order_by('-created_at')

    return render(request, 'community/community.html', {
        'questions': questions,
        'query': query,
    })


@login_required_custom
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk, is_active=True)
    answers = question.answers.filter(is_active=True).select_related('author', 'author__profile')

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, "Answer cannot be empty.")
        else:
            Answer.objects.create(question=question, author=request.user, body=body)
            messages.success(request, "Answer posted.")
        return redirect('question_detail', pk=pk)

    return render(request, 'community/question.html', {
        'question': question,
        'answers': answers,
    })


@login_required_custom
@require_POST
def create_question(request):
    title = request.POST.get('title', '').strip()
    body = request.POST.get('body', '').strip()
    if not title or not body:
        messages.error(request, "Title and body required.")
        return redirect('community_list')
    q = Question(author=request.user, title=title, body=body)
    if request.FILES.get('image'):
        q.image = request.FILES['image']
    q.save()
    messages.success(request, "Question posted.")
    return redirect('question_detail', pk=q.pk)


@login_required_custom
@require_POST
def mark_solved(request, pk):
    question = get_object_or_404(Question, pk=pk, author=request.user)
    question.is_solved = True
    question.save()
    return redirect('question_detail', pk=pk)


@login_required_custom
@require_POST
def accept_answer(request, pk, answer_id):
    question = get_object_or_404(Question, pk=pk, author=request.user)
    answer = get_object_or_404(Answer, pk=answer_id, question=question)
    question.answers.update(is_accepted=False)
    answer.is_accepted = True
    answer.save()
    question.is_solved = True
    question.save()
    messages.success(request, "Answer accepted.")
    return redirect('question_detail', pk=pk)