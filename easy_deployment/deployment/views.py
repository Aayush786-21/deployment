# deployment/views.py
from django.shortcuts import redirect
from django.conf import settings
import requests
from .models import GithubAccount

def github_login(request):
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo"
    return redirect(github_auth_url)

def github_callback(request):
    code = request.GET.get('code')
    
    # Exchange code for access token
    response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': code
        },
        headers={'Accept': 'application/json'}
    )
    
    data = response.json()
    access_token = data.get('access_token')
    
    # Get user info
    user_response = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': f'token {access_token}'}
    )
    github_user = user_response.json()
    
    # Store GitHub account info
    github_account, created = GithubAccount.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': access_token,
            'github_username': github_user['login']
        }
    )
    
    return redirect('dashboard')