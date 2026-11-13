from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import User


def home(request):
    return render(request, 'landing.html')


@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return _dashboard_redirect(request.user)
    return render(request, 'login.html')


def _dashboard_redirect(user):
    return redirect({
        User.ROLE_CUSTOMER: 'customer_app',
        User.ROLE_RIDER: 'rider_app',
        User.ROLE_VENDOR: 'vendor_app',
    }.get(user.role, 'login'))


def logout_view(request):
    logout(request)
    return redirect('login')


def _role_required(request, role):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role != role:
        return _dashboard_redirect(request.user)
    return None


@ensure_csrf_cookie
def customer_app(request):
    response = _role_required(request, User.ROLE_CUSTOMER)
    if response:
        return response
    return render(request, 'customer/app.html')


@ensure_csrf_cookie
def rider_app(request):
    response = _role_required(request, User.ROLE_RIDER)
    if response:
        return response
    return render(request, 'rider/app.html')


@ensure_csrf_cookie
def vendor_app(request):
    response = _role_required(request, User.ROLE_VENDOR)
    if response:
        return response
    return render(request, 'vendor/dashboard.html')
