import paramiko
import time
from datetime import datetime

# SSH credentials
host = '192.168.3.1'
username = 'engineer'
password = 'gf123'

# Create an SSH client
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Log file path
log_file_path = 'wlanconfig_output_log.txt'

try:
    # Connect to the router
    ssh_client.connect(host, username=username, password=password)
    print(f"Connected to {host}")

    while True:
        # Run the command
        stdin, stdout, stderr = ssh_client.exec_command('wlanconfig ath2 list sta')

        # Get the command output
        output = stdout.read().decode()

        # Get the current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Log the output to a file
        with open(log_file_path, 'a') as log_file:
            log_file.write(f"[{timestamp}] Command output:\n{output}\n")

        print(f"[{timestamp}] Command output:\n{output}")

        # Wait for 30 seconds
        time.sleep(300)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the SSH connection
    ssh_client.close()
    print("SSH connection closed.")
