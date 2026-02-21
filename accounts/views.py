import json
import logging
import os

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages

from .models import Profile
from .decorators import login_required_custom

logger = logging.getLogger(__name__)


# ============================
# Firebase Admin Initialization
# ============================
def _init_firebase_admin():
    """
    Initializes Firebase Admin SDK exactly once.
    Reads credentials path from env var:
      FIREBASE_CREDENTIALS_PATH
    fallback:
      firebase-credentials.json in project root (where manage.py is)
    """
    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception as e:
        raise RuntimeError(f"firebase-admin not installed: {e}")

    if firebase_admin._apps:
        return  # already initialized

    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

    if not os.path.exists(cred_path):
        raise FileNotFoundError(
            f"Firebase credentials file not found: {cred_path}. "
            "Download the Service Account JSON from Firebase Console and save it here."
        )

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)


# ============================
# Redirect logic (ADMIN / SELLER / BUYER)
# ============================
def _pick_redirect(user):
    # ✅ Admin/staff/superuser -> your custom dashboard
    if user.is_superuser or user.is_staff:
        return "/dashboard/"

    # ✅ Seller -> seller dashboard
    try:
        if user.profile.role == "seller":
            return "/shop/seller/dashboard/"
    except Exception:
        pass

    # ✅ Buyer default
    return "/shop/products/"


def landing(request):
    if request.user.is_authenticated:
        return redirect(_pick_redirect(request.user))
    return render(request, "landing.html")


def register_page(request):
    role = request.GET.get("role", "buyer")
    if role not in ("buyer", "seller"):
        role = "buyer"
    return render(request, "accounts/register.html", {"role": role})


def login_page(request):
    if request.user.is_authenticated:
        return redirect(_pick_redirect(request.user))
    return render(request, "accounts/login.html")


# ==========================================================
# ✅ NEW: Standard Django login API (for admin username login)
# ==========================================================
@require_POST
def standard_auth(request):
    """
    Accepts JSON:
      { "username": "...", "password": "..." }

    Logs in Django user and returns redirect.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return JsonResponse({"success": False, "error": "Username and password required."}, status=400)

    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({"success": False, "error": "Invalid username or password."}, status=401)

    if not user.is_active:
        return JsonResponse({"success": False, "error": "Account is deactivated."}, status=403)

    login(request, user)
    return JsonResponse({"success": True, "redirect": _pick_redirect(user)})


# ============================
# Firebase session login (buyers/sellers)
# ============================
@csrf_exempt
@require_POST
def firebase_auth(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        id_token = data.get("id_token") or data.get("idToken")
        role = data.get("role", "buyer")
        display_name = data.get("display_name", "") or data.get("displayName", "")
        email = data.get("email", "")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if not id_token:
        return JsonResponse({"success": False, "error": "id_token required"}, status=400)

    if role not in ("buyer", "seller"):
        role = "buyer"

    # Verify Firebase token
    uid = None
    try:
        _init_firebase_admin()
        from firebase_admin import auth as fa

        decoded = fa.verify_id_token(id_token)
        uid = decoded.get("uid")
        email = decoded.get("email", email)
        display_name = decoded.get("name", display_name)
    except Exception as e:
        logger.warning(f"Firebase verify failed: {e}")
        return JsonResponse({"success": False, "error": f"Firebase verify failed: {str(e)}"}, status=401)

    if not uid:
        return JsonResponse({"success": False, "error": "Token missing uid"}, status=401)
    if not email:
        return JsonResponse({"success": False, "error": "Email required"}, status=400)

    # Find or create user + profile
    try:
        profile = Profile.objects.get(firebase_uid=uid)
        user = profile.user
    except Profile.DoesNotExist:
        base = email.split("@")[0]
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "first_name": display_name.split(" ")[0] if display_name else "",
                "last_name": " ".join(display_name.split(" ")[1:]) if display_name else "",
            },
        )

        if created:
            user.set_unusable_password()
            user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.firebase_uid = uid
        profile.role = role
        profile.save()

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # ✅ IMPORTANT: redirect rules include admin -> /dashboard/
    return JsonResponse({"success": True, "redirect": _pick_redirect(user)})


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required_custom
def profile_view(request):
    profile = request.user.profile
    if request.method == "POST":
        bio = request.POST.get("bio", "").strip()
        profile.bio = bio
        if request.FILES.get("avatar"):
            profile.avatar = request.FILES["avatar"]
        profile.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"profile": profile})


def fallback_login(request):
    # keep it if you still want it, but you don't need to use it anymore
    if request.user.is_authenticated:
        return redirect(_pick_redirect(request.user))

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return redirect(_pick_redirect(user))
            else:
                error = "Your account has been deactivated."
        else:
            error = "Invalid username or password."

    return render(request, "accounts/fallback_login.html", {"error": error})