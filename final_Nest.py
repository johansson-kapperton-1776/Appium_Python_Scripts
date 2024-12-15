import json
import time
import csv
from datetime import datetime
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
from appium import webdriver
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ThreadPoolExecutor

# Load device configurations from JSON file
with open("devices_config.json", "r") as file:
    devices = json.load(file)

# XPath Definitions
XPATH_TIMESTAMP = "//android.widget.TextView[@resource-id='com.nest.android:id/timeline_timestamp']"
XPATH_LIVE_CAMERA = "//android.view.ViewGroup[@resource-id='com.nest.android:id/camera_stream_view']/android.view.View"
XPATH_ERROR_TEXT = "//android.widget.TextView[@resource-id='com.nest.android:id/top_text_view']"
XPATH_BLUE_CONTAINER = "//android.widget.LinearLayout[@resource-id='com.nest.android:id/scroll_container_child']"
XPATH_TRY_AGAIN = "//android.widget.Button[@content-desc='Try Again']"
XPATH_PROGRESS_VIEW = "//android.view.View[@resource-id='com.nest.android:id/structure_progress_view']"
XPATH_SMALL_CAMERA_VIEW = "//android.view.ViewGroup[@resource-id='com.nest.android:id/space_camera']/android.view.View"
XPATH_NO_INTERNET = "//android.widget.TextView[@resource-id='com.nest.android:id/top_text_view']"
XPATH_BUFFERING = "//android.widget.ImageView[@content-desc='Loading']"

# Function to check if an element is present
def is_element_present(driver, xpath):
    try:
        driver.find_element(AppiumBy.XPATH, xpath)
        return True
    except NoSuchElementException:
        return False

# Function to fetch timestamp from the live stream UI
def get_timestamp(driver):
    try:
        timestamp_element = driver.find_element(AppiumBy.XPATH, XPATH_TIMESTAMP)
        return timestamp_element.text
    except NoSuchElementException:
        return None

# Function to handle reconnection attempts
def handle_reconnection(driver, device_name):
    while True:
        try:
            print(f"\033[93m[{device_name} RECONNECTING]\033[0m Clicking 'Try Again' button...")
            driver.find_element(AppiumBy.XPATH, XPATH_TRY_AGAIN).click()
            time.sleep(4)  # Wait for reconnection

            if is_element_present(driver, XPATH_PROGRESS_VIEW) and is_element_present(driver, XPATH_SMALL_CAMERA_VIEW):
                print(f"\033[94m[{device_name} RECONNECTED PARTIALLY]\033[0m Progress detected. Clicking small camera view...")
                driver.find_element(AppiumBy.XPATH, XPATH_SMALL_CAMERA_VIEW).click()
                return True
        except NoSuchElementException:
            print(f"\033[93m[{device_name} TRY AGAIN NOT FOUND]\033[0m Retrying in 4 seconds...")
            time.sleep(4)

# Monitor a single device
def monitor_device(device):
    options = UiAutomator2Options()
    options.platform_name = device["platformName"]
    options.platform_version = device["platformVersion"]
    options.device_name = device["deviceName"]
    options.udid = device["deviceUID"]
    options.app_package = device["appPackage"]
    options.app_activity = device["appActivity"]
    options.no_reset = device["noReset"]
    options.full_reset = device["fullReset"]

    log_file = f"{device['deviceUniqueId']}_disconnect_log.csv"
    comprehensive_log = "comprehensive_log.txt"
    disconnect_start_time = None
    buffering_start_time = None
    live_stream_logged = False

    try:
        driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
        print(f"Appium session started for {device['deviceName']}. Monitoring live stream...")

        with open(log_file, mode="w", newline="") as file, open(comprehensive_log, "a") as report:
            writer = csv.writer(file)
            writer.writerow(["Device", "Event", "Start Time", "End Time", "Duration (seconds)"])
            file.flush()

            while True:
                timestamp = get_timestamp(driver)
                live_camera_present = is_element_present(driver, XPATH_LIVE_CAMERA)
                buffering_present = is_element_present(driver, XPATH_BUFFERING)
                error_text_present = is_element_present(driver, XPATH_ERROR_TEXT)
                blue_container_present = is_element_present(driver, XPATH_BLUE_CONTAINER)
                no_internet_present = is_element_present(driver, XPATH_NO_INTERNET)

                # Detect Buffering
                if buffering_present:
                    if buffering_start_time is None:
                        buffering_start_time = datetime.now()
                        log_message = f"\033[93m[{device['deviceName']} BUFFERING]\033[0m Started at {buffering_start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        print(log_message)
                        report.write(log_message + "\n")
                        report.flush()
                elif buffering_start_time:
                    buffering_end_time = datetime.now()
                    buffering_duration = (buffering_end_time - buffering_start_time).total_seconds()
                    log_message = f"\033[92m[{device['deviceName']} BUFFERING ENDED]\033[0m Ended at {buffering_end_time.strftime('%Y-%m-%d %H:%M:%S')} - Duration: {buffering_duration:.2f} seconds"
                    print(log_message)
                    report.write(log_message + "\n")
                    writer.writerow([device["deviceName"], "Buffering", buffering_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                     buffering_end_time.strftime('%Y-%m-%d %H:%M:%S'), buffering_duration])
                    file.flush()
                    buffering_start_time = None

                # Detect Disconnection
                if error_text_present or blue_container_present or no_internet_present:
                    if disconnect_start_time is None:
                        disconnect_start_time = datetime.now()
                        log_message = f"\033[91m[{device['deviceName']} DISCONNECTED]\033[0m {disconnect_start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        print(log_message)
                        report.write(log_message + "\n")
                        report.flush()

                    if is_element_present(driver, XPATH_TRY_AGAIN):
                        success = handle_reconnection(driver, device["deviceName"])
                        if success:
                            reconnect_time = datetime.now()
                            duration = (reconnect_time - disconnect_start_time).total_seconds()
                            log_message = f"\033[92m[{device['deviceName']} RECONNECTED]\033[0m Reconnected after {duration:.2f} seconds."
                            print(log_message)
                            report.write(log_message + "\n")
                            writer.writerow([device["deviceName"], "Disconnection", disconnect_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                             reconnect_time.strftime('%Y-%m-%d %H:%M:%S'), duration])
                            file.flush()
                            disconnect_start_time = None

                # Log Live Stream
                elif timestamp and live_camera_present and not live_stream_logged:
                    log_message = f"\033[92m[{device['deviceName']} LIVE STREAM]\033[0m Timestamp: {timestamp} - Actively monitoring."
                    print(log_message)
                    report.write(log_message + "\n")
                    report.flush()
                    live_stream_logged = True

                time.sleep(1)

    except KeyboardInterrupt:
        print(f"\nMonitoring stopped for {device['deviceName']}. Log saved to {log_file}.")
    finally:
        driver.quit()

# Run monitoring for all devices concurrently
def monitor_all_devices(devices):
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        executor.map(monitor_device, devices)

# Run the script
monitor_all_devices(devices)
