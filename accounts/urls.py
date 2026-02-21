from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('accounts/register/', views.register_page, name='register'),
    path('accounts/login/', views.login_page, name='login'),
    path('accounts/firebase-auth/', views.firebase_auth, name='firebase_auth'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/login/fallback/', views.fallback_login, name='fallback_login'),
    path("standard-auth/", views.standard_auth, name="standard_auth"),
]