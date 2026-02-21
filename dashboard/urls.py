from django.urls import path
from . import views

urlpatterns = [
    path('', views.overview, name='admin_dashboard'),
    path('users/', views.manage_users, name='admin_users'),
    path('users/<int:user_id>/toggle/', views.toggle_user_active, name='admin_toggle_user'),
    path('shop/', views.manage_shop, name='admin_shop'),
    path('shop/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('orders/', views.manage_orders, name='admin_orders'),
    path('orders/<int:order_id>/update/', views.admin_update_order, name='admin_update_order'),
    path('community/', views.manage_community, name='admin_community'),
    path('community/<int:pk>/delete/', views.admin_delete_question, name='admin_delete_question'),
    path('reports/', views.manage_reports, name='admin_reports'),
]