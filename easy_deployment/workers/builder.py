import os
import logging
import time
from django.conf import settings
from deployment.models import Deployment
from deployment.services.github_service import GitHubService
from deployment.services.deployment_service import DeploymentService
from deployment.services.container_service import ContainerService

logger = logging.getLogger(__name__)

class DeploymentWorker:
    """Worker to handle deployment jobs"""
    
    def process_deployment(self, deployment_id):
        """Process a single deployment"""
        try:
            # Get deployment
            deployment = Deployment.objects.get(id=deployment_id)
            
            # Check if deployment is in pending status
            if deployment.status != 'pending':
                logger.info(f"Deployment {deployment_id} is not in pending status, skipping")
                return
            
            # Get GitHub account
            github_account = deployment.project.owner.github_account
            
            # Create services
            github_service = GitHubService(github_account.access_token)
            deployment_service = DeploymentService(github_account)
            
            # Start the deployment process
            logger.info(f"Starting deployment process for deployment {deployment_id}")
            deployment = deployment_service.start_deployment_process(deployment)
            
            logger.info(f"Deployment {deployment_id} completed with status: {deployment.status}")
            
        except Deployment.DoesNotExist:
            logger.error(f"Deployment {deployment_id} not found")
        except Exception as e:
            logger.error(f"Error processing deployment {deployment_id}: {str(e)}")
            
            # Update deployment status if possible
            try:
                deployment = Deployment.objects.get(id=deployment_id)
                deployment.status = 'failed'
                deployment.logs += f"\nError: {str(e)}"
                deployment.save()
            except:
                pass

def run_worker():
    """Run the deployment worker process"""
    worker = DeploymentWorker()
    
    logger.info("Starting deployment worker...")
    
    while True:
        try:
            # Get pending deployments
            pending_deployments = Deployment.objects.filter(status='pending')
            
            for deployment in pending_deployments:
                logger.info(f"Processing deployment {deployment.id}")
                worker.process_deployment(deployment.id)
            
            # Sleep for a while before checking again
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
            time.sleep(10)  # Sleep longer on error

if __name__ == "__main__":
    run_worker()