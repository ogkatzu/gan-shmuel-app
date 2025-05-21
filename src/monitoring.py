#!/usr/bin/env python3
import requests
import time
import logging
import argparse
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('docker_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class DockerMonitor:
    def __init__(self, container_url, check_interval=60, max_retries=3, retry_delay=5):
        """
        Initialize the Docker container monitor.
        
        Args:
            container_url (str): URL endpoint to check container status
            check_interval (int): Time between checks in seconds
            max_retries (int): Number of retries before sending alert
            retry_delay (int): Seconds to wait between retries
        """
        self.container_url = container_url
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.consecutive_failures = 0
        self.alert_sent = False
        
    def check_container(self):
        """Check if the Docker container is running."""
        try:
            response = requests.get(self.container_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Container health check passed. Status code: {response.status_code}")
                # Reset failure counter on success
                if self.consecutive_failures > 0:
                    logger.info("Container is back up after previous failures.")
                    if self.alert_sent:
                        self.send_recovery_notification()
                self.consecutive_failures = 0
                self.alert_sent = False
                return True
            else:
                logger.warning(f"Container health check failed. Status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to container: {str(e)}")
            return False
    
    def send_failure_notification(self):
        """Send notification that container is down."""
        try:
            # Here you would call your existing send_mail() function
            # For demonstration, we'll just log the action
            logger.critical(f"ALERT: Container down at {datetime.now()}! Sending notification email.")
            
            # Uncomment and modify this to use your actual send_mail function
            # from your_mail_module import send_mail
            # send_mail(
            #     subject="ALERT: Docker Container Down",
            #     message=f"Your Docker container at {self.container_url} is down. "
            #             f"Failed after {self.max_retries} retries. "
            #             f"Time of failure: {datetime.now()}",
            #     to_email="your-email@example.com"
            # )
            
            self.alert_sent = True
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return False
    
    def send_recovery_notification(self):
        """Send notification that container is back up."""
        try:
            # Here you would call your existing send_mail() function
            logger.info(f"RECOVERY: Container is back up at {datetime.now()}! Sending recovery notification.")
            
            # Uncomment and modify this to use your actual send_mail function
            # from your_mail_module import send_mail
            # send_mail(
            #     subject="RECOVERY: Docker Container Back Online",
            #     message=f"Your Docker container at {self.container_url} is back online. "
            #             f"Time of recovery: {datetime.now()}",
            #     to_email="your-email@example.com"
            # )
            
            return True
        except Exception as e:
            logger.error(f"Failed to send recovery notification: {str(e)}")
            return False
    
    def run(self):
        """Main monitoring loop."""
        logger.info(f"Starting Docker container monitoring for {self.container_url}")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        try:
            while True:
                if not self.check_container():
                    self.consecutive_failures += 1
                    logger.warning(f"Container check failed. Consecutive failures: {self.consecutive_failures}")
                    
                    if self.consecutive_failures >= self.max_retries:
                        if not self.alert_sent:
                            self.send_failure_notification()
                    else:
                        # Wait a shorter time before retrying
                        logger.info(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                        continue
                
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user.")
        except Exception as e:
            logger.critical(f"Unexpected error: {str(e)}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Monitor Docker container status")
    parser.add_argument("url", help="URL endpoint to check container status")
    parser.add_argument("-i", "--interval", type=int, default=60, 
                        help="Check interval in seconds (default: 60)")
    parser.add_argument("-r", "--retries", type=int, default=3,
                        help="Number of retries before sending alert (default: 3)")
    parser.add_argument("-d", "--delay", type=int, default=5,
                        help="Seconds to wait between retries (default: 5)")
    
    args = parser.parse_args()
    
    monitor = DockerMonitor(
        container_url=args.url,
        check_interval=args.interval,
        max_retries=args.retries,
        retry_delay=args.delay
    )
    
    monitor.run()

if __name__ == "__main__":
    main()