from django.contrib import admin
from .models import Question, Answer

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_solved', 'created_at']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'author', 'is_accepted', 'created_at']