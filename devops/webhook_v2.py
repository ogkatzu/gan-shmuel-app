from flask import Flask, request, jsonify
import os
import json
import subprocess
import shutil
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import git
import time
import ssl, smtplib
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
    'main_branch': os.environ.get('MAIN_BRANCH', 'main'),
    'repo_path': os.environ.get('REPO_PATH', '/tmp/repo'),
    'test_command': os.environ.get('TEST_COMMAND', 'pytest'),
    'github_secret': os.environ.get('GITHUB_SECRET', 'my_webhook'),
    'email_sender': os.environ.get('EMAIL_SENDER', 'devopsganshmuel@gmail.com'),
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
    'smtp_username': os.environ.get('SMTP_USERNAME', ''),
    'smtp_password': os.environ.get('SMTP_PASSWORD', 'cdghvoecadvndscn'),
    # Docker environment settings
    'test_docker_compose': os.environ.get('TEST_DOCKER_COMPOSE', 'docker-compose-test.yaml'),
    'prod_docker_compose': os.environ.get('PROD_DOCKER_COMPOSE', 'docker-compose-prod.yaml'),
    'docker_compose_timeout': int(os.environ.get('DOCKER_COMPOSE_TIMEOUT', 180)),
    'repo_url': os.environ.get('REPO_URL', 'https://github.com/ogkatzu/gan-shmuel-app.git')
}

def send_email(subject, message, recive,is_failure=False):
    """Send email with test results"""
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(CONFIG['smtp_server'], CONFIG['smtp_port']) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(CONFIG['smtp_username'], CONFIG['smtp_password'])
            server.sendmail(CONFIG['email_sender'],recive, message)
            server.quit()
        logger.info(f"Email sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def setup_test_env():
    """Set up the test environment using docker-compose-test.yaml"""
    logger.info("Setting up test environment with docker-compose")
    try:
        # Check if docker-compose-test.yaml exists
        docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yaml')
        if not os.path.exists(docker_compose_file):
            logger.warning(f"docker-compose-test.yaml not found at {docker_compose_file}")
            docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yml')
            if not os.path.exists(docker_compose_file):
                logger.error("Neither docker-compose-test.yaml nor docker-compose-test.yml found")
                return False
        
        # Run docker-compose up with the test configuration
        logger.info(f"Starting test environment with {docker_compose_file}")
        result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'up', '-d'],
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to start test environment: {result.stderr}")
            return False
            
        # Give containers time to initialize
        logger.info("Waiting for test containers to initialize...")
        time.sleep(10)
        
        logger.info("Test environment setup complete")
        return True
    except Exception as e:
        logger.error(f"Error setting up test environment: {str(e)}")
        return False

def teardown_test_env():
    """Tear down the test environment using docker-compose-test.yaml"""
    logger.info("Tearing down test environment")
    try:
        # Determine which docker-compose file to use
        docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yaml')
        if not os.path.exists(docker_compose_file):
            docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yml')
            if not os.path.exists(docker_compose_file):
                logger.error("Neither docker-compose-test.yaml nor docker-compose-test.yml found")
                return False
        
        # Run docker-compose down
        logger.info(f"Stopping test environment with {docker_compose_file}")
        result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'down', '--volumes', '--remove-orphans'],
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to tear down test environment: {result.stderr}")
            return False
            
        logger.info("Test environment teardown complete")
        return True
    except Exception as e:
        logger.error(f"Error tearing down test environment: {str(e)}")
        return False

def run_tests():
    """Run the test suite in the docker environment"""
    logger.info("Running tests")
    try:
        # Determine which docker-compose file to use
        docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yaml')
        if not os.path.exists(docker_compose_file):
            docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-test.yml')
        
        # Run tests through docker-compose exec
        # Assuming there's a main service where tests should run
        # TODO - Update this to run tests in the correct service
        # billing_command = 
        wieght_command = ["pyestest", "/weight/test/test_api.py"]
        logger.info(f"Running tests")
        result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'exec', '-T', 'weight_app_test'] + wieght_command,
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        # Log test output for debugging
        logger.info(f"Test stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Test stderr: {result.stderr}")
            
        logger.info(f"Tests completed with return code: {result.returncode}")
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return False, str(e)


def deploy_to_production():
    """Deploy code to production using docker-compose-prod.yaml"""
    logger.info("Deploying to production")
    try:
        # Determine which docker-compose file to use for production
        docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-prod.yaml')
        if not os.path.exists(docker_compose_file):
            docker_compose_file = os.path.join(CONFIG['repo_path'], 'docker-compose-prod.yml')
            if not os.path.exists(docker_compose_file):
                logger.error("Neither docker-compose-prod.yaml nor docker-compose-prod.yml found")
                return False
        
        # Prod env down - take down production environment
        logger.info("Taking down production environment")
        down_result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'down', '--volumes', '--remove-orphans'],
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        if down_result.returncode != 0:
            logger.error(f"Failed to take down production environment: {down_result.stderr}")
            return False
            
        # Fetch latest changes to main
        logger.info("Fetching latest changes to main")
        repo = git.Repo(CONFIG['repo_path'])
        repo.git.fetch('origin', CONFIG['main_branch'])
        repo.git.checkout(CONFIG['main_branch'])
        repo.git.pull('origin', CONFIG['main_branch'])
        
        # Prod env up - bring up production environment
        logger.info("Building and bringing up production environment")
        # First build the images
        build_result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'build'],
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        if build_result.returncode != 0:
            logger.error(f"Failed to build production environment: {build_result.stderr}")
            return False
            
        # Then start the containers
        up_result = subprocess.run(
            ['docker-compose', '-f', docker_compose_file, 'up', '-d'],
            cwd=CONFIG['repo_path'],
            capture_output=True,
            text=True
        )
        
        if up_result.returncode != 0:
            logger.error(f"Failed to start production environment: {up_result.stderr}")
            return False
            
        logger.info("Production deployment completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error deploying to production: {str(e)}")
        return False

def clone_repo(repo_url, branch, is_local=False):
    """Clone the repository or update local copy"""
    try:
        # Remove existing repo if it exists
        if os.path.exists(CONFIG['repo_path']):
            shutil.rmtree(CONFIG['repo_path'])
        
        # Clone the repository
        logger.info(f"Cloning {repo_url}, branch: {branch}")
        git.Repo.clone_from(repo_url, CONFIG['repo_path'], branch=branch)
        logger.info("Repository cloned successfully")
        return True
    except Exception as e:
        logger.error(f"Error cloning repository: {str(e)}")
        return False

def fetch_branch(branch):
    """Fetch and checkout a branch in an existing repository"""
    try:
        repo = git.Repo(CONFIG['repo_path'])
        logger.info(f"Fetching branch: {branch}")
        repo.git.fetch('origin', branch)
        repo.git.checkout(branch)
        logger.info(f"Successfully checked out branch: {branch}")
        return True
    except Exception as e:
        logger.error(f"Error fetching branch: {str(e)}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook"""
    if request.method != 'POST':
        return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405
    
    logger.info("Received webhook payload")
    
    # Get payload
    payload = request.json
    with open('payload.json', 'w') as f:
        json.dump(payload, f, indent=4)
    # Extract information
    is_merge_to_main = False
    is_pr = False
    is_repo_local = os.path.exists(CONFIG['repo_path'])
    if payload.get('commits'):
        commit_id = payload['commits'][-1]['author']['email']
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
    result = subprocess.run(
    ["git", "-C", CONFIG['repo_path'], "show", "--no-patch", "--pretty=format:'%an|%ae'", commit_id],
    capture_output=True,
    text=True,
    check=True
    )
    github_username, developer_email = output.split("|")
    # Extract Name and Email
    output = result.stdout.strip()  # Remove extra spaces/newlines
    github_username, developer_email = output.split("|")
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
    
    # Check results and send email
    send_email(
        f"{'PASSED' if tests_passed else 'FAILED'} - {'PR' if is_pr else 'Merge to main'}",
        f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}\n"
    )
    
    # For merge to main and successful tests, deploy to production
    if is_merge_to_main and tests_passed:
        deploy_success = deploy_to_production()
        if deploy_success:
            result_message += "Deployed to production successfully\n"
            send_email("Deployment to Production Successful", f"CI pipeline successfully deployed to production.\n\n{result_message}", developer_email, True)
        else:
            result_message += "Failed to deploy to production\n"
            send_email("Deployment to Production Failed", f"CI pipeline failed to deploy to production.\n\n{result_message}", developer_email, True)
    
    return jsonify({
        'status': 'success',
        'message': result_message,
        'tests_passed': tests_passed,
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)