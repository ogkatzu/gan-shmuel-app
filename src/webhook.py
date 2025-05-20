from flask import Flask, request, Response
import hmac
import hashlib
import os
import subprocess
import json
import smtplib, ssl
import logging
import shutil
from dotenv import load_dotenv
from email.mime.text import MIMEText



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

load_dotenv()
# Configuration
CONFIG = {
    'repo_path': os.environ.get('REPO_PATH', '/tmp/repo'),
    'repo_url': os.environ.get('REPO_URL', '/tmp/repo'),
    'test_command': os.environ.get('TEST_COMMAND', 'pytest'),
    'github_secret': os.environ.get('GITHUB_SECRET', ''),
    'email_sender': os.environ.get('EMAIL_SENDER', 'ci@example.com'),
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.example.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
    'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
    'prod_deploy_script': os.environ.get('PROD_DEPLOY_SCRIPT', 'scripts/deploy_prod.sh'),
    'weight_emails':os.environ.get('WEIGHT_EMAILS', ''),
    'billing_emails':os.environ.get('BILLING_EMAILS', ''),
    'devops_emails':os.environ.get('DEVOPS_EMAILS', ''),
    'workdir_test': os.environ.get('WORKDIR_TEST', '')
}

def build_email(Subject, To, Msg):
    message = MIMEText(Msg)
    message["Subject"] = Subject
    message["From"] = CONFIG['email_sender']
    message["To"] = To

    return message.as_string()

def send_email(message, receiver_email):
    logger.info("Sending email")
    context = ssl.create_default_context()
    with smtplib.SMTP(CONFIG['smtp_server'], CONFIG['smtp_port']) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(CONFIG['email_sender'], CONFIG['smtp_password'])
        server.sendmail(CONFIG['email_sender'], receiver_email, message)


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
    subprocess.run(['docker', 'compose', '-f', 'docker-compose-test.yaml', 'down'], check=True)
    subprocess.run(['rm', '-rf', CONFIG['workdir_test'] + '/' + CONFIG['repo_path']])
    return True


def run_tests(branch):
    logger.info("Running tests")
    try:
        
        # Run tests through docker-compose exec
        # Assuming there's a main service where tests should run
        # TODO - Update this to run tests in the correct service
        if not os.path.exists(CONFIG['workdir_test'] + '/' + CONFIG['repo_path']):
            subprocess.run(['git', 'clone', '--branch', branch, CONFIG['repo_url'],CONFIG['workdir_test'] + '/' + CONFIG['repo_path']], check=True)

        #billing_command = ["pyestest", "test_env/gan-shmuel-app/billing/test/test_api.py"]
        wieght_command = ["pyestest", "test_env/gan-shmuel-app/weight/test/test_api.py"]

        logger.info(f"Running tests wieght")
        result_wieght = subprocess.run(
            wieght_command,
            cwd=CONFIG['workdir_test'],
            capture_output=True,
            text=True
        )

        # logger.info(f"Running tests billing")
        # result_billing = subprocess.run(
        #     billing_command,
        #     cwd=CONFIG['workdir_test'],
        #     capture_output=True,
        #     text=True
        # )
        
        # Log test output for debugging
        logger.info(f"Test stdout: {result_wieght.stdout}")
        if result_wieght.stderr:
            logger.warning(f"Test stderr: {result_wieght.stderr}")

        # logger.info(f"Test stdout: {result_billing.stdout}")
        # if result_billing.stderr:
        #     logger.warning(f"Test stderr: {result_billing.stderr}")
            
        logger.info(f"Tests completed with return code: {result_wieght.returncode}")
        #logger.info(f"Tests completed with return code: {result_billing.returncode}")

        #return result_wieght.returncode == 0 and result_billing.returncode == 0, result_wieght.stdout + result_wieght.stderr + "\n" + result_billing.stdout + result_billing.stderr
        return result_wieght.returncode == 0 , result_wieght.stdout + result_wieght.stderr
    except Exception as error:
        logger.error(f"Error running tests: {str(error)}")
        return False, str(error)




def deploy_to_production():
    logger.info("Deploying to production")
    try:
        # Prod env down
        logger.info("Taking down production environment")
        subprocess.run(['docker', 'compose', '-f', 'docker-compose-deploy.yaml', 'down'], check=True)
        # This would typically involve SSH commands or API calls to your production environment
        
        # Fetch latest changes to main
        logger.info("Fetching latest changes to main")
        fetch_branch('main')
        
        # Prod env up
        logger.info("Bringing up production environment")
        subprocess.run(['docker', 'compose', '-f', 'docker-compose-deploy.yaml', 'up'], check=True)
        return True

    except Exception as error:
        logger.error(f"Error deploying to production: {str(error)}")
        return False


def clone_repo(repo_url, branch, is_local=False):
    try:
        # Remove existing repo if it exists
        if os.path.exists(CONFIG['repo_path']): #TODO:check if is nessesery
            shutil.rmtree(CONFIG['repo_path'])
        
        # Clone the repository
        logger.info(f"Cloning {repo_url}, branch: {branch}")
        subprocess.run(['git', 'clone', '--branch', branch, repo_url, CONFIG['repo_path']], check=True)
        logger.info("Repository cloned successfully")
        return True
    except Exception as error:
        logger.error(f"Error cloning repository: {str(error)}")
        return False
    
def fetch_branch(branch):
    try:
        logger.info(f"Fetching branch: {branch}")
        subprocess.run(['git', '-C', CONFIG['repo_path'], 'fetch', 'origin'], check=True)
        subprocess.run(['git', 'checkout', branch], check=True)
        subprocess.run(['git', '-C', CONFIG['repo_path'], 'pull', 'origin', branch], check=True)
        logger.info(f"Successfully checked out branch: {branch}")
        return True
    except Exception as error:
        logger.error(f"Error fetching branch: {str(error)}")
        return False

def send_email_to_all(Subject, Msg):
    emails = json.loads(CONFIG['weight_emails'])
    for email in emails.values():
        msg = build_email(Subject, email, Msg)
        send_email(msg, email)

    emails = json.loads(CONFIG['billing_emails'])
    for email in emails.values():
        msg = build_email(Subject, email, Msg)
        send_email(msg, email)

    emails = json.loads(CONFIG['devops_emails'])
    for email in emails.values():
        msg = build_email(Subject, email, Msg)
        send_email(msg, email)


@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method != 'POST': # If this is not a post request we will send this response
        response_data = json.dumps({'status': 'error', 'message': 'Method not allowed'})
        return Response(response=response_data, status=405, mimetype='application/json')
    
    logger.info("Received webhook payload")
    
    signature = request.headers.get('X-Hub-Signature-256')
    # Get payload
    payload = request.json
    branch =''

    if not verify_signature(payload, signature):# check if the request from github
      os.abort(401, 'Signature verification failed')
    
    # Extract information
    is_merge_to_main = False
    is_pr = False

    is_repo_local = os.path.exists(CONFIG['repo_path'])

 
    # Check if it's a push to main
    if 'ref' in payload and payload['ref'] == f"refs/heads/main":
        is_merge_to_main = True
        repo_url = CONFIG['repo_url']
        branch = 'main'
    
    # Check if it's a PR
    elif 'pull_request' in payload:
        is_pr = True
        repo_url = CONFIG['repo_url']
        branch = payload['pull_request']['head']['ref'] # the branch the pull request is from
    
    # If neither PR nor merge to main, return 200 with no action
    if not is_merge_to_main and not is_pr:
        logger.info("Webhook is neither PR nor merge to main, no action needed")
        response_data = json.dumps({'status': 'success', 'message': 'No action needed'})
        return Response(response=response_data, status=200, mimetype='application/json')
    
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
            response_data = json.dumps({'status': 'error', 'message': 'Failed to get repository'})
            return Response(response=response_data, status=500, mimetype='application/json')
    
    # Merge to main path
    elif is_merge_to_main:
        logger.info("Processing merge to main workflow")
        
        # Clone or fetch based on repo locality
        if is_repo_local:
            success = fetch_branch('main')
            result_message += f"Fetched main branch\n"
        else:
            success = clone_repo(repo_url, 'main')
            result_message += f"Cloned main branch\n"
        
        if not success:
            response_data = json.dumps({'status': 'error', 'message': 'Failed to get repository'})
            return Response(response=response_data, status=500, mimetype='application/json')
    
    # Set up test environment
    setup_success = setup_test_env()
    if not setup_success:
        devops_team = json.loads(CONFIG['devops_emails'])
        for email in devops_team.values():
            send_email(build_email("Subject: Test Environment Setup Failed", email, "CI pipeline could not set up test environment."), email)
        response_data = json.dumps({'status': 'error', 'message': 'Failed to setup test environment'})
        return Response(response=response_data, status=500, mimetype='application/json')
    
    # Run tests
    tests_passed, test_output = run_tests(branch)
    result_message += f"Test results: {'PASSED' if tests_passed else 'FAILED'}\n"
    
    # Tear down test environment
    test_env_down_and_clean()
    
    # Check results and send email
    if is_pr:
        emails = json.loads(CONFIG['weight_emails'])
        if not tests_passed:
            if 'billing' in branch:
                emails = json.loads(CONFIG['billing_emails'])

        for email in emails.values():
            Msg = build_email("FAILED - PR", email, f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}")
            send_email(Msg, email)
            
        emails = json.loads(CONFIG['devops_emails'])
        for email in emails.values():
            Msg = build_email("FAILED - PR", email, f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}")
            send_email(Msg, email)
        else:
            send_email_to_all("PASSED - PR" , f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}")

    else:
        emails = json.loads(CONFIG['devops_emails'])
        if not tests_passed:
            send_email(build_email("FAILED - MERGE",  payload['head_commit']['author']['email'], f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}"), email)
            for email in emails.values():
                send_email(build_email("FAILED - MERGE", email, f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}"), email)
        else:
            send_email_to_all("PASSED - MERGE" , f"Test Results:\n{result_message}\n\nTest Output:\n{test_output}\n\nPull latest version.")
            
    
    # For merge to main and successful tests, deploy to production
    if is_merge_to_main and tests_passed:
        deploy_success = deploy_to_production()
        if deploy_success:
            send_email_to_all("Deployed to production successfully", "CI pipeline successfully deployed to production.")
            result_message = "Deployed to production successfully\n"
        else:
            emails = json.loads(CONFIG['devops_emails'])
            for email in emails.values():
                Msg = build_email("Failed to deploy to production", email, "CI pipeline failed to deploy to production.")
                send_email(Msg, email)
            result_message = "Failed to deploy to production\n"
    
    response_data = json.dumps({'status': 'success', 'message': result_message, 'tests_passed':tests_passed})
    return Response(response=response_data, status=200, mimetype='application/json')

@app.route('/health', methods=['GET'])
def health():
    response_data = json.dumps({'status': 'healthy'})
    return Response(response=response_data, status=200, mimetype='application/json')


# Tries to get the value of an environment variable called GITHUB_SECRET.
# If the environment variable is not set, it falls back to the default value: 'my_webhook'.
def verify_signature(payload, signature_header):
    if signature_header is None:
        return False

    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False

    mac = hmac.new(CONFIG['github_secret'].encode(), msg=payload, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()
    return hmac.compare_digest(expected_signature, signature)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)