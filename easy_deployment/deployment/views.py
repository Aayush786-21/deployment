import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import GithubAccount, Project, Deployment, Environment
from .serializers import ProjectSerializer, DeploymentSerializer, EnvironmentVariableSerializer
from .services.github_service import GitHubService
from .services.deployment_service import DeploymentService

@login_required
def dashboard(request):
    """Main dashboard view"""
    projects = Project.objects.filter(owner=request.user).order_by('-last_deployed')
    
    # Check if user has GitHub account connected
    try:
        github_account = GithubAccount.objects.get(user=request.user)
        has_github = True
    except GithubAccount.DoesNotExist:
        has_github = False
    
    return render(request, 'dashboard.html', {
        'projects': projects,
        'has_github': has_github
    })

@login_required
def github_login(request):
    """Redirect to GitHub OAuth flow"""
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo"
    return redirect(github_auth_url)

@login_required
def github_callback(request):
    """Handle GitHub OAuth callback"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f"GitHub authentication failed: {error}")
        return redirect('dashboard')
    
    if not code:
        messages.error(request, "No authorization code received from GitHub")
        return redirect('dashboard')
    
    try:
        # Exchange code for access token
        import requests
        response = requests.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code
            },
            headers={'Accept': 'application/json'}
        )
        
        data = response.json()
        access_token = data.get('access_token')
        
        if not access_token:
            messages.error(request, "Failed to get access token from GitHub")
            return redirect('dashboard')
        
        # Get user info
        user_response = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'token {access_token}'}
        )
        github_user = user_response.json()
        
        # Store GitHub account info
        github_account, created = GithubAccount.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': access_token,
                'github_username': github_user['login']
            }
        )
        
        messages.success(request, f"Successfully connected to GitHub as {github_user['login']}")
        
    except Exception as e:
        messages.error(request, f"Error connecting to GitHub: {str(e)}")
    
    return redirect('dashboard')

@login_required
def project_detail(request, project_id):
    """Project detail view"""
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    deployments = project.deployments.order_by('-created_at')
    environments = project.environments.all()
    
    return render(request, 'project_detail.html', {
        'project': project,
        'deployments': deployments,
        'environments': environments
    })

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        project = self.get_object()
        
        try:
            # Get GitHub account
            github_account = GithubAccount.objects.get(user=request.user)
            
            # Create deployment service
            deployment_service = DeploymentService(github_account)
            
            # Get environment name from request
            environment_name = request.data.get('environment', 'production')
            
            # Create deployment
            deployment = deployment_service.create_deployment(project, environment_name=environment_name)
            
            # Start deployment process (this could be moved to a Celery task)
            deployment = deployment_service.start_deployment_process(deployment)
            
            return Response(DeploymentSerializer(deployment).data)
            
        except GithubAccount.DoesNotExist:
            return Response(
                {"error": "GitHub account not connected"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def github_repos(self, request, pk=None):
        try:
            github_account = GithubAccount.objects.get(user=request.user)
            github_service = GitHubService(github_account.access_token)
            repos = github_service.get_user_repos()
            return Response(repos)
        except GithubAccount.DoesNotExist:
            return Response(
                {"error": "GitHub account not connected"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeploymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeploymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Deployment.objects.filter(project__owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        deployment = self.get_object()
        
        # If container is running, get live logs
        if deployment.container_id:
            try:
                container_service = ContainerService()
                container_logs = container_service.get_container_logs(deployment.container_id)
                deployment.logs += f"\n\n--- Live Container Logs ---\n{container_logs}"
            except Exception as e:
                deployment.logs += f"\n\nError getting live logs: {str(e)}"
        
        return Response({"logs": deployment.logs})

class EnvironmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnvironmentVariableSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Environment.objects.filter(project__owner=self.request.user)
    
    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        project = get_object_or_404(Project, id=project_id, owner=self.request.user)
        serializer.save(project=project)