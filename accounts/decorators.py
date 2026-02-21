from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def seller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            profile = request.user.profile
        except Exception:
            messages.error(request, "Profile not found.")
            return redirect('landing')
        if profile.role != 'seller':
            messages.error(request, "Seller account required.")
            return redirect('product_list')
        return view_func(request, *args, **kwargs)
    return wrapper

def buyer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            profile = request.user.profile
        except Exception:
            messages.error(request, "Profile not found.")
            return redirect('landing')
        if profile.role != 'buyer':
            messages.error(request, "Buyer account required.")
            return redirect('seller_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "Staff access required.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper