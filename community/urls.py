from django.urls import path
from . import views

urlpatterns = [
    path('', views.community_list, name='community_list'),
    path('ask/', views.create_question, name='create_question'),
    path('<int:pk>/', views.question_detail, name='question_detail'),
    path('<int:pk>/solved/', views.mark_solved, name='mark_solved'),
    path('<int:pk>/accept/<int:answer_id>/', views.accept_answer, name='accept_answer'),
]