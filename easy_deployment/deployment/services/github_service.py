import os
import requests
import tempfile
import subprocess
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self, access_token):
        self.access_token = access_token
        self.api_base_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_user_repos(self):
        """Get repositories for the authenticated user"""
        response = requests.get(f"{self.api_base_url}/user/repos", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_repository_details(self, owner, repo):
        """Get details for a specific repository"""
        response = requests.get(f"{self.api_base_url}/repos/{owner}/{repo}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_branches(self, owner, repo):
        """Get branches for a repository"""
        response = requests.get(f"{self.api_base_url}/repos/{owner}/{repo}/branches", 
                               headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_latest_commit(self, owner, repo, branch):
        """Get the latest commit for a branch"""
        response = requests.get(f"{self.api_base_url}/repos/{owner}/{repo}/commits/{branch}", 
                               headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def clone_repository(self, repo_url, branch='main'):
        """Clone a repository to a temporary directory"""
        try:
            temp_dir = tempfile.mkdtemp()
            auth_url = repo_url.replace('https://', f'https://oauth2:{self.access_token}@')
            
            result = subprocess.run(
                ['git', 'clone', '--single-branch', '--branch', branch, auth_url, temp_dir],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Cloned repository {repo_url} to {temp_dir}")
            return temp_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            raise Exception(f"Failed to clone repository: {e.stderr}")
    
    def detect_framework(self, repo_dir):
        """Detect the framework used in the repository"""
        files = os.listdir(repo_dir)
        
        # Check for LAMP stack
        if 'composer.json' in files or any(f.endswith('.php') for f in files):
            if os.path.exists(os.path.join(repo_dir, 'public', '.htaccess')):
                return 'lamp'
            return 'php'
        
        package_json_path = os.path.join(repo_dir, 'package.json')
        
        if 'package.json' in files:
            with open(package_json_path, 'r') as f:
                package_data = f.read()
                dependencies = json.loads(package_data).get('dependencies', {})
                
                # Check for MERN stack
                if ('express' in dependencies and 
                    'mongoose' in dependencies and 
                    'react' in dependencies):
                    return 'mern'
                
                # Check for Node.js frameworks
                if 'next' in package_data:
                    return 'node-next'
                elif 'react' in package_data:
                    return 'node-react'
                elif 'vue' in package_data:
                    return 'node-vue'
                else:
                    return 'node'
        
        # Check for Python frameworks
        if 'requirements.txt' in files or 'Pipfile' in files:
            if 'manage.py' in files:
                return 'python-django'
            elif 'app.py' in files or any(f.endswith('.py') for f in files):
                return 'python-flask'
        
        # Check for Java frameworks
        if 'pom.xml' in files:
            return 'java-maven'
        elif 'build.gradle' in files:
            return 'java-gradle'
        
        # Default to static if there's index.html
        if 'index.html' in files:
            return 'static'
        
        return 'unknown'