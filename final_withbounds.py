import os
import json
import time
import openpyxl
from datetime import datetime
from subprocess import check_output, CalledProcessError
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load device configurations from JSON file
def load_device_config():
    """Load device configurations from a JSON file."""
    with open("device_config.json", "r") as file:
        return json.load(file)["devices"]

# Get list of connected devices
def get_connected_devices():
    """Get a list of connected devices using ADB."""
    try:
        result = check_output("adb devices", shell=True).decode("utf-8")
        devices = [line.split()[0] for line in result.splitlines() if "device" in line and "List" not in line]
        return devices
    except CalledProcessError as e:
        print(f"Error fetching connected devices: {e}")
        return []

# Ensure the correct device is connected and available
def ensure_device(device_uid):
    """Ensure the specified device is connected."""
    connected_devices = get_connected_devices()
    if device_uid not in connected_devices:
        raise Exception(f"Device {device_uid} not found. Connected devices: {connected_devices}")
    print(f"Device {device_uid} is connected and ready.")

# Initialize Excel workbook to store results
def setup_excel(folder_path, device_name):
    """Set up an Excel workbook to store download speed results."""
    device_folder = os.path.join(folder_path, device_name)
    if not os.path.exists(device_folder):
        os.makedirs(device_folder)
    excel_file_path = os.path.join(device_folder, f"{device_name}_asphalt9_speeds.xlsx")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Download Speeds"
    sheet.append(["Attempt", "Timestamp", "Download Speed (Mbps)", "Total Time (min:sec)"])
    return excel_file_path, workbook, sheet

# Retry function with logging
def log_and_retry(action, max_retries=3):
    """Retry a specified action with logging for failures."""
    for attempt in range(max_retries):
        try:
            return action()
        except NoSuchElementException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    raise Exception(f"Action failed after {max_retries} retries.")

# Click on the search tab
def click_search_tab(driver):
    """Click on the search tab in the Google Play Store."""
    search_xpaths = ["//android.widget.TextView[@text='Search']"]
    for xpath in search_xpaths:
        try:
            log_and_retry(lambda: driver.find_element(By.XPATH, xpath).click())
            return
        except Exception:
            pass
    raise Exception("Failed to click the search tab.")

# Monitor the download progress
def monitor_download_progress(driver):
    """Monitor the download progress and print updates in real-time."""
    last_progress = None
    while True:
        try:
            progress_tracker = driver.find_element(By.XPATH, "//android.view.View[contains(@content-desc, '%')]")
            progress_text = progress_tracker.get_attribute("content-desc")
            if progress_text != last_progress:
                print(f"Current progress: {progress_text}")
                last_progress = progress_text
            if "100%" in progress_text:
                print("Download completed!")
                break
        except NoSuchElementException:
            print("Progress tracker not found, waiting...")
        time.sleep(0.1)

# Search and install the app
def search_and_install_app(driver):
    """Search for the specified app in the Google Play Store and initiate installation."""
    try:
        print("Clicking on the search tab at the bottom...")
        click_search_tab(driver)

        search_bar = log_and_retry(lambda: WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//android.view.View[@content-desc='Search Google Play']"))
        ))
        search_bar.click()

        search_box = log_and_retry(lambda: WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//android.widget.EditText"))
        ))
        search_box.click()
        search_box.send_keys("Asphalt 9: Legends")
        driver.press_keycode(66)  # Press 'Enter'

        install_button = log_and_retry(lambda: WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "(//android.widget.TextView[@content-desc='Install'])[2]"))
        ))
        install_button.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//android.view.View[contains(@content-desc, '%')]"))
        )
        print("Download started...")
        start_time = time.time()

        monitor_download_progress(driver)

        end_time = time.time()
        download_time = end_time - start_time
        total_time = divmod(download_time, 60)
        print(f"Download time: {int(total_time[0])} min {int(total_time[1])} sec")
        speed = (3220 * 8) / download_time
        return speed, f"{int(total_time[0])}:{int(total_time[1]):02d}"

    except Exception as e:
        print(f"Error during search and install: {e}")
        return None, None

# Uninstall the app with dynamic XPath and bounds handling
def uninstall_app(driver, device_name):
    """Uninstall the specified app with dynamic XPath and bounds handling."""
    try:
        if device_name in ["Galaxy S22 Ultra", "Galaxy A54", "Galaxy S8 Tab", "Galaxy S22"]:
            print("Waiting longer for installation to stabilize...")
            time.sleep(60)
        else:
            time.sleep(30)

        # Define XPaths and bounds for devices
        xpaths_and_bounds = {
            "Galaxy S22 Ultra": [
                ("//android.view.View[@content-desc='Asphalt Legends Unite Installed ']", [271, 1210, 809, 1327]),
                ("//androidx.compose.ui.platform.ComposeView[@resource-id='com.android.vending:id/0_resource_name_obfuscated']/android.view.View/android.view.View[1]/android.view.View[1]/android.view.View[3]", [271, 865, 801, 994])
            ],
            "Galaxy A54": [
                ("//android.view.View[@content-desc='Asphalt Legends Unite Installed ']", [271, 865, 801, 994]),
                ("//androidx.compose.ui.platform.ComposeView[@resource-id='com.android.vending:id/0_resource_name_obfuscated']/android.view.View/android.view.View[1]/android.view.View[1]/android.view.View[3]", [271, 865, 801, 994])
            ],
            "Galaxy S8 Tab": [
                ("//android.view.View[@content-desc='Asphalt Legends Unite Installed ']", [213, 758, 1530, 846]),
                ("//androidx.compose.ui.platform.ComposeView[@resource-id='com.android.vending:id/0_resource_name_obfuscated']/android.view.View/android.view.View[1]/android.view.View[1]/android.view.View[3]", [213, 758, 1530, 846])
            ],
            "Galaxy S22": [
                ("//android.view.View[@content-desc='Asphalt Legends Unite Installed ']", [240, 895, 828, 1019]),
                ("//androidx.compose.ui.platform.ComposeView[@resource-id='com.android.vending:id/0_resource_name_obfuscated']/android.view.View/android.view.View[1]/android.view.View[1]/android.view.View[3]", [240, 895, 828, 1019])
            ]
        }

        device_xpaths_and_bounds = xpaths_and_bounds.get(device_name, [])

        for xpath, bounds in device_xpaths_and_bounds:
            print(f"Trying XPath: {xpath} for {device_name}")
            try:
                element = log_and_retry(lambda: driver.find_element(By.XPATH, xpath), max_retries=2)
                # Tap on the provided bounds
                x_center = bounds[0] + (bounds[2] - bounds[0]) // 2
                y_top = bounds[1] + 10
                driver.tap([(x_center, y_top)])
                print(f"Successfully tapped bounds for XPath: {xpath}")
                break
            except Exception as e:
                print(f"Failed for XPath: {xpath}. Error: {e}")

        # Click the uninstall button
        uninstall_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                "//androidx.compose.ui.platform.ComposeView[@resource-id='com.android.vending:id/0_resource_name_obfuscated']/android.view.View/android.view.View[1]/android.view.View[1]/android.view.View[2]/android.widget.Button"))
        )
        uninstall_button.click()

        confirm_uninstall_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                "//android.view.ViewGroup/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View/android.view.View[2]/android.widget.Button"))
        )
        confirm_uninstall_button.click()
        print(f"App successfully uninstalled on {device_name}.")
    except Exception as e:
        print(f"Error during uninstall on {device_name}: {e}")

# Main script
def main():
    """Main function to execute the testing process."""
    folder_path = "C:\\GooglePlayDL_speed_results"
    devices = load_device_config()
    attempts = int(input("Enter the number of download attempts per device: "))

    for device in devices:
        ensure_device(device["deviceUID"])
        print(f"Testing on device: {device['deviceName']} ({device['deviceUID']})")
        excel_file_path, workbook, sheet = setup_excel(folder_path, device["deviceName"])
        options = UiAutomator2Options()
        options.platform_name = device["platformName"]
        options.device_name = device["deviceName"]
        options.udid = device["deviceUID"]
        options.app_package = "com.android.vending"
        options.app_activity = "com.android.vending.AssetBrowserActivity"
        options.no_reset = device["noReset"]
        options.new_command_timeout = 300

        driver = webdriver.Remote("http://localhost:4723/wd/hub", options=options)

        for i in range(attempts):
            print(f"Starting attempt {i + 1} on {device['deviceName']}...")
            speed, total_time = search_and_install_app(driver)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if speed:
                print(f"Attempt {i + 1} on {device['deviceUID']}: {speed:.2f} Mbps")
                sheet.append([i + 1, timestamp, speed, total_time])
                uninstall_app(driver, device["deviceName"])
            else:
                print(f"Attempt {i + 1} on {device['deviceUID']} failed.")

        driver.quit()
        workbook.save(excel_file_path)
        print(f"Results saved to {excel_file_path}")

if __name__ == "__main__":
    main()
