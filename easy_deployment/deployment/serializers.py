from rest_framework import serializers
from .models import GithubAccount, Project, Deployment, Environment

class GithubAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GithubAccount
        fields = ['id', 'github_username']
        read_only_fields = ['id', 'github_username']

class EnvironmentVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = ['id', 'name', 'variables']
        
    def validate_variables(self, value):
        """Ensure all environment variables are strings"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Environment variables must be a dictionary")
        
        for key, val in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError("Environment variable keys must be strings")
            if not isinstance(val, str):
                value[key] = str(val)
        
        return value

class DeploymentSerializer(serializers.ModelSerializer):
    environment_name = serializers.ReadOnlyField(source='environment.name')
    
    class Meta:
        model = Deployment
        fields = ['id', 'commit_hash', 'status', 'created_at', 'completed_at', 
                  'deployment_url', 'logs', 'environment_name']
        read_only_fields = ['id', 'created_at', 'completed_at', 'status', 
                           'deployment_url', 'logs']

class ProjectSerializer(serializers.ModelSerializer):
    latest_deployment = DeploymentSerializer(read_only=True)
    environments = EnvironmentVariableSerializer(many=True, read_only=True)
    owner_username = serializers.ReadOnlyField(source='owner.username')
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_url', 'framework_type', 'branch',
                  'created_at', 'last_deployed', 'owner_username', 'latest_deployment',
                  'environments']
        read_only_fields = ['id', 'created_at', 'last_deployed', 'owner_username']
    
    def get_latest_deployment(self, obj):
        latest = obj.deployments.order_by('-created_at').first()
        if latest:
            return DeploymentSerializer(latest).data
        return None