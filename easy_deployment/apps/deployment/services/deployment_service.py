import os
import logging
import uuid
from datetime import datetime
from django.conf import settings
from .github_service import GitHubService
from .container_service import ContainerService
from easy_deployment.deployment.models import Project, Deployment, Environment

logger = logging.getLogger(__name__)

class DeploymentService:
    def __init__(self, github_account=None):
        self.github_account = github_account
        if github_account:
            self.github_service = GitHubService(github_account.access_token)
        self.container_service = ContainerService()
    
    def create_deployment(self, project, branch=None, environment_name='production'):
        """Create a new deployment for a project"""
        if not branch:
            branch = project.branch
        
        # Get GitHub repository details
        repo_parts = project.repository_url.split('/')
        owner, repo = repo_parts[-2], repo_parts[-1].replace('.git', '')
        
        # Get latest commit
        commit_data = self.github_service.get_latest_commit(owner, repo, branch)
        commit_hash = commit_data['sha']
        
        # Get or create environment
        environment, _ = Environment.objects.get_or_create(
            project=project,
            name=environment_name
        )
        
        # Create deployment record
        deployment = Deployment.objects.create(
            project=project,
            commit_hash=commit_hash,
            status='pending',
            environment=environment
        )
        
        return deployment
    
    def start_deployment_process(self, deployment):
        """Start the deployment process"""
        try:
            deployment.status = 'building'
            deployment.save(update_fields=['status'])
            
            # Clone repository
            deployment.logs += f"[{datetime.now().isoformat()}] Cloning repository...\n"
            deployment.save(update_fields=['logs'])
            
            repo_dir = self.github_service.clone_repository(
                deployment.project.repository_url,
                deployment.project.branch or 'main'  # Use 'main' as the default branch
            )
            
            # Detect framework if not specified
            if deployment.project.framework_type == 'auto':
                framework = self.github_service.detect_framework(repo_dir)
                deployment.project.framework_type = framework
                deployment.project.save(update_fields=['framework_type'])
            
            # Apply environment variables
            if deployment.environment and deployment.environment.variables:
                env_file_path = os.path.join(repo_dir, '.env')
                with open(env_file_path, 'w') as env_file:
                    for key, value in deployment.environment.variables.items():
                        env_file.write(f"{key}={value}\n")
            
            # Build and deploy container
            deployment.logs += f"[{datetime.now().isoformat()}] Building container...\n"
            deployment.save(update_fields=['logs'])
            
            container_id, container_logs = self.container_service.build_and_run(
                repo_dir=repo_dir,
                project_name=deployment.project.name,
                deployment_id=deployment.id,
                framework=deployment.project.framework_type,
                environment=deployment.environment.variables if deployment.environment else {}
            )
            
            deployment.logs += container_logs
            deployment.container_id = container_id
            
            # Generate a deployment URL
            deployment_domain = settings.DEPLOYMENT_DOMAIN
            deployment_url = f"https://{deployment.project.name.lower()}-{deployment.id}.{deployment_domain}"
            
            # Update deployment record
            deployment.status = 'deployed'
            deployment.deployment_url = deployment_url
            deployment.completed_at = datetime.now()
            deployment.save()
            
            # Update project's last deployed timestamp
            deployment.project.last_deployed = datetime.now()
            deployment.project.save(update_fields=['last_deployed'])
            
            return deployment
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            deployment.logs += f"[{datetime.now().isoformat()}] ERROR: {str(e)}\n"
            deployment.status = 'failed'
            deployment.completed_at = datetime.now()
            deployment.save()
            return deployment