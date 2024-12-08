import json
import logging
import os
import time
from datetime import datetime
import openpyxl
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load device configurations from a JSON file
with open('device_configs.json') as config_file:
    config_data = json.load(config_file)


def toggle_wifi(device_config, num_toggles):
    logging.info(f"Starting Wi-Fi automation on {device_config['deviceName']} with {num_toggles} toggles.")

    # Set up the Excel file for storing results
    excel_file_path = f"C:\\Users\\actio\\Documents\\SSID-RSSI-VALUES\\{device_config['deviceUniqueId']}_wifi_stats.xlsx"
    workbook, sheet = prepare_excel_file(excel_file_path)

    # Initialize the Appium driver with device configurations
    driver = initialize_driver(device_config)

    try:
        wifi_toggle = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.Switch[@content-desc='Wi-Fi']"))
        )

        for i in range(num_toggles):
            logging.info(f"Toggle {i + 1}/{num_toggles}: Turning Wi-Fi off.")
            wifi_toggle.click()
            time.sleep(2)  # Wait for Wi-Fi to turn off

            logging.info(f"Toggle {i + 1}/{num_toggles}: Turning Wi-Fi on.")
            wifi_toggle.click()
            time.sleep(20)  # Allow time for Wi-Fi to reconnect and stabilize

            ssid, connection_detail = fetch_connection_details(driver)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append([timestamp, ssid, connection_detail])
            logging.info(f"Recorded: {timestamp}, {ssid}, {connection_detail}")

            time.sleep(40)  # Additional sleep after each run to ensure stability and proper intervals

    except Exception as e:
        logging.error(f"Error occurred on {device_config['deviceName']}: {str(e)}")

    finally:
        workbook.save(excel_file_path)
        logging.info(f"Results saved to {excel_file_path}")
        driver.quit()


def prepare_excel_file(path):
    if os.path.exists(path):
        workbook = openpyxl.load_workbook(path)
    else:
        workbook = openpyxl.Workbook()
        workbook.active.append(["Timestamp", "SSID", "Connection Detail"])
    return workbook, workbook.active


def initialize_driver(config):
    options = UiAutomator2Options()
    options.platform_name = config['platformName']
    options.device_name = config['deviceName']
    options.udid = config['deviceUID']
    options.automation_name = 'UiAutomator2'
    options.app_package = config['appPackage']
    options.app_activity = config['appActivity']
    options.no_reset = True
    return webdriver.Remote("http://localhost:4723/wd/hub", options=options)


def fetch_connection_details(driver):
    ssid_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.XPATH,
                                        "//androidx.recyclerview.widget.RecyclerView[@resource-id='com.android.settings:id/connected_list']//android.widget.TextView[@resource-id='com.android.settings:id/title']"))
    )
    ssid = ssid_element.text if ssid_element else "N/A"
    detail_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (AppiumBy.XPATH, "//android.widget.TextView[@resource-id='com.android.settings:id/summary']"))
    )
    connection_detail = detail_element.text if detail_element else "N/A"
    return ssid, connection_detail


def main(num_toggles):
    with ThreadPoolExecutor(max_workers=len(config_data['devices'])) as executor:
        futures = [executor.submit(toggle_wifi, device, num_toggles) for device in config_data['devices']]
        for future in as_completed(futures):
            if future.exception() is not None:
                logging.error(f"Error occurred: {future.exception()}")
            else:
                logging.info("Task completed successfully.")


if __name__ == "__main__":
    num_toggles = int(input("Enter the number of Wi-Fi toggles: "))
    main(num_toggles)

