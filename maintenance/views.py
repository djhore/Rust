from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_POST
from django.db import transaction
import mimetypes
from django.http import FileResponse, Http404
from .forms import (
    TenantRegistrationForm,
    MaintenanceRequestForm,
    ProfileUpdateForm,
    AssignTechnicianForm,
    ChangePriorityForm,
)
from .models import UserProfile, MaintenanceRequest, RoleVerificationCode
from .decorators import (
    manager_required,
    tenant_required,
    technician_required,
)
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Count
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme


def register(request):
    if request.method == "POST":
        form = TenantRegistrationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Lock the code row so simultaneous registrations
                    # cannot successfully claim the same code.
                    verification_code = (
                        RoleVerificationCode.objects
                        .select_for_update()
                        .get(code=form.cleaned_data["role_code"])
                    )

                    if verification_code.is_used:
                        form.add_error(
                            "role_code",
                            "This verification code is invalid or no longer available.",
                        )
                        raise ValueError("Verification code unavailable.")

                    # Create the user and profile in the same transaction.
                    user = form.save(commit=False)
                    user.save()

                    profile = UserProfile(
                        user=user,
                        role=verification_code.role,
                        phone_number=form.cleaned_data["phone_number"],
                        apartment_number=form.cleaned_data["apartment_number"],
                    )

                    profile.full_clean()
                    profile.save()

                    verification_code.is_used = True
                    verification_code.used_by = user
                    verification_code.save(
                        update_fields=["is_used", "used_by"]
                    )

            except RoleVerificationCode.DoesNotExist:
                form.add_error(
                    "role_code",
                    "This verification code is invalid or no longer available.",
                )

            except ValueError:
                # The form now contains the code error.
                pass

            else:
                login(request, user)

                messages.success(
                    request,
                    "Your Rust account has been created successfully.",
                )

                return redirect("dashboard")

    else:
        form = TenantRegistrationForm()

    return render(
        request,
        "maintenance/register.html",
        {"form": form},
    )

def user_login(request):
    if request.method != "POST":
        return render(request, "maintenance/login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    role_code = request.POST.get("role_code", "").strip()

    # Use the username and client IP to limit repeated attempts.
    # Do not trust forwarded IP headers unless your proxy is configured.
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    attempt_key = f"rust-login:{client_ip}:{username.lower()}"
    attempts = cache.get(attempt_key, 0)

    if attempts >= 5:
        messages.error(
            request,
            "Too many failed login attempts. Please wait five minutes "
            "before trying again.",
        )
        return render(request, "maintenance/login.html")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        attempts += 1
        cache.set(attempt_key, attempts, timeout=300)

        messages.error(
            request,
            "Invalid login details or role verification code.",
        )
        return render(request, "maintenance/login.html")

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        cache.delete(attempt_key)
        messages.error(
            request,
            "This account is not configured for Rust access.",
        )
        return render(request, "maintenance/login.html")

    

    verification_code = RoleVerificationCode.objects.filter(
        code=role_code,
        is_used=True,
        used_by=user,
        role=profile.role,
    ).first()

    if verification_code is None:
        messages.error(
            request,
             "Invalid login details or role verification code.",
        )
        return render(
            request,
            "maintenance/login.html",
        )


    # Clear the failure counter after successful authentication.
    cache.delete(attempt_key)

    login(request, user)

    # Honour ?next= only when it points to a safe local destination.
    next_url = request.POST.get("next") or request.GET.get("next")

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("dashboard")


@login_required
def profile(request):

    user_profile = UserProfile.objects.get(user=request.user)

    return render(
        request,
        'maintenance/profile.html',
        {
            'profile': user_profile,
        }
    )

@login_required
def edit_profile(request):

    user_profile = UserProfile.objects.get(
        user=request.user
    )

    if request.method == 'POST':

        form = ProfileUpdateForm(
            request.POST,
            instance=user_profile
        )

        if form.is_valid():

            user = request.user

            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']

            user.save()

            form.save()

            messages.success(
                request,
                'Your profile has been updated successfully.'
            )

            return redirect('profile')

    else:

        form = ProfileUpdateForm(
            instance=user_profile
        )

    return render(
        request,
        'maintenance/edit_profile.html',
        {
            'form': form,
            'profile': user_profile,
        }
    )

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(
            user=request.user,
            data=request.POST,
        )

        for field in form.fields.values():
            field.widget.attrs["class"] = "form-control"

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            messages.success(
                request,
                "Your password has been changed successfully.",
            )

            return redirect("profile")

    else:
        form = PasswordChangeForm(user=request.user)

    return render(
        request,
        "maintenance/change_password.html",
        {"form": form},
    )



@login_required
def dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(
            request,
            "This account is not configured for Rust access. Please contact the administrator.",
        )
        auth_logout(request)
        return redirect("login")

    if profile.role == "tenant":
        return render(
            request,
            "maintenance/dashboard.html",
            {"profile": profile},
        )

    if profile.role == "manager":
        return render(
            request,
            "maintenance/manager_dashboard.html",
            {"profile": profile},
        )

    if profile.role == "technician":
        return render(
            request,
            "maintenance/technician_dashboard.html",
            {"profile": profile},
        )

    messages.error(
        request,
        "This account has an invalid Rust role. Please contact the administrator.",
    )
    auth_logout(request)
    return redirect("login")

@manager_required
def manager_requests(request):

    requests = MaintenanceRequest.objects.all().order_by(
        '-date_submitted'
    )

    return render(
        request,
        'maintenance/manager_requests.html',
        {
            'requests': requests,
        }
    )
@manager_required
def manager_request_detail(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id
    )

    return render(
        request,
        'maintenance/manager_request_detail.html',
        {'maintenance_request': maintenance_request}
    )

@login_required
def maintenance_request_image(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id,
    )

    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        raise Http404

    if profile.role == "tenant":
        if maintenance_request.tenant_id != request.user.id:
            raise Http404

    elif profile.role == "technician":
        if maintenance_request.assigned_technician_id != request.user.id:
            raise Http404

    elif profile.role != "manager":
        raise Http404

    if not maintenance_request.image:
        raise Http404

    content_type, _ = mimetypes.guess_type(
        maintenance_request.image.name
    )

    return FileResponse(
        maintenance_request.image.open("rb"),
        content_type=content_type or "application/octet-stream",
    )
@manager_required
def assign_technician(request, request_id):
    if request.method == "POST":
        with transaction.atomic():
            maintenance_request = get_object_or_404(
                MaintenanceRequest.objects.select_for_update(),
                id=request_id,
            )

            if maintenance_request.status != "pending":
                messages.error(
                    request,
                    "Only pending maintenance requests can be assigned.",
                )
                return redirect(
                    "manager_request_detail",
                    request_id=request_id,
                )

            form = AssignTechnicianForm(request.POST)

            if form.is_valid():
                technician = form.cleaned_data["technician"]

                # Check the technician's role again on the server.
                if not UserProfile.objects.filter(
                    user=technician,
                    role="technician",
                ).exists() or not technician.is_active:
                    form.add_error(
                        "technician",
                        "Please select an active maintenance technician.",
                    )
                else:
                    maintenance_request.assigned_technician = technician
                    maintenance_request.status = "assigned"
                    maintenance_request.date_assigned = timezone.now()
                    maintenance_request.save(
                        update_fields=[
                            "assigned_technician",
                            "status",
                            "date_assigned",
                            "updated_at",
                        ]
                    )

                    messages.success(
                        request,
                        "The maintenance request has been assigned successfully.",
                    )
                    return redirect(
                        "manager_request_detail",
                        request_id=request_id,
                    )
    else:
        maintenance_request = get_object_or_404(
            MaintenanceRequest,
            id=request_id,
        )

        if maintenance_request.status != "pending":
            messages.error(
                request,
                "Only pending maintenance requests can be assigned.",
            )
            return redirect(
                "manager_request_detail",
                request_id=request_id,
            )

        form = AssignTechnicianForm()

    return render(
        request,
        "maintenance/assign_technician.html",
        {
            "form": form,
            "maintenance_request": maintenance_request,
        },
    )

@manager_required
def change_priority(request, request_id):
    if request.method == "POST":
        with transaction.atomic():
            maintenance_request = get_object_or_404(
                MaintenanceRequest.objects.select_for_update(),
                id=request_id,
            )

            # Do not allow priority changes for closed requests.
            if maintenance_request.status in {"cancelled", "completed"}:
                messages.error(
                    request,
                    "Priority cannot be changed for cancelled or completed requests.",
                )
                return redirect(
                    "manager_request_detail",
                    request_id=request_id,
                )

            form = ChangePriorityForm(
                request.POST,
                instance=maintenance_request,
            )

            if form.is_valid():
                form.save()

                messages.success(
                    request,
                    "The maintenance request priority has been updated successfully.",
                )

                return redirect(
                    "manager_request_detail",
                    request_id=request_id,
                )

    else:
        maintenance_request = get_object_or_404(
            MaintenanceRequest,
            id=request_id,
        )

        if maintenance_request.status in {"cancelled", "completed"}:
            messages.error(
                request,
                "Priority cannot be changed for cancelled or completed requests.",
            )
            return redirect(
                "manager_request_detail",
                request_id=request_id,
            )

        form = ChangePriorityForm(
            instance=maintenance_request,
        )

    return render(
        request,
        "maintenance/change_priority.html",
        {
            "form": form,
            "maintenance_request": maintenance_request,
        },
    )

@manager_required
@require_POST
def cancel_maintenance_request(request, request_id):
    with transaction.atomic():
        maintenance_request = get_object_or_404(
            MaintenanceRequest.objects.select_for_update(),
            id=request_id,
        )

        if maintenance_request.status in ("completed", "cancelled"):
            messages.error(
                request,
                "Completed or already cancelled requests cannot be cancelled.",
            )
        else:
            maintenance_request.status = "cancelled"
            maintenance_request.save(update_fields=["status", "updated_at"])

            messages.success(
                request,
                "The maintenance request has been cancelled successfully.",
            )

    return redirect(
        "manager_request_detail",
        request_id=request_id,
    )


@manager_required
def manager_technicians(request):
    technicians = User.objects.filter(
        userprofile__role='technician',
        is_active=True
    ).order_by('username')

    return render(
        request,
        'maintenance/manager_technicians.html',
        {'technicians': technicians}
    )

@manager_required
def manager_users(request):
    users = (
        UserProfile.objects
        .select_related("user")
        .all()
        .order_by("role", "user__username")
    )

    return render(
        request,
        "maintenance/manager_users.html",
        {"users": users},
    )

@manager_required
def manager_reports(request):
    total_requests = MaintenanceRequest.objects.count()

    pending_requests = MaintenanceRequest.objects.filter(
        status='pending'
    ).count()

    assigned_requests = MaintenanceRequest.objects.filter(
        status='assigned'
    ).count()

    in_progress_requests = MaintenanceRequest.objects.filter(
        status='in_progress'
    ).count()

    completed_requests = MaintenanceRequest.objects.filter(
        status='completed'
    ).count()

    cancelled_requests = MaintenanceRequest.objects.filter(
    status='cancelled'
    ).count()

    category_data = (
        MaintenanceRequest.objects
        .values('category')
        .annotate(total=Count('id'))
        .order_by('category')
    )

    priority_data = (
        MaintenanceRequest.objects
        .values('priority')
        .annotate(total=Count('id'))
        .order_by('priority')
    )

    status_data = [
        {
            'status': 'Pending',
            'total': pending_requests
        },
        {
            'status': 'Assigned',
            'total': assigned_requests
        },
        {
            'status': 'In Progress',
            'total': in_progress_requests
        },
        {
            'status': 'Completed',
            'total': completed_requests
        },
        {
            'status': 'Cancelled',
            'total': cancelled_requests
        },
    ]

    context = {
    'total_requests': total_requests,
    'pending_requests': pending_requests,
    'assigned_requests': assigned_requests,
    'in_progress_requests': in_progress_requests,
    'completed_requests': completed_requests,
    'cancelled_requests': cancelled_requests,
    'category_data': list(category_data),
    'priority_data': list(priority_data),

    'status_data': [
        {
            'status': 'Pending',
            'total': pending_requests
        },
        {
            'status': 'Assigned',
            'total': assigned_requests
        },
        {
            'status': 'In Progress',
            'total': in_progress_requests
        },
        {
            'status': 'Completed',
            'total': completed_requests
        },
        {
            'status': 'Cancelled',
            'total': cancelled_requests
        },
    ],
    }
    return render(
        request,
        'maintenance/manager_reports.html',
        context
    )


@technician_required
def technician_requests(request):
    requests = (
        MaintenanceRequest.objects
        .filter(
            assigned_technician=request.user,
            status__in=["assigned", "in_progress", "completed"],
        )
        .select_related('tenant', 'assigned_technician')
        .order_by('-date_submitted')
    )

    return render(
        request,
        'maintenance/technician_requests.html',
        {'requests': requests}
    )

@technician_required
def technician_progress(request):
    requests = (
        MaintenanceRequest.objects
        .filter(
            assigned_technician=request.user,
            status__in=['assigned', 'in_progress']
        )
        .select_related('tenant', 'assigned_technician')
        .order_by('-date_submitted')
    )

    return render(
        request,
        'maintenance/technician_progress.html',
        {'requests': requests}
    )

@technician_required
def technician_request_detail(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id,
        assigned_technician=request.user
    )

    return render(
        request,
        'maintenance/technician_request_detail.html',
        {'maintenance_request': maintenance_request}
    )



@technician_required
def technician_update_request(request, request_id):
    if request.method != "POST":
        return redirect(
            "technician_request_detail",
            request_id=request_id,
        )

    with transaction.atomic():
        maintenance_request = get_object_or_404(
            MaintenanceRequest.objects.select_for_update(),
            id=request_id,
            assigned_technician=request.user,
        )

        current_status = maintenance_request.status

        # Prevent updates to cancelled or completed requests.
        if current_status in {"cancelled", "completed"}:
            messages.error(
                request,
                "Cancelled or completed requests cannot be updated.",
            )
            return redirect(
                "technician_request_detail",
                request_id=request_id,
            )

        new_status = request.POST.get("status", "").strip()
        repair_notes = request.POST.get("repair_notes", "").strip()

        allowed_transitions = {
            "assigned": {"in_progress"},
            "in_progress": {"completed"},
        }

        # Allow saving a progress note without changing the status.
        if not new_status:
            if not repair_notes:
                messages.error(
                    request,
                    "Enter a progress note before saving.",
                )
                return redirect(
                    "technician_request_detail",
                    request_id=request_id,
                )

            if current_status not in {"assigned", "in_progress"}:
                messages.error(
                    request,
                    "Progress notes can only be added to active requests.",
                )
                return redirect(
                    "technician_request_detail",
                    request_id=request_id,
                )

            maintenance_request.repair_notes = repair_notes
            maintenance_request.save(
                update_fields=["repair_notes", "updated_at"]
            )

            messages.success(
                request,
                "Progress note saved successfully.",
            )
            return redirect(
                "technician_request_detail",
                request_id=request_id,
            )

        # Reject unsupported status transitions.
        allowed_statuses = allowed_transitions.get(current_status, set())

        if new_status not in allowed_statuses:
            messages.error(
                request,
                "This status change is not allowed.",
            )
            return redirect(
                "technician_request_detail",
                request_id=request_id,
            )

        if new_status == "completed":
            if not repair_notes:
                messages.error(
                    request,
                    "Please enter repair notes before completing the request.",
                )
                return redirect(
                    "technician_request_detail",
                    request_id=request_id,
                )

            maintenance_request.date_completed = timezone.now()

        maintenance_request.status = new_status
        maintenance_request.repair_notes = repair_notes
        maintenance_request.save()

    messages.success(
        request,
        "Maintenance request updated successfully.",
    )

    return redirect(
        "technician_request_detail",
        request_id=request_id,
    )


@tenant_required
def my_requests(request):
    requests = MaintenanceRequest.objects.filter(
        tenant=request.user
    ).order_by('-date_submitted')

    return render(
        request,
        'maintenance/my_requests.html',
        {'requests': requests}
    )

@tenant_required
def request_detail(request, request_id):
    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        id=request_id,
        tenant=request.user
    )

    return render(
        request,
        'maintenance/request_detail.html',
        {'maintenance_request': maintenance_request}
    )

@tenant_required
def maintenance_history(request):
    history = MaintenanceRequest.objects.filter(
        tenant=request.user,
        status='completed'
    ).order_by('-date_completed')

    return render(
        request,
        'maintenance/maintenance_history.html',
        {'history': history}
    )

@tenant_required
def submit_request(request):
    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES)

        if form.is_valid():
            maintenance_request = form.save(commit=False)

            maintenance_request.tenant = request.user
            maintenance_request.apartment_number = (
                UserProfile.objects.get(user=request.user).apartment_number
            )
            maintenance_request.status = 'pending'

            maintenance_request.save()

            messages.success(
                request,
                'Your maintenance request has been submitted successfully.'
            )

            return redirect('dashboard')

    else:
        form = MaintenanceRequestForm()

    return render(
        request,
        'maintenance/submit_request.html',
        {'form': form}
    )

@login_required
@require_POST
def user_logout(request):
    auth_logout(request)
    return redirect("login")