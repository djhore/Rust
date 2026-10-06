from functools import wraps

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import UserProfile


def role_required(required_role):

    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):

            try:
                profile = UserProfile.objects.get(
                    user=request.user
                )
            except UserProfile.DoesNotExist:
                return render(
                    request,
                    'maintenance/access_denied.html'
                )

            if profile.role != required_role:
                return render(
                    request,
                    'maintenance/access_denied.html'
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def tenant_required(view_func):
    return role_required('tenant')(view_func)


def manager_required(view_func):
    return role_required('manager')(view_func)


def technician_required(view_func):
    return role_required('technician')(view_func)