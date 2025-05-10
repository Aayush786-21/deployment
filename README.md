# Easy Deployment Platform

This project is a containerized deployment platform inspired by services like Vercel. It automates the deployment of web applications using frameworks like Django, Flask, Node.js, and more.

## Features

- **GitHub Integration**: Connect your GitHub account to deploy projects directly from repositories.
- **Framework Detection**: Automatically detects the framework used in your repository.
- **Environment Variables**: Manage environment variables for different deployment environments.
- **Containerized Deployment**: Deploy applications in isolated Docker containers.
- **Logs and Monitoring**: View deployment logs and monitor the status of running containers.

## Prerequisites

- Python 3.10 or higher
- Docker
- PostgreSQL
- Redis
- GitHub account with OAuth credentials
- Node.js (optional, for Node.js projects)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/easy-deployment.git
   cd easy-deployment
   ```

2. Set up a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the `.env` file:
   Create a `.env` file in the root directory and configure the following variables:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DB_NAME=vercel_clone
   DB_USER=postgres
   DB_PASSWORD=your-db-password
   DB_HOST=localhost
   DB_PORT=5432
   CORS_ALLOWED_ORIGINS=http://localhost:3000
   GITHUB_CLIENT_ID=your-github-client-id
   GITHUB_CLIENT_SECRET=your-github-client-secret
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   BASE_CONTAINER_PORT=8000
   DEPLOYMENT_DOMAIN=localhost
   NGINX_PROXY_NETWORK=web
   ```

5. Apply migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage

1. Access the platform at `http://localhost:8000`.
2. Log in with your superuser credentials.
3. Connect your GitHub account via the dashboard.
4. Create a project by specifying the repository URL and branch.
5. Deploy the project and monitor logs in real-time.

## Running Celery Workers

Start the Celery worker and beat scheduler:
```bash
celery -A easy_deployment worker --loglevel=info
celery -A easy_deployment beat --loglevel=info
```

## Running Docker Containers

Ensure Docker is running and accessible:
```bash
docker ps
```

## License

This project is licensed under the MIT License.
