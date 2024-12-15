import json
import logging
import time
from datetime import datetime
import openpyxl
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load device configurations from a JSON file
with open('device_configs.json') as config_file:
    devices = json.load(config_file)

# XPath definitions
XPATH_CONNECTED_NETWORK = "//android.widget.TextView[@resource-id='com.android.settings:id/connected_network_category']"
XPATH_CONNECTED_SSID = "//android.widget.TextView[@resource-id='com.android.settings:id/title' and @text='Ahomewifi']"
XPATH_CONNECTED_STATS = "//android.widget.TextView[@resource-id='com.android.settings:id/summary' and contains(@text,'Connected')]"
XPATH_DISCONNECTED_NETWORK = "//android.widget.TextView[@resource-id='com.android.settings:id/available_network_category']"
XPATH_DISCONNECTED_STATS = "//android.widget.TextView[@resource-id='com.android.settings:id/summary' and contains(@text,'Auto reconnect turned off')]"
XPATH_WIFI_TITLE = "//android.widget.TextView[@resource-id='com.android.settings:id/collapsing_appbar_extended_title']"

# Bounds for Wi-Fi title per device
DEVICE_BOUNDS = {
    "default": [0, 383, 1080, 514],
    "Galaxy S8 Tab": [854, 122, 960, 184]
}

def initialize_driver(config):
    """Initializes Appium driver."""
    options = UiAutomator2Options()
    options.platform_name = config['platformName']
    options.device_name = config['deviceName']
    options.udid = config['deviceUID']
    options.automation_name = 'UiAutomator2'
    options.no_reset = True

    return webdriver.Remote("http://localhost:4723/wd/hub", options=options)

def prepare_excel_file(device_name):
    """Prepares an Excel file for logging."""
    file_path = f"{device_name}_wifi_log.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Wi-Fi Events"
    sheet.append(["Timestamp", "Event", "Details"])
    workbook.save(file_path)
    return file_path

def log_event_to_excel(file_path, event, details):
    """Logs an event to the Excel file."""
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    sheet.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event, details])
    workbook.save(file_path)

def keep_device_awake(driver, device_name):
    """Periodically taps the Wi-Fi title to keep the device awake."""
    bounds = DEVICE_BOUNDS.get(device_name, DEVICE_BOUNDS["default"])
    x = (bounds[0] + bounds[2]) // 2
    y = (bounds[1] + bounds[3]) // 2

    while True:
        try:
            logging.info(f"[{device_name}] Tapping on Wi-Fi title to keep the device awake.")
            driver.tap([(x, y)])  # Tap on the center of the Wi-Fi title
            time.sleep(300)  # Wait for 5 minutes before the next tap
        except Exception as e:
            logging.error(f"Error while keeping device awake for {device_name}: {e}")
            break

def check_wifi_status(driver, device_config):
    """Continuously checks the Wi-Fi connection status."""
    device_name = device_config['deviceName']
    file_path = prepare_excel_file(device_name)
    disconnect_start_time = None

    try:
        while True:
            connected_network_present = is_element_present(driver, XPATH_CONNECTED_NETWORK)
            connected_ssid_present = is_element_present(driver, XPATH_CONNECTED_SSID)
            connected_stats_present = is_element_present(driver, XPATH_CONNECTED_STATS)

            if connected_network_present and connected_ssid_present and connected_stats_present:
                if disconnect_start_time:
                    disconnect_duration = (datetime.now() - disconnect_start_time).total_seconds()
                    log_message = f"[{device_name}] Reconnected after {disconnect_duration:.2f} seconds."
                    logging.info(log_message)
                    log_event_to_excel(file_path, "Reconnected", f"Duration: {disconnect_duration:.2f} seconds")
                    disconnect_start_time = None

                ssid = driver.find_element(AppiumBy.XPATH, XPATH_CONNECTED_SSID).text
                stats = driver.find_element(AppiumBy.XPATH, XPATH_CONNECTED_STATS).text
                logging.info(f"[{device_name}] Wi-Fi Connected: SSID = {ssid}, Stats = {stats}")
            else:
                disconnected_network_present = is_element_present(driver, XPATH_DISCONNECTED_NETWORK)
                disconnected_stats_present = is_element_present(driver, XPATH_DISCONNECTED_STATS)

                if disconnected_network_present and disconnected_stats_present:
                    if disconnect_start_time is None:
                        disconnect_start_time = datetime.now()
                        log_message = f"[{device_name}] Wi-Fi Disconnected at {disconnect_start_time.strftime('%Y-%m-%d %H:%M:%S')}."
                        logging.warning(log_message)
                        log_event_to_excel(file_path, "Disconnected", "Wi-Fi disconnected")
                else:
                    logging.warning(f"[{device_name}] Unable to detect Wi-Fi stats. Retrying...")
            time.sleep(3)  # Check every 3 seconds
    except KeyboardInterrupt:
        logging.info(f"Monitoring stopped for {device_name}.")
        if disconnect_start_time:
            disconnect_duration = (datetime.now() - disconnect_start_time).total_seconds()
            log_event_to_excel(file_path, "Disconnected (Incomplete)", f"Duration: {disconnect_duration:.2f} seconds")
    finally:
        driver.quit()

def is_element_present(driver, xpath):
    """Checks if an element is present on the screen."""
    try:
        driver.find_element(AppiumBy.XPATH, xpath)
        return True
    except NoSuchElementException:
        return False

def monitor_device(device_config):
    """Monitors Wi-Fi status for a single device."""
    driver = initialize_driver(device_config)

    # Run keep_device_awake in a separate thread
    ThreadPoolExecutor(max_workers=1).submit(keep_device_awake, driver, device_config['deviceName'])

    check_wifi_status(driver, device_config)

def monitor_all_devices():
    """Monitors Wi-Fi status for all devices concurrently."""
    with ThreadPoolExecutor(max_workers=len(devices['devices'])) as executor:
        futures = [executor.submit(monitor_device, device) for device in devices['devices']]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error occurred: {e}")

if __name__ == "__main__":
    monitor_all_devices()
