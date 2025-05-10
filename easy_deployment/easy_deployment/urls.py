from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('deployment.urls')),
    
    # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # API URLs
    path('api-auth/', include('rest_framework.urls')),
    
    # Default to dashboard if no URL matches
    path('', RedirectView.as_view(url='dashboard', permanent=False)),
]