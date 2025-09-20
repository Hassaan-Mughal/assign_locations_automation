from selenium.webdriver.common.by import By
from Utils.utils import *
from Utils.drive_uploader import process_files
from Utils.functions import login_to_enrollware_and_navigate_to_settings_users, create_templete



class CreateUsersBackup:
    def __init__(self):
        self.driver = None

    def initialize(self) -> bool:
        """Initialize the processor with safe exception handling."""
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
        """Safely cleanup resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Resources cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")


def main():
    url = "https://www.enrollware.com/admin/tc-user-list.aspx"
    processor = CreateUsersBackup()
    files_to_download = []
    owners = []
    try:
        if not processor.initialize():
            return
        if not login_to_enrollware_and_navigate_to_settings_users(processor.driver):
            return
        total_user_selector = "//td/a[contains(@href, 'user-edit')]"
        total_user_elements = processor.driver.find_elements(By.XPATH, total_user_selector)
        for i in range (1, len(total_user_elements) + 1):
            user_selector = f"({total_user_selector})[{i}]"
            try:
                click_element_by_js(processor.driver, (By.XPATH, user_selector))
                time.sleep(2)
                f_name = get_element_attribute(processor.driver, (By.ID, "mainContent_fname"), "value")
                l_name = get_element_attribute(processor.driver, (By.ID, "mainContent_lname"), "value")
                user_name = f_name.strip() + " " + l_name.strip()
                links = processor.driver.find_elements(By.XPATH, "//a[@title= 'View']")
                for link in links:
                    file_url = link.get_attribute("href")
                    file_name = link.text.strip()
                    if file_url and file_name:
                        files_to_download.append(create_templete(file_url, user_name, file_name))
                        if user_name not in owners:
                            owners.append(user_name)
                safe_navigate_to_url(processor.driver, url)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error processing user at index {i}: {e}")
                safe_navigate_to_url(processor.driver, url)
                time.sleep(2)
        processor.cleanup()
        if files_to_download and owners:
            process_files(files_to_download, owners)
        else:
            logger.info("No files to download or no owners found.")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")

    finally:
        if 'processor' in locals():
            processor.cleanup()

if __name__ == "__main__":
    main()
