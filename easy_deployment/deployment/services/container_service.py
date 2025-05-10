import os
import subprocess
import logging
import docker
import tempfile
import shutil
from django.conf import settings

logger = logging.getLogger(__name__)

class ContainerService:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.base_container_port = settings.BASE_CONTAINER_PORT
        self.deployment_domain = settings.DEPLOYMENT_DOMAIN
        self.nginx_proxy_network = settings.NGINX_PROXY_NETWORK
    
    def _write_dockerfile(self, repo_dir, framework):
        """Write an appropriate Dockerfile based on the detected framework"""
        dockerfile_path = os.path.join(repo_dir, 'Dockerfile')
        
        # If Dockerfile exists, use it
        if os.path.exists(dockerfile_path):
            return dockerfile_path
        
        # Create framework-specific Dockerfile
        with open(dockerfile_path, 'w') as f:
            if framework.startswith('python-django'):
                f.write("""
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations (optional, can be moved to a startup script)
RUN python manage.py migrate

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "YOUR_PROJECT_NAME.wsgi:application"]
                """)
            elif framework.startswith('python-flask'):
                f.write("""
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
                """)
            elif framework.startswith('node'):
                f.write("""
FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build step for frameworks like React, Next.js
RUN if [ -f "next.config.js" ]; then npm run build; elif [ -f "vite.config.js" ]; then npm run build; elif [ -f "package.json" ]; then npm run build; fi

# Set the appropriate start command
CMD if [ -f "next.config.js" ]; then npm start; elif [ -f "package.json" ]; then npm start; else node index.js; fi
                """)
            elif framework.startswith('java'):
                f.write("""
FROM maven:3.8-openjdk-17 AS build
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM openjdk:17-slim
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
CMD ["java", "-jar", "app.jar"]
                """)
            elif framework == 'static':
                f.write("""
FROM nginx:alpine
COPY . /usr/share/nginx/html
                """)
            else:
                # Generic fallback
                f.write("""
FROM ubuntu:20.04
WORKDIR /app
COPY . .
CMD ["bash", "-c", "echo 'Application running. Configure container as needed.' && sleep infinity"]
                """)
        
        return dockerfile_path
    
    def build_and_run(self, repo_dir, project_name, deployment_id, framework, environment=None):
        """Build a container image and run it"""
        logs = []
        container_id = None
        
        try:
            # Sanitize project name for Docker
            safe_project_name = f"{project_name.lower().replace(' ', '-')}-{deployment_id}"
            
            # Write appropriate Dockerfile if it doesn't exist
            dockerfile_path = self._write_dockerfile(repo_dir, framework)
            logs.append(f"Created Dockerfile for {framework}")
            
            # Build the Docker image
            logs.append("Building Docker image...")
            image_tag = f"{safe_project_name}:latest"
            
            build_output = self.docker_client.images.build(
                path=repo_dir,
                tag=image_tag,
                rm=True
            )
            logs.append("Docker image built successfully")
            
            # Stop existing container if it exists
            try:
                existing_container = self.docker_client.containers.get(safe_project_name)
                logs.append(f"Stopping existing container {safe_project_name}")
                existing_container.stop()
                existing_container.remove()
            except docker.errors.NotFound:
                pass
            
            # Determine port
            container_port = self.base_container_port + deployment_id
            
            # Prepare environment variables
            env_vars = environment or {}
            
            # Add standard environment variables
            env_vars.update({
                'PORT': '8000',  # Standard port inside container
                'HOST': '0.0.0.0',
                'NODE_ENV': 'production',
                'DEPLOYMENT_ID': str(deployment_id),
                'PROJECT_NAME': project_name
            })
            
            # Run the container
            logs.append(f"Starting container {safe_project_name} on port {container_port}")
            container = self.docker_client.containers.run(
                image_tag,
                name=safe_project_name,
                detach=True,
                environment=env_vars,
                network=self.nginx_proxy_network,
                ports={
                    '8000/tcp': container_port
                },
                labels={
                    'traefik.enable': 'true',
                    f'traefik.http.routers.{safe_project_name}.rule': f'Host(`{safe_project_name}.{self.deployment_domain}`)',
                    f'traefik.http.services.{safe_project_name}.loadbalancer.server.port': '8000'
                }
            )
            
            logs.append(f"Container {safe_project_name} started successfully")
            container_id = container.id
            
            # Clean up
            shutil.rmtree(repo_dir)
            logs.append("Cleaned up temporary files")
            
            return container_id, "\n".join(logs)
            
        except Exception as e:
            error_msg = f"Error building/running container: {str(e)}"
            logger.error(error_msg)
            logs.append(error_msg)
            
            # Clean up on error
            try:
                shutil.rmtree(repo_dir)
            except:
                pass
                
            return container_id, "\n".join(logs)
    
    def stop_container(self, container_id):
        """Stop and remove a container"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()
            container.remove()
            return True, "Container stopped and removed successfully"
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {str(e)}")
            return False, f"Error stopping container: {str(e)}"
    
    def get_container_logs(self, container_id, lines=100):
        """Get logs from a container"""
        try:
            container = self.docker_client.containers.get(container_id)
            return container.logs(tail=lines).decode('utf-8')
        except Exception as e:
            logger.error(f"Error getting logs for container {container_id}: {str(e)}")
            return f"Error getting logs: {str(e)}"