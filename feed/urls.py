from django.urls import path
from . import views

urlpatterns = [
    path('', views.feed, name='feed'),
    path('post/', views.create_post, name='create_post'),
    path('post/<int:pk>/react/', views.react_post, name='react_post'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
]