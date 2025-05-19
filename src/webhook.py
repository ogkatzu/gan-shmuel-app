from flask import Flask, request, abort
import hmac
import hashlib
import os
import subprocess
import json
import smtplib, ssl

app = Flask(__name__)

# Tries to get the value of an environment variable called GITHUB_SECRET.
# If the environment variable is not set, it falls back to the default value: 'my_webhook'.
GITHUB_SECRET = os.environ.get('GITHUB_SECRET', 'my_webhook')
PORT = 587
PASSWORD = "cdghvoecadvndscn"
context = ssl.create_default_context()
smtp_server = "smtp.gmail.com"
sender_email = "devopsganshmuel@gmail.com"
receiver_email = ""
message = """\
Subject: Hi there

This message is sent from Python."""



def verify_signature(payload, signature_header):
    if signature_header is None:
        return False

    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False

    mac = hmac.new(GITHUB_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    return hmac.compare_digest(expected_signature, signature)

#  @app.route('/webhook', methods=['POST', 'GET'])
# def github_webhook():
#     signature = request.headers.get('X-Hub-Signature-256')
#     payload = request.data

# #    if not verify_signature(payload, signature):
# #        abort(401, 'Signature verification failed')

#     event = request.headers.get('X-GitHub-Event', 'ping')
#     data = request.json
#     print(json.dumps(data, indent=2))
#     #if event == 'pull_request':
#     action = data.get('action')
#     repository = data.get('repository', {})
#     repo_url = repository.get('clone_url')
#     #pull_request = data.get('push', {})
#     #repo_url = pull_request.get('head', {}).get('repo', {}).get('clone_url')
#     print(repo_url)
#     #    if action == 'closed':
#     run_and_build_environment(repo_url)
#     return 'Pull request is in process...', 200


#     return 'Event ignored', 200 
 
# @app.route('/webhook', methods=['GET'])
# def github_webhook():
#     signature = request.headers.get('X-Hub-Signature-256')
#     payload = request.data

#     if not verify_signature(payload, signature):
#      abort(401, 'Signature verification failed')

#     data = request.json
#     repository = data.get('repository', {})
#     repo_url = repository.get('clone_url')
#     sender_login = payload['sender']['login']
#     #receiver_email = users[sender_login]
#     run_and_build_environment(repo_url)

#     return 'Pull request is in process...', 200

# def run_and_build_environment(repo_url):
#     repo_dir = 'gan-shmuel-app'

#     if not os.path.exists(repo_dir):
#         print("Cloning repository...")
#         subprocess.run(['git', 'clone', '--branch', 'main', str(repo_url), repo_dir], check=True)
#     else:
#         print("Repository already exists. Fetching latest changes...")
#         subprocess.run(['git', '-C', repo_dir, 'fetch'], check=True)

#         #subprocess.run(['docker', 'compose', '-f', 'docker-compose-deploy.yaml', 'up'], check=True)

#     context = ssl.create_default_context()
# with smtplib.SMTP(smtp_server, PORT) as server:
#      server.ehlo()  # Can be omitted
#      server.starttls(context=context)
#      server.ehlo()  # Can be omitted
#      server.login(sender_email, PASSWORD)
#      server.sendmail(sender_email, receiver_email, message)
def cheking_docker_up():
    print("getting the webhook http merge request")
    print("verify signature")
    print("checking if there is a local repo")
    print("clone the repo now")
    subprocess.run(['git', 'clone', '--branch', 'main', "https://github.com/ogkatzu/gan-shmuel-app.git", "gan-shmuel-app"], check=True)
    print("running container")
    subprocess.run(['docker', 'compose', '-f', 'docker-compose-deploy.yaml', 'up'], check=True)


if __name__ == '__main__':
    #app.run(debug=True ,host='0.0.0.0', port=8080)
    cheking_docker_up()