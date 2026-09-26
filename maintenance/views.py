from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required

from .forms import TenantRegistrationForm, MaintenanceRequestForm
from .models import UserProfile, MaintenanceRequest


def register(request):
    if request.method == 'POST':
        form = TenantRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(
                user=user,
                role='tenant',
                phone_number=form.cleaned_data['phone_number'],
                apartment_number=form.cleaned_data['apartment_number'],
            )

            login(request, user)

            messages.success(
                request,
                'Your Rust account has been created successfully.'
            )

            return redirect('register')

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

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
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
def dashboard(request):
    profile = UserProfile.objects.get(user=request.user)

    return render(
        request,
        'maintenance/dashboard.html',
        {'profile': profile}
    )

@login_required
def my_requests(request):
    requests = MaintenanceRequest.objects.filter(
        tenant=request.user
    ).order_by('-date_submitted')

    return render(
        request,
        'maintenance/my_requests.html',
        {'requests': requests}
    )

@login_required
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

@login_required
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

@login_required
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