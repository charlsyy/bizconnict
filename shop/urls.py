from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_page, name='cart'),
    path('checkout/', views.checkout_page, name='checkout'),
    path('checkout/submit/', views.checkout_submit, name='checkout_submit'),
    path('orders/', views.my_orders, name='my_orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    # Payment
    path('order/<int:order_id>/payment/', views.payment_page, name='payment_page'),
    path('order/<int:order_id>/payment/cod/', views.payment_cod, name='payment_cod'),
    path('order/<int:order_id>/payment/manual/', views.payment_manual_submit, name='payment_manual'),
    path('order/<int:order_id>/payment/stripe/', views.payment_stripe_redirect, name='payment_stripe'),
    path('order/<int:order_id>/payment/stripe/success/', views.payment_stripe_success, name='payment_stripe_success'),
    path('order/<int:order_id>/payment/stripe/cancel/', views.payment_stripe_cancel, name='payment_stripe_cancel'),
    path('order/<int:order_id>/payment/confirm-proof/', views.confirm_payment_proof, name='confirm_payment_proof'),
    # Seller
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/orders/item/<int:item_id>/status/', views.update_item_status, name='update_item_status'),
    path('seller/products/new/', views.product_create, name='product_create'),
    path('seller/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('seller/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('seller/reports/', views.seller_reports, name='seller_reports'),
    path("auth/firebase/", views.firebase_auth, name="firebase_auth"),
    # path('order/<int:order_id>/payment/confirm-proof/', views.confirm_payment_proof, name='confirm_payment_proof'),
    # path('seller/products/new/', views.product_create, name='product_create'),
# path('seller/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
# path('seller/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
]