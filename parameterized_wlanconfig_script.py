import paramiko
import threading
import time
from datetime import datetime


def monitor_device(host, username, command, log_file_path):
    try:
        # Use paramiko's Transport object to create a connection
        transport = paramiko.Transport((host, 22))  # Port 22 is standard for SSH

        # Connect to the host without a password
        transport.connect(username=username)

        # Create an SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client._transport = transport

        print(f"Connected to {host}")

        while True:
            # Run the command
            stdin, stdout, stderr = ssh_client.exec_command(command)
            output = stdout.read().decode()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Log the output to a file
            with open(log_file_path, 'a') as log_file:
                log_file.write(f"[{timestamp}] Command output from {host}:\n{output}\n")

            print(f"[{timestamp}] Command output from {host}:\n{output}")

            # Wait for 5 minutes (300 seconds)
            time.sleep(300)

    except paramiko.AuthenticationException as auth_err:
        print(f"Authentication failed for {host}: {auth_err}")

    except Exception as e:
        print(f"An error occurred on {host}: {e}")

    finally:
        # Close the SSH connection
        transport.close()
        print(f"SSH connection to {host} closed.")


def main():
    # User-friendly menu for selecting router
    print("Select the router to test:")
    print("1: 192.168.3.1")
    print("2: 192.168.2.1")

    router_choice = input("Enter the number corresponding to the router (1 or 2): ")

    if router_choice == '1':
        router_host = '192.168.3.1'
        router_username = 'engineer'
        router_command = 'wlanconfig ath2 list sta'
        extenders = ['192.168.3.106']
    elif router_choice == '2':
        router_host = '192.168.2.1'
        router_username = 'root'
        router_command = 'wlanconfig ath1 list sta'
        extenders = ['192.168.2.157', '192.168.2.102']
    else:
        print("Invalid choice. Please enter 1 or 2.")
        return

    # Log file paths
    router_log_file_path = f'wlanconfig_output_{router_host.replace(".", "_")}_log.txt'
    extender_log_files = [f'wlanconfig_output_{ext.replace(".", "_")}_log.txt' for ext in extenders]

    # Start thread for router
    router_thread = threading.Thread(target=monitor_device, args=(router_host, router_username, router_command, router_log_file_path))
    router_thread.start()

    # Start threads for each extender
    extender_threads = []
    for i, extender in enumerate(extenders):
        extender_command = 'wlanconfig ath1 list sta'  # Assume extenders use the same command
        extender_thread = threading.Thread(target=monitor_device, args=(extender, 'root', extender_command, extender_log_files[i]))
        extender_threads.append(extender_thread)
        extender_thread.start()

    # Wait for all threads to complete
    router_thread.join()
    for thread in extender_threads:
        thread.join()


if __name__ == "__main__":
    main()
