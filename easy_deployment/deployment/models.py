from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class GithubAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='github_account')
    access_token = models.CharField(max_length=255)
    github_username = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.user.username}'s GitHub Account ({self.github_username})"

class Project(models.Model):
    name = models.CharField(max_length=255)
    repository_url = models.URLField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    last_deployed = models.DateTimeField(null=True, blank=True)
    framework_type = models.CharField(max_length=50, choices=[
        ('python', 'Python'),
        ('node', 'Node.js'),
        ('java', 'Java'),
        ('static', 'Static HTML'),
        ('other', 'Other')
    ], default='node')
    branch = models.CharField(max_length=100, default='main')
    
    def __str__(self):
        return self.name
    
    def update_last_deployed(self):
        self.last_deployed = timezone.now()
        self.save(update_fields=['last_deployed'])

class Environment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments')
    name = models.CharField(max_length=50)  # production, development, staging, etc.
    variables = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ('project', 'name')
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"

class Deployment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('building', 'Building'),
        ('deploying', 'Deploying'),
        ('deployed', 'Deployed'),
        ('failed', 'Failed')
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deployments')
    commit_hash = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    deployment_url = models.URLField(null=True, blank=True)
    logs = models.TextField(blank=True)
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, related_name='deployments')
    container_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.project.name} - {self.commit_hash[:7]} ({self.status})"
    
    def mark_as_deployed(self, url):
        self.status = 'deployed'
        self.deployment_url = url
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'deployment_url', 'completed_at'])
        self.project.update_last_deployed()
    
    def mark_as_failed(self, error_logs=None):
        self.status = 'failed'
        self.completed_at = timezone.now()
        if error_logs:
            self.logs += f"\n{error_logs}"
        self.save(update_fields=['status', 'completed_at', 'logs'])