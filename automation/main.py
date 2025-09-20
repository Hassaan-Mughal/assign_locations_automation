import sys
import os
import time
import logging
import requests
import shutil
from selenium.webdriver.common.by import By
from Utils.utils import *
from Utils.drive_uploader import authenticate, get_folder_id, upload_or_update_file
from Utils.functions import login_to_enrollware_and_navigate_to_settings_users

# Ensure the parent directory is in sys.path for reliable imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

class CreateUsersBackup:
    def __init__(self):
        self.driver = None

    def initialize(self) -> bool:
        try:
            self.driver = get_undetected_driver()
            if self.driver:
                logger.info("Chrome driver initialized successfully")
                return True
            else:
                logger.error("Failed to initialize Chrome driver")
                return False
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Resources cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

def main():
    tu_elements_urls = []
    url = "https://www.enrollware.com/admin/tc-user-list.aspx"
    processor = CreateUsersBackup()
    try:
        if not processor.initialize():
            return
        if not login_to_enrollware_and_navigate_to_settings_users(processor.driver):
            return
        # Authenticate Google Drive and get root folder
        drive_service = authenticate()
        root_folder_id = get_folder_id(drive_service, "Instructor Files")
        downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Instructor Files")
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir, exist_ok=True)
        total_user_selector = "//td/a[contains(@href, 'user-edit')]"
        total_user_elements = processor.driver.find_elements(By.XPATH, total_user_selector)
        for tu_element in total_user_elements:
            tu_elements_urls.append(tu_element.get_attribute("href"))
        for user_url in tu_elements_urls:
            try:
                processor.driver.get(user_url)
                time.sleep(1)
                user_name = get_element_attribute(processor.driver, (By.ID, "mainContent_username"), "value").strip()
                # Ensure local and Drive folder for user
                owner_folder = os.path.join(downloads_dir, user_name)
                if not os.path.exists(owner_folder):
                    os.makedirs(owner_folder, exist_ok=True)
                owner_drive_id = get_folder_id(drive_service, user_name, root_folder_id)
                links = processor.driver.find_elements(By.XPATH, "//a[@title= 'View']")
                if not links:
                    logger.info(f"No files found for user: {user_name}")
                    continue
                for link in links:
                    file_url = link.get_attribute("href")
                    file_name = link.text.strip()
                    if file_url and file_name:
                        local_path = os.path.join(owner_folder, file_name)
                        # Additional check: skip if file already exists locally
                        if os.path.exists(local_path):
                            logger.info(f"File already exists locally, skipping: {local_path}")
                            continue
                        # Download file immediately
                        try:
                            response = requests.get(file_url, stream=True)
                            if response.status_code == 200:
                                with open(local_path, "wb") as f:
                                    shutil.copyfileobj(response.raw, f)
                                logger.info(f"Downloaded: {local_path}")
                                # Upload to Google Drive immediately
                                upload_or_update_file(drive_service, owner_drive_id, local_path, file_name)
                            else:
                                logger.error(f"Failed to download {file_url}")
                        except Exception as e:
                            logger.error(f"Exception downloading/uploading {file_url}: {e}")
            except Exception as e:
                safe_navigate_to_url(processor.driver, url)
                time.sleep(2)
        processor.cleanup()
        print("\nAll files processed and backed up locally and to Google Drive.\n")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
    finally:
        if 'processor' in locals():
            processor.cleanup()

if __name__ == "__main__":
    main()
