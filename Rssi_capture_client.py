import json
import logging
import os
import time
from datetime import datetime
import openpyxl
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load device configurations from a JSON file
with open('device_configs.json') as config_file:
    config_data = json.load(config_file)


def record_rssi(device_config, interval):
    logging.info(f"Starting RSSI recording on {device_config['deviceName']} with {interval} second intervals.")

    # Set up the Excel file for storing RSSI values
    excel_file_path = f"C:\\Users\\QAthinkpad\\Documents\\RSSI_VALUES_Client\\{device_config['deviceUniqueId']}_rssi_stats.xlsx"
    workbook, sheet = prepare_excel_file(excel_file_path)

    # Initialize the Appium driver with device configurations
    driver = initialize_driver(device_config)

    try:
        while True:
            try:
                # Refresh the screen by scrolling downward
                refresh_screen(driver)

                # Wait 1 second for the screen to refresh
                time.sleep(1)

                # Fetch all visible data
                visible_data = fetch_visible_data(driver)

                # Extract and log only the RSSI value
                rssi = extract_rssi(visible_data)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f"Timestamp: {timestamp}, RSSI: {rssi}")

                # Write only the RSSI value to the Excel file (append "N/A" if not found)
                sheet.append([timestamp, rssi])

                # Wait for the specified interval
                time.sleep(max(0, interval - 1))  # Adjust for the 1-second delay after refresh

            except Exception as e:
                # Handle errors gracefully and continue
                logging.warning(f"Error encountered: {e}. Skipping this trial.")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append([timestamp, "N/A"])  # Append N/A for failed trials
                time.sleep(interval)  # Wait for the interval before retrying

            except KeyboardInterrupt:
                # Stop the script manually
                logging.info("Manual stop detected. Saving results and exiting...")
                break

    finally:
        workbook.save(excel_file_path)
        logging.info(f"RSSI values saved to {excel_file_path}")
        driver.quit()


def prepare_excel_file(path):
    if os.path.exists(path):
        workbook = openpyxl.load_workbook(path)
    else:
        workbook = openpyxl.Workbook()
        workbook.active.append(["Timestamp", "RSSI"])  # Only two columns: Timestamp and RSSI
    return workbook, workbook.active


def initialize_driver(config):
    options = UiAutomator2Options()
    options.platform_name = config['platformName']
    options.device_name = config['deviceName']
    options.udid = config['deviceUID']
    options.automation_name = 'UiAutomator2'
    options.no_reset = True
    return webdriver.Remote("http://localhost:4723/wd/hub", options=options)


def refresh_screen(driver):
    # Perform a downward swipe on the top half of the screen
    screen_size = driver.get_window_size()
    start_x = screen_size['width'] // 2
    start_y = screen_size['height'] // 4  # Start from the top quarter
    end_y = screen_size['height'] // 2    # Swipe to the middle
    driver.swipe(start_x=start_x, start_y=start_y, end_x=start_x, end_y=end_y, duration=500)
    logging.info("Screen refreshed.")


def fetch_visible_data(driver):
    """
    Fetch all visible text from the screen.
    """
    try:
        elements = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView")
        return [element.text for element in elements if element.text.strip()]
    except Exception as e:
        logging.warning(f"Error while fetching visible data: {e}")
        return []


def extract_rssi(visible_data):
    """
    Extract the RSSI value from the visible data.
    """
    for line in visible_data:
        if "rssi" in line.lower():  # Look for RSSI-related text
            parts = line.split("rssi =")
            if len(parts) > 1:
                return parts[1].split()[0].strip()  # Extract the RSSI value
    return "N/A"


# Prompt for interval in seconds
try:
    interval = int(input("Enter the interval in seconds for RSSI recording: "))
    if interval <= 0:
        raise ValueError("Interval must be a positive integer.")
except ValueError as e:
    logging.error(f"Invalid interval input: {e}. Defaulting to 5 seconds.")
    interval = 5  # Default interval if input is invalid

# Start RSSI recording for each device
for device in config_data['devices']:
    record_rssi(device, interval)
