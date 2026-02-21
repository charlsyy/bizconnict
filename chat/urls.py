from django.urls import path
from . import views

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('<int:conv_id>/', views.chat_room, name='chat_room'),
    path('start/<int:seller_id>/', views.start_chat, name='start_chat'),
    path('<int:conv_id>/fetch/', views.fetch_messages, name='fetch_messages'),
    path('<int:conv_id>/send/', views.send_message, name='send_message'),
]