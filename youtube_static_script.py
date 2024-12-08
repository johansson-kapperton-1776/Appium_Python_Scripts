import pytest
import random
import time
import subprocess
import pandas as pd
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Pytest fixture for setting up the Appium driver
@pytest.fixture(scope="module")
def driver():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.platform_version = "14"  # Ensure this matches your actual Android version
    options.device_name = "Galaxy A55"  # Make sure this matches the device name
    options.udid = "R5CX33PG3KA"  # Verify the UDID is correct
    options.app_package = "com.google.android.youtube"
    options.app_activity = "com.google.android.youtube.HomeActivity"
    options.no_reset = True

    try:
        # Debugging: Print the options to see the configuration
        print("Initializing Appium driver with options:", options)
        driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
        return driver
    except Exception as e:
        print(f"Error initializing Appium driver: {e}")
        pytest.fail(f"Failed to initialize Appium driver: {e}")


# Helper function to monitor network activity using adb
def monitor_network_activity():
    result = subprocess.check_output("adb shell cat /proc/net/dev", shell=True).decode('utf-8')
    print("Network activity:", result)
    return result


# Function to pause the video assuming it is playing
def pause_video(driver):
    """
    Function to pause the video directly.
    """
    try:
        # Tap on the video player to reveal the controls
        video_player = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "com.google.android.youtube:id/watch_player"))
        )
        video_player.click()
        time.sleep(0.1)  # Short wait to ensure controls are visible

        # Click the pause button directly
        pause_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Pause video']"))
        )
        pause_button.click()
        print("Video paused successfully.")
    except Exception as e:
        print(f"Failed to pause the video: {e}")


# Function to play the video
def play_video(driver):
    """
    Function to play the video directly after fetching time values.
    """
    try:
        # Tap on the video player to reveal the controls
        video_player = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "com.google.android.youtube:id/watch_player"))
        )
        video_player.click()
        time.sleep(0.1)  # Short wait to ensure controls are visible

        # Click the play button directly
        play_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Play video']"))
        )
        play_button.click()
        print("Video played successfully.")
    except Exception as e:
        print(f"Failed to play the video: {e}")


# Test function to perform YouTube search, play a video, and log network activity
def test_youtube_video_playback_and_resolution(driver):
    # Array of keywords
    keywords = ["4k video", "8k videos", "12k videos"]

    # Click on the search icon
    search_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ACCESSIBILITY_ID, "Search"))
    )
    search_icon.click()

    # Select a random keyword and enter it in the search bar
    selected_keyword = random.choice(keywords)
    search_bar = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "com.google.android.youtube:id/search_edit_text"))
    )
    search_bar.send_keys(selected_keyword)

    # Explicitly tap the "Enter" key using driver.press_keycode for mobile
    driver.press_keycode(66)  # Keycode 66 is for the "Enter" key on Android

    # Click on the first video
    first_video = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "(//android.view.ViewGroup[@content-desc])[2]"))
    )
    first_video.click()

    # Wait for the video to start playing
    time.sleep(5)

    # Pause the video to ensure controls are visible before clicking fullscreen
    pause_video(driver)

    # Click the fullscreen button
    fullscreen_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Enter fullscreen']"))
    )
    fullscreen_button.click()

    # Wait for a moment after entering fullscreen
    time.sleep(2)

    # Pause the video again to fetch time values
    pause_video(driver)

    # Initialize the start time for tracking
    start_time = time.time()

    # Fetch the current time and total time elements
    try:
        # Log the current time and total video length
        current_time_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "com.google.android.youtube:id/time_bar_current_time"))
        )
        total_time_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "com.google.android.youtube:id/time_bar_total_time"))
        )

        current_time = current_time_element.get_attribute("text")
        total_time = total_time_element.get_attribute("text")
        print(f"Current time: {current_time}")
        print(f"Total video length: {total_time}")
    except Exception as e:
        print(f"Failed to get time elements, Error: {e}")

    # Play the video again after fetching time values
    play_video(driver)

    end_time = time.time()
    total_time_playback = end_time - start_time
    print(f"Total video playback time: {total_time_playback} seconds")

    # Initialize data storage for network activity and buffering
    network_data = []
    buffer_times = []

    # Monitor playback and network activity
    video_complete = False
    while not video_complete:
        # Monitor network activity
        network_stats = monitor_network_activity()
        network_data.append(network_stats)

        # Check for buffering or ad elements
        try:
            current_time_element = driver.find_element(By.ID, "com.google.android.youtube:id/time_bar_current_time")
            current_time = current_time_element.get_attribute("text")
            if "elapsed" in current_time:
                video_complete = True
            time.sleep(10)
        except Exception as e:
            buffer_times.append(time.time())
            print("Buffering or ad detected")

    end_time = time.time()
    print(f"Total video playback time: {total_time} seconds")

    # Access settings and change to the highest resolution
    settings_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='More options']"))
    )
    settings_icon.click()

    quality_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//android.support.v7.widget.RecyclerView/android.view.ViewGroup[1]/android.widget.ImageView"))
    )
    quality_option.click()

    advanced_section = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//android.support.v7.widget.RecyclerView[@resource-id='com.google.android.youtube:id/bottom_sheet_list']/android.view.ViewGroup/android.view.ViewGroup[4]"))
    )
    advanced_section.click()

    highest_resolution_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH,
                                    "//android.support.v7.widget.RecyclerView[@resource-id='com.google.android.youtube:id/bottom_sheet_list']/android.view.ViewGroup/android.view.ViewGroup[1]"))
    )
    highest_resolution_option.click()

    # Export network data and buffering events to Excel
    df = pd.DataFrame({'Network Stats': network_data, 'Buffer Times': buffer_times})
    df.to_excel('test_report.xlsx', index=False)

    print("Test completed successfully and data exported to Excel!")
