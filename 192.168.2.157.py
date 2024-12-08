import subprocess
import time
from datetime import datetime


def monitor_extender():
    host = '192.168.2.157'
    username = 'root'
    command = 'wlanconfig ath1 list sta'
    log_file_path = 'wlanconfig_output_192_168_2_157_log.txt'

    while True:
        try:
            # Use subprocess to run the SSH command
            result = subprocess.run(
                ['ssh', f'{username}@{host}', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                input='yes\n'  # Automatically answer 'yes' for first-time connections
            )

            output = result.stdout
            error = result.stderr

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Log the output to a file
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"[{timestamp}] Command output from {host}:\n{output}\n")
                if error:
                    log_file.write(f"[{timestamp}] Error output from {host}:\n{error}\n")

            print(f"[{timestamp}] Command output from {host}:\n{output}")
            if error:
                print(f"[{timestamp}] Error output from {host}:\n{error}")

        except Exception as e:
            print(f"An error occurred: {e}")

        # Wait for 5 minutes (300 seconds)
        time.sleep(300)


if __name__ == "__main__":
    monitor_extender()
