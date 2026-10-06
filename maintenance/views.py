from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from .forms import (
    TenantRegistrationForm,
    MaintenanceRequestForm,
    ProfileUpdateForm,
)
from .models import UserProfile, MaintenanceRequest, RoleVerificationCode
from .decorators import manager_required,tenant_required
from django.contrib.auth.forms import AuthenticationForm

def register(request):

    if request.method == 'POST':

        form = TenantRegistrationForm(request.POST)

        if form.is_valid():

            user = form.save()

            verification_code = RoleVerificationCode.objects.get(
                code=form.cleaned_data['role_code']
            )

            UserProfile.objects.create(
                user=user,
                role=verification_code.role,
                phone_number=form.cleaned_data['phone_number'],
                apartment_number=form.cleaned_data['apartment_number'],
            )

            verification_code.is_used = True
            verification_code.used_by = user
            verification_code.save()

            login(request, user)

            messages.success(
                request,
                'Your Rust account has been created successfully.'
            )

            return redirect('dashboard')

    else:

        form = TenantRegistrationForm()

    return render(
        request,
        'maintenance/register.html',
        {'form': form}
    )

def user_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')
        role_code = request.POST.get('role_code')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            try:
                profile = UserProfile.objects.get(user=user)
            except UserProfile.DoesNotExist:
                messages.error(
                    request,
                    'Your account does not have a Rust role assigned.'
                )
                return render(
                    request,
                    'maintenance/login.html'
                )

            try:
                verification_code = RoleVerificationCode.objects.get(
                    code=role_code
                )
            except RoleVerificationCode.DoesNotExist:
                messages.error(
                    request,
                    'Invalid role verification code.'
                )
                return render(
                    request,
                    'maintenance/login.html'
                )

            if verification_code.role != profile.role:
                messages.error(
                    request,
                    'The verification code does not match your account role.'
                )
                return render(
                    request,
                    'maintenance/login.html'
                )

            login(request, user)
            return redirect('dashboard')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(
        request,
        'maintenance/login.html'
    )

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

    if request.method == 'POST':

        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):

            messages.error(
                request,
                'Your current password is incorrect.'
            )

            return redirect('change_password')

        if new_password != confirm_password:

            messages.error(
                request,
                'The new passwords do not match.'
            )

            return redirect('change_password')

        if len(new_password) < 8:

            messages.error(
                request,
                'Your new password must be at least 8 characters long.'
            )

            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(
            request,
            'Your password has been changed successfully.'
        )

        return redirect('profile')

    return render(
        request,
        'maintenance/change_password.html'
    )

@login_required
def delete_account(request):

    if request.method == 'POST':

        password = request.POST.get('password', '')

        if not request.user.check_password(password):
            messages.error(
                request,
                'Incorrect password. Your account was not deactivated.'
            )
        else:
            user = request.user

            user.is_active = False
            user.save(update_fields=['is_active'])

            auth_logout(request)

            messages.success(
                request,
                'Your Rust account has been deactivated.'
            )

            return redirect('login')

    return render(
        request,
        'maintenance/delete_account.html'
    )

@login_required
def dashboard(request):

    profile = UserProfile.objects.get(user=request.user)

    if profile.role == 'tenant':

        return render(
            request,
            'maintenance/dashboard.html',
            {'profile': profile}
        )

    elif profile.role == 'manager':

        return render(
            request,
            'maintenance/manager_dashboard.html',
            {'profile': profile}
        )

    elif profile.role == 'technician':

        return render(
            request,
            'maintenance/technician_dashboard.html',
            {'profile': profile}
        )



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

def user_logout(request):
    auth_logout(request)
    return redirect('login')