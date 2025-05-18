from flask import Flask, request, abort
import hmac
import hashlib
import os
import subprocess

app = Flask(__name__)

# Tries to get the value of an environment variable called GITHUB_SECRET.
# If the environment variable is not set, it falls back to the default value: 'my_webhook'.
GITHUB_SECRET = os.environ.get('GITHUB_SECRET', 'my_webhook')

def verify_signature(payload, signature_header):
    if signature_header is None:
        return False

    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False

    mac = hmac.new(GITHUB_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    return hmac.compare_digest(expected_signature, signature)

@app.route('/webhook', methods=['POST'])
def github_webhook():
    signature = request.headers.get('X-Hub-Signature-256')
    payload = request.data

    if not verify_signature(payload, signature):
        abort(401, 'Signature verification failed')

    event = request.headers.get('X-GitHub-Event', 'ping')
    data = request.json

    if event == 'pull_request':
        action = data.get('action')
        pull_request = data.get('pull_request', {})
        repo_url = pull_request.get('head', {}).get('repo', {}).get('ssh_url')
        
        if action == 'closed':
            run_and_build_environment(repo_url)
            return 'Pull request is in process...', 200
            

    return 'Event ignored', 200


def run_and_build_environment(repo_url):
    repo_dir = 'gan-shmuel-app'

    if not os.path.exists(repo_dir):
        print("Cloning repository...")
        subprocess.run(['git', 'clone', '--branch', 'main', repo_url, repo_dir], check=True)
    else:
        print("Repository already exists. Fetching latest changes...")
        subprocess.run(['git', '-C', repo_dir, 'fetch'], check=True)

    subprocess.run(['docker', 'compose', '-f', 'docker-compose-deploy.yml', 'up'], check=True)


if __name__ == '__main__':
    app.run(debug=True ,host='0.0.0.0', port=8080)

