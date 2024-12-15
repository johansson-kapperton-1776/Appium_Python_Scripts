import json
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from datetime import datetime, timezone, timedelta


# Function to convert timestamp to EST time format
def format_timestamp(timestamp):
    est = timezone(timedelta(hours=-5))  # EST offset
    dt = datetime.fromtimestamp(timestamp, tz=est)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds


# Load device configuration
with open('device_config.json', 'r') as config_file:
    device_config = json.load(config_file)


# Function to clean strings for text file compatibility
def clean_text(text):
    return ''.join(c for c in text if c.isalnum() or c in ' .,_-')


# Function to save data to text files
def save_to_txt(device_name, stats_data, buffering_intervals):
    # Save Stats Data
    stats_file_path = f"{device_name}_stats_log.txt"
    with open(stats_file_path, 'w') as stats_file:
        stats_file.write(f"Stats Log for {device_name}:\n")
        stats_file.write("-" * 50 + "\n")
        for entry in stats_data:
            stats_file.write(f"{entry}\n")
    print(f"Stats log saved to {stats_file_path}")

    # Save Buffering Data
    buffering_file_path = f"{device_name}_buffer_log.txt"
    with open(buffering_file_path, 'w') as buffer_file:
        buffer_file.write(f"Buffering Log for {device_name}:\n")
        buffer_file.write("-" * 50 + "\n")
        for interval in buffering_intervals:
            buffer_file.write(f"{interval}\n")
    print(f"Buffering log saved to {buffering_file_path}")


# Function to run the test on a single device
def run_test(device):
    # Appium driver setup
    options = UiAutomator2Options()
    options.platform_name = device["platform_name"]
    options.platform_version = device["platform_version"]
    options.device_name = device["device_name"]
    options.udid = device["udid"]
    options.app_package = device["app_package"]
    options.app_activity = device["app_activity"]
    options.no_reset = device["no_reset"]

    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)

    stats_data = []
    buffering_intervals = []

    try:
        print(f"Starting test on {device['device_name']}...")
        print("Monitoring for buffering...")

        buffering = False
        buffer_start, buffer_end = None, None

        # Open log files for appending
        buffer_log_path = f"{device['device_name']}_buffer_log.txt"
        stats_log_path = f"{device['device_name']}_stats_log.txt"
        with open(buffer_log_path, 'w') as buffer_log, open(stats_log_path, 'w') as stats_log:
            buffer_log.write(f"Buffering Log for {device['device_name']}:\n")
            buffer_log.write("-" * 50 + "\n")

            stats_log.write(f"Stats Log for {device['device_name']}:\n")
            stats_log.write("-" * 50 + "\n")

            while True:  # Infinite loop
                try:
                    # Detect buffering
                    buffer_element = driver.find_element(
                        By.XPATH,
                        "//android.widget.ProgressBar[@resource-id='com.google.android.youtube:id/player_loading_view_thin']"
                    )
                    if buffer_element.is_displayed():
                        if not buffering:
                            buffer_start = time.time()
                            print(f"Buffering started at {format_timestamp(buffer_start)}...")
                            buffer_log.write(f"Buffering started at {format_timestamp(buffer_start)}...\n")
                            buffering = True

                        # Capture stats during buffering
                        stats = {
                            "timestamp": format_timestamp(time.time()),
                            "device_info": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/device_info']").text),
                            "scpn": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/scpn']").text),
                            "video_format": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/video_format']").text),
                            "bandwidth": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/bandwidth_estimate']").text),
                            "readahead": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/readahead']").text),
                            "viewport": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/viewport']").text),
                            "dropped_frames": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/dropped_frames']").text),
                            "latency": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/latency']").text)
                        }
                        buffer_log.write(f"During buffering: {stats}\n")
                except:
                    # If buffering ends
                    if buffering:
                        buffer_end = time.time()
                        buffer_duration = buffer_end - buffer_start
                        buffering_intervals.append({
                            "start": format_timestamp(buffer_start),
                            "end": format_timestamp(buffer_end),
                            "duration (s)": round(buffer_duration, 2)
                        })
                        print(f"Buffering ended at {format_timestamp(buffer_end)}. Duration: {buffer_duration:.2f} seconds")
                        buffer_log.write(f"Buffering ended at {format_timestamp(buffer_end)}. Duration: {buffer_duration:.2f} seconds\n")
                        buffering = False

                # Capture overall stats (outside buffering)
                try:
                    stats = {
                        "timestamp": format_timestamp(time.time()),
                        "device_info": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/device_info']").text),
                        "scpn": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/scpn']").text),
                        "video_format": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/video_format']").text),
                        "bandwidth": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/bandwidth_estimate']").text),
                        "readahead": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/readahead']").text),
                        "viewport": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/viewport']").text),
                        "dropped_frames": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/dropped_frames']").text),
                        "latency": clean_text(driver.find_element(By.XPATH, "//android.widget.TextView[@resource-id='com.google.android.youtube:id/latency']").text)
                    }
                    stats_data.append(stats)
                    stats_log.write(f"{stats}\n")
                    print(f"Captured stats at {stats['timestamp']}: {stats}")
                except Exception as e:
                    print(f"Failed to capture stats: {e}")

                time.sleep(0.01)  # Polling interval

    except KeyboardInterrupt:
        print("Manual interruption detected. Saving data...")
    finally:
        save_to_txt(device['device_name'], stats_data, buffering_intervals)
        driver.quit()


# Run the test on each device in the configuration
for device in device_config["devices"]:
    run_test(device)
