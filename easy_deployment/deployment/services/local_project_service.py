import os
import shutil
import tempfile
import zipfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import Project
from .github_service import GitHubService

class LocalProjectService:
    def __init__(self):
        self.github_service = GitHubService(None)  # For framework detection
    
    def handle_upload(self, file, user):
        """Handle uploaded project files"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Save zip file
            path = default_storage.save(
                f'tmp/projects/{file.name}',
                ContentFile(file.read())
            )
            full_path = default_storage.path(path)
            
            # Extract zip file
            with zipfile.ZipFile(full_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Clean up zip file
            default_storage.delete(path)
            
            # Detect framework
            framework = self.github_service.detect_framework(temp_dir)
            
            return {
                'framework': framework,
                'temp_dir': temp_dir,
                'valid': True
            }
            
        except Exception as e:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise Exception(f"Error processing upload: {str(e)}")
    
    def create_project(self, temp_dir, name, user, framework_type='auto'):
        """Create a project from uploaded files"""
        try:
            # Create project record
            project = Project.objects.create(
                name=name,
                owner=user,
                repository_url='local://' + name,  # Special URL for local projects
                framework_type=framework_type
            )
            
            # Store files in a permanent location
            project_dir = os.path.join('projects', str(project.id))
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            
            # Copy files from temp directory
            shutil.copytree(temp_dir, project_dir, dirs_exist_ok=True)
            
            return project
            
        finally:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
