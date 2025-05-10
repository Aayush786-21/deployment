from django.contrib import admin
from .models import GithubAccount, Project, Deployment, Environment

@admin.register(GithubAccount)
class GithubAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'github_username')
    search_fields = ('user__username', 'github_username')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'repository_url', 'owner', 'created_at', 'last_deployed')
    list_filter = ('created_at', 'last_deployed')
    search_fields = ('name', 'repository_url', 'owner__username')
    date_hierarchy = 'created_at'

@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('project', 'commit_hash', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('project__name', 'commit_hash')
    date_hierarchy = 'created_at'

@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('project', 'name')
    list_filter = ('project',)
    search_fields = ('project__name', 'name')