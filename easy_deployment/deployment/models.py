from django.db import models
from django.contrib.auth.models import User

class GithubAccount(models.Models):
    user = = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255)
    github_username = models.CharField(max_length=100)

class Project(models.Model):
    name = models.CharField(max_length=255)
    repository_url = models.URLField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_deployed = models.DateTimeField(null=True, blank=True)
    
class Deployment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    commit_hash = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('building', 'Building'),
        ('deployed', 'Deployed'),
        ('failed', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    deployment_url = models.URLField(null=True, blank=True)
    logs = models.TextField(blank=True)