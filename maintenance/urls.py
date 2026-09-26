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
]