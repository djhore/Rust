from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('submit-request/', views.submit_request, name='submit_request'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path(
    'request/<int:request_id>/',
    views.request_detail,
    name='request_detail'
    ),
    path(
    'maintenance-history/',
    views.maintenance_history,
    name='maintenance_history'
    ),
    path(
    'manager/requests/',
    views.manager_requests,
    name='manager_requests'
    ),
    path(
    'manager/requests/<int:request_id>/',
    views.manager_request_detail,
    name='manager_request_detail'
    ),
    path(
    'manager/requests/<int:request_id>/assign/',
    views.assign_technician,
    name='assign_technician'
    ),
    path(
    'manager/requests/<int:request_id>/priority/',
    views.change_priority,
    name='change_priority'
    ),
    path(
    'manager/technicians/',
    views.manager_technicians,
    name='manager_technicians'
    ),
    path(
    'manager/users/',
    views.manager_users,
    name='manager_users'
    ),
    path(
    'manager/reports/',
    views.manager_reports,
    name='manager_reports'
    ),
    # path('technician/dashboard/', 
    # views.technician_dashboard, 
    # name='technician_dashboard'),
    path(
    'technician/requests/',
    views.technician_requests,
    name='technician_requests'
    ),
    path(
    'technician/requests/<int:request_id>/',
    views.technician_request_detail,
    name='technician_request_detail'
    ),
    path(
    'technician/requests/<int:request_id>/update/',
    views.technician_update_request,
    name='technician_update_request'
    ),
    path(
    'technician/progress/',
    views.technician_progress,
    name='technician_progress'
    ),
    path(
    'profile/',
    views.profile,
    name='profile'
    ),
    path(
    'profile/edit/',
    views.edit_profile,
    name='edit_profile'
    ),
    path(
    'profile/change-password/',
    views.change_password,
    name='change_password'
    ),
   
]