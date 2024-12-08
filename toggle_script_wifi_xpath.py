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

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load device configurations
with open('device_configs.json') as config_file:
    config_data = json.load(config_file)


def toggle_wifi(device_config, num_toggles):
    logging.info(f"Starting Wi-Fi automation on {device_config['deviceName']} with {num_toggles} toggles.")

    # Excel file setup
    excel_file_path = f"C:\\Users\\actio\\Documents\\SSID-RSSI-VALUES\\{device_config['deviceUniqueId']}_wifi_stats.xlsx"
    if os.path.exists(excel_file_path):
        workbook = openpyxl.load_workbook(excel_file_path)
        sheet = workbook.active
    else:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Timestamp", "SSID", "Wi-Fi Status"])

    # Initialize the Appium driver
    options = UiAutomator2Options()
    options.platform_name = device_config['platformName']
    options.device_name = device_config['deviceName']
    options.udid = device_config['deviceUID']
    options.automation_name = 'UiAutomator2'
    options.app_package = device_config['appPackage']
    options.app_activity = device_config['appActivity']
    options.no_reset = True
    driver = webdriver.Remote("http://localhost:4723/wd/hub", options=options)

    try:
        wifi_toggle = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.XPATH, "//android.widget.Switch[@content-desc='Wi-Fi']"))
        )

        for i in range(num_toggles):
            logging.info(f"Toggle {i + 1}/{num_toggles}: Turning Wi-Fi off.")
            wifi_toggle.click()
            time.sleep(2)

            logging.info(f"Toggle {i + 1}/{num_toggles}: Turning Wi-Fi on.")
            wifi_toggle.click()
            time.sleep(20)  # Wait for connection to stabilize

            ssid_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((AppiumBy.XPATH, "//androidx.recyclerview.widget.RecyclerView[@resource-id='com.android.settings:id/connected_list']//android.widget.TextView[@resource-id='com.android.settings:id/title']"))
            )
            ssid = ssid_element.text if ssid_element else "N/A"
            wifi_status = "ON" if wifi_toggle.get_attribute("checked") == "true" else "OFF"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append([timestamp, ssid, wifi_status])
            logging.info(f"Recorded: {timestamp}, {ssid}, {wifi_status}")

    finally:
        workbook.save(excel_file_path)
        logging.info(f"Results saved to {excel_file_path}")
        driver.quit()


num_toggles = int(input("Enter the number of Wi-Fi toggles: "))
for device in config_data['devices']:
    toggle_wifi(device, num_toggles)
