from django.urls import path, include
from rest_framework.routers import DefaultRouter
from deployment import views

router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'deployments', views.DeploymentViewSet, basename='deployment')
router.register(r'environments', views.EnvironmentViewSet, basename='environment')

urlpatterns = [
    # Web views
    path('', views.dashboard, name='dashboard'),
    path('github/login/', views.github_login, name='github_login'),
    path('github/callback/', views.github_callback, name='github_callback'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    
    # API endpoints
    path('api/', include(router.urls)),
]