from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_project, name='upload-project'),
    path('validate/', views.validate_project, name='validate-project'),
]
