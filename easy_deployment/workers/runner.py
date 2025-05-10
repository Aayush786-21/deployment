import os
import logging
import time
import docker
from django.conf import settings
from deployment.models import Deployment
from deployment.services.container_service import ContainerService

logger = logging.getLogger(__name__)

class ContainerManager:
    """Manages running containers"""
    
    def __init__(self):
        self.container_service = ContainerService()
        self.docker_client = docker.from_env()
    
    def check_containers(self):
        """Check all containers for running deployments"""
        try:
            # Get all deployed deployments with container IDs
            active_deployments = Deployment.objects.filter(
                status='deployed'
            ).exclude(container_id__isnull=True)
            
            for deployment in active_deployments:
                try:
                    # Check if container is running
                    container = self.docker_client.containers.get(deployment.container_id)
                    
                    # If container is not running, mark deployment as failed
                    if container.status != 'running':
                        logger.warning(f"Container for deployment {deployment.id} is not running ({container.status})")
                        
                        # Get container logs
                        logs = container.logs().decode('utf-8', errors='replace')
                        
                        # Update deployment
                        deployment.status = 'failed'
                        deployment.logs += f"\nContainer stopped running. Status: {container.status}\n"
                        deployment.logs += f"Container logs:\n{logs}"
                        deployment.save()
                        
                except docker.errors.NotFound:
                    logger.warning(f"Container for deployment {deployment.id} not found")
                    deployment.status = 'failed'
                    deployment.logs += f"\nContainer not found. It may have been removed."
                    deployment.save()
                    
                except Exception as e:
                    logger.error(f"Error checking container for deployment {deployment.id}: {str(e)}")
                    deployment.logs += f"\nError checking container: {str(e)}"
                    deployment.save()
            
        except Exception as e:
            logger.error(f"Error checking containers: {str(e)}")
    
    def cleanup_old_containers(self, max_age_days=7):
        """Clean up old containers from completed deployments"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Get completed deployments older than max_age_days
            cutoff_date = timezone.now() - timedelta(days=max_age_days)
            old_deployments = Deployment.objects.filter(
                status__in=['deployed', 'failed'],
                completed_at__lt=cutoff_date
            ).exclude(container_id__isnull=True)
            
            for deployment in old_deployments:
                try:
                    # Try to stop and remove container
                    success, message = self.container_service.stop_container(deployment.container_id)
                    
                    if success:
                        deployment.logs += f"\nContainer cleaned up after {max_age_days} days of inactivity."
                        deployment.container_id = None
                        deployment.save()
                    else:
                        logger.warning(f"Failed to clean up container for deployment {deployment.id}: {message}")
                        deployment.logs += f"\nFailed to clean up container: {message}"
                        deployment.save()
                        
                except Exception as e:
                    logger.error(f"Error cleaning up container for deployment {deployment.id}: {str(e)}")
                    deployment.logs += f"\nError during cleanup: {str(e)}"
                    deployment.save()
                    
        except Exception as e:
            logger.error(f"Error during container cleanup: {str(e)}")

def run_container_manager():
    """Run the container manager process"""
    manager = ContainerManager()
    
    logger.info("Starting container manager...")
    
    while True:
        try:
            # Check containers
            manager.check_containers()
            
            # Clean up old containers once per day
            if time.localtime().tm_hour == 3:  # Run at 3 AM
                manager.cleanup_old_containers()
            
            # Sleep for a while before checking again
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Container manager error: {str(e)}")
            time.sleep(120)  # Sleep longer on error

if __name__ == "__main__":
    run_container_manager()