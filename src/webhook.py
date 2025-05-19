from flask import Flask, request, Response
import hmac
import hashlib
import os
import subprocess
import json
import smtplib, ssl
import logging
import shutil



# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ci_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
CONFIG = {
    'main_branch': 'main',
    'repo_path': os.environ.get('REPO_PATH', '/tmp/repo'),
    'test_command': os.environ.get('TEST_COMMAND', 'pytest'),
    # 'build_command': os.environ.get('BUILD_COMMAND', 'npm run build'),
    'github_secret': os.environ.get('GITHUB_SECRET', ''),
    'email_sender': os.environ.get('EMAIL_SENDER', 'ci@example.com'),
    'email_recipients': os.environ.get('EMAIL_RECIPIENTS', 'dev@example.com').split(','),
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.example.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
    'smtp_username': os.environ.get('SMTP_USERNAME', ''),
    'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
    'prod_deploy_script': os.environ.get('PROD_DEPLOY_SCRIPT', 'scripts/deploy_prod.sh'),
}

def send_email(message, receiver_email):
    logger.info("Sending email")
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, PORT) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(sender_email, PASSWORD)
        server.sendmail(sender_email, receiver_email, message)


def setup_test_env():
    logger.info("Setting up test environment")
    try:
        subprocess.run(['docker', 'compose', '-f', 'docker-compose-test.yaml', 'up'], check=True)
        logger.info("Test environment setup complete")
        return True
    
    except Exception as error:
        logger.error(f"Error setting up test environment: {str(error)}")
        return False
    

def test_env_down_and_clean():
    logger.info("Tearing down test environment")
    # Add cleanup code if needed
    return True


def run_tests():
    logger.info("Running tests")
    try:
        result = subprocess.run(
            CONFIG['test_command'].split(), 
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        logger.info(f"Tests completed with return code: {result.returncode}")
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as error:
        logger.error(f"Error running tests: {str(error)}")
        return False, str(error)
    

"""
def deploy_to_production():
    logger.info("Deploying to production")
    try:
        # Prod env down
        logger.info("Taking down production environment")
        # This would typically involve SSH commands or API calls to your production environment
        
        # Fetch latest changes to main
        logger.info("Fetching latest changes to main")
        
        # Prod env up
        logger.info("Bringing up production environment")
        
        # Run deploy script if it exists
        if os.path.exists(os.path.join(CONFIG['repo_path'], CONFIG['prod_deploy_script'])):
            deploy_result = subprocess.run(
                [os.path.join(CONFIG['repo_path'], CONFIG['prod_deploy_script'])],
                cwd=CONFIG['repo_path'],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Deployment completed: {deploy_result.stdout}")
            return True
        else:
            logger.warning("No deployment script found")
            return False
    except Exception as e:
        logger.error(f"Error deploying to production: {str(e)}")
        return False

"""
def clone_repo(repo_url, branch, is_local=False):
    """Clone the repository or update local copy"""
    try:
        # Remove existing repo if it exists
        if os.path.exists(CONFIG['repo_path']):
            shutil.rmtree(CONFIG['repo_path'])
        
        # Clone the repository
        logger.info(f"Cloning {repo_url}, branch: {branch}")
        subprocess.run(['git', 'clone', '--branch', 'main', repo_url, repo_dir], check=True)
        logger.info("Repository cloned successfully")
        return True
    except Exception as error:
        logger.error(f"Error cloning repository: {str(error)}")
        return False
    
def fetch_branch(branch, repo_dir):
    try:
        logger.info(f"Fetching branch: {branch}")
        subprocess.run(['git', '-C', repo_dir, 'fetch', 'origin'], check=True)
        subprocess.run(['git', 'checkout', branch], check=True)
        subprocess.run(['git', '-C', repo_dir, 'pull', 'origin', branch], check=True)
        logger.info(f"Successfully checked out branch: {branch}")
        return True
    except Exception as error:
        logger.error(f"Error fetching branch: {str(error)}")
        return False
    

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method != 'POST':
        response_data = json.dumps({'status': 'error', 'message': 'Method not allowed'})
        return Response(response=response_data, status=405, mimetype='application/json')
    
    logger.info("Received webhook payload")
    
    signature = request.headers.get('X-Hub-Signature-256')
    # Get payload
    payload = request.json
    if not verify_signature(payload, signature):
      os.abort(401, 'Signature verification failed')
    
    # Extract information
    is_merge_to_main = False
    is_pr = False
    is_repo_local = os.path.exists(CONFIG['repo_path'])


#TODO:continue from here



    
    # Check if it's a push to main
    if 'ref' in payload and payload['ref'] == f"refs/heads/{CONFIG['main_branch']}":
        is_merge_to_main = True
        repo_url = payload['repository']['clone_url']
        branch = CONFIG['main_branch']
    
    # Check if it's a PR
    elif 'pull_request' in payload:
        is_pr = True
        repo_url = payload['repository']['clone_url']
        branch = payload['pull_request']['head']['ref']
    
    # If neither PR nor merge to main, return 200 with no action
    if not is_merge_to_main and not is_pr:
        logger.info("Webhook is neither PR nor merge to main, no action needed")
        return jsonify({'status': 'success', 'message': 'No action needed'}), 200
    
    # Process according to the flowchart
    result_message = ""
    
    # PR path
    if is_pr:
        logger.info("Processing PR workflow")
        
        # Clone or fetch based on repo locality
        if is_repo_local:
            success = fetch_branch(branch)
            result_message += f"Fetched tested branch: {branch}\n"
        else:
            success = clone_repo(repo_url, branch)
            result_message += f"Cloned tested branch: {branch}\n"
        
        if not success:
            return jsonify({'status': 'error', 'message': 'Failed to get repository'}), 500
    
    # Merge to main path
    elif is_merge_to_main:
        logger.info("Processing merge to main workflow")
        
        # Clone or fetch based on repo locality
        if is_repo_local:
            success = fetch_branch(CONFIG['main_branch'])
            result_message += f"Fetched main branch\n"
        else:
            success = clone_repo(repo_url, CONFIG['main_branch'])
            result_message += f"Cloned main branch\n"
        
        if not success:
            return jsonify({'status': 'error', 'message': 'Failed to get repository'}), 500
    
    # Set up test environment
    setup_success = setup_test_env()
    if not setup_success:
        send_email("Test Environment Setup Failed", "CI pipeline could not set up test environment.", True)
        return jsonify({'status': 'error', 'message': 'Failed to setup test environment'}), 500
    
    # Run tests
    tests_passed, test_output = run_tests()
    result_message += f"Test results: {'PASSED' if tests_passed else 'FAILED'}\n"
    
    # Tear down test environment
    teardown_test_env()
    
    # Run all additional checks
    all_checks_passed, check_output = run_all_checks()
    result_message += f"Additional checks: {'PASSED' if all_checks_passed else 'FAILED'}\n"
    
    # Check results and send email
    send_email(
        f"{'PASSED' if tests_passed else 'FAILED'} - {'PR' if is_pr else 'Merge to main'}",
        f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}\n\nCheck Output:\n{check_output}"
    )
    
    # For merge to main and successful tests, deploy to production
    if is_merge_to_main and tests_passed and all_checks_passed:
        deploy_success = deploy_to_production()
        if deploy_success:
            result_message += "Deployed to production successfully\n"
            send_email("Deployment to Production Successful", f"CI pipeline successfully deployed to production.\n\n{result_message}")
        else:
            result_message += "Failed to deploy to production\n"
            send_email("Deployment to Production Failed", f"CI pipeline failed to deploy to production.\n\n{result_message}", True)
    
    return jsonify({
        'status': 'success',
        'message': result_message,
        'tests_passed': tests_passed,
        'all_checks_passed': all_checks_passed
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


# Tries to get the value of an environment variable called GITHUB_SECRET.
# If the environment variable is not set, it falls back to the default value: 'my_webhook'.
GITHUB_SECRET = os.environ.get('GITHUB_SECRET', 'my_webhook')
PORT = 587
PASSWORD = "cdghvoecadvndscn"
context = ssl.create_default_context()
smtp_server = "smtp.gmail.com"
sender_email = "devopsganshmuel@gmail.com"
receiver_email = input("Type your email and press enter: ")
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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)