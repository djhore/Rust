"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

"""Now we need to connect the maintenance app's URLs to the main Rust project.
Step 4 — Connect the app URLs to Rust
What did we just do?
This line:
path('', include('maintenance.urls')),
tells Django:
"Use the URLs defined in the maintenance app for the main Rust website."
Because our maintenance/urls.py contains:
path('register/', views.register, name='register'),
the final address will be:
http://127.0.0.1:8000/register/
So the flow is now:
Browser
   ↓
Rust (config/urls.py)
   ↓
maintenance/urls.py
   ↓
register() in views.py
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('maintenance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)