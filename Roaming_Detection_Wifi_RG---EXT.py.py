import subprocess
import re
import time
from datetime import datetime
from collections import defaultdict
from openpyxl import Workbook

# Configuration
RG_IP = "192.168.1.1"
EXT_IP = "192.168.1.177"
RADIOS = ["ath0", "ath1", "ath2"]
MAC_ADDRESSES = ["1a:1e:36:da:66:b7", "06:7f:7f:50:16:fe"]
POLLING_INTERVAL = 1
OUTPUT_FILE = f"roaming_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

RADIO_FREQUENCIES = {"ath0": "2.4GHz", "ath1": "5GHz", "ath2": "6GHz"}

# Execute SSH command and fetch output
def ssh_execute(ip, command):
    try:
        result = subprocess.run(
            ["ssh", f"root@{ip}", command],
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception as e:
        print(f"Error executing SSH on {ip}: {e}")
        return ""


def parse_wlanconfig(output):
    clients = {}
    mac = None  # Current MAC address being processed
    lines = output.splitlines()

    for line in lines:
        # Skip lines that are clearly metadata, headers, or empty
        if ("ADDR" in line or "RSSI is combined" in line or "Minimum Tx Power" in line
                or "HT Capability" in line or "VHT Capability" in line
                or not line.strip()):
            continue

        # Split the line into fields
        fields = re.split(r"\s+", line.strip())

        # Check if it's a MAC address line (MAC + RSSI format expected)
        if len(fields) >= 8 and ":" in fields[0]:
            mac = fields[0]  # Extract MAC address
            rssi = fields[5]
            clients[mac] = {"RSSI": rssi, "Client_Count": fields[1]}  # Initialize client entry

        # Check for SNR line associated with the current MAC
        elif "SNR" in line and mac:
            match = re.search(r"SNR\s+:\s+(\d+)", line)
            if match:
                clients[mac]["SNR"] = match.group(1)

    return clients


# Save roaming events to Excel
def save_to_excel(roaming_events, roaming_counts, initial_states):
    workbook = Workbook()

    # Roaming Events Sheet
    sheet_events = workbook.active
    sheet_events.title = "Roaming Events"
    event_headers = [
        "Timestamp",
        "MAC Address",
        "From AP -> To AP",
        "From Radio -> To Radio",
        "From Frequency -> To Frequency",
        "RSSI Before Roam",
        "RSSI After Roam",
        "SNR Before Roam",
        "SNR After Roam",
    ]
    sheet_events.append(event_headers)
    for event in roaming_events:
        sheet_events.append([
            event["timestamp"],
            event["mac"],
            f"{event['from_device']} -> {event['to_device']}",
            f"{event['from_radio']} -> {event['to_radio']}",
            f"{event['from_frequency']} -> {event['to_frequency']}",
            event["rssi_before"],
            event["rssi_after"],
            event.get("snr_before", "N/A"),
            event.get("snr_after", "N/A"),
        ])

    # Roaming Summary Sheet
    sheet_summary = workbook.create_sheet(title="Summary")
    summary_headers = [
        "MAC Address",
        "RG -> EXT (2.4GHz)",
        "RG -> EXT (5GHz)",
        "RG -> EXT (6GHz)",
        "EXT -> RG (2.4GHz)",
        "EXT -> RG (5GHz)",
        "EXT -> RG (6GHz)",
        "Total Roaming Events",
        "Initial State (AP, Radio, Freq)",
    ]
    sheet_summary.append(summary_headers)

    for mac, counts in roaming_counts.items():
        initial_state = initial_states.get(mac, "N/A")
        sheet_summary.append([
            mac,
            counts["RG -> EXT"]["2.4GHz"],
            counts["RG -> EXT"]["5GHz"],
            counts["RG -> EXT"]["6GHz"],
            counts["EXT -> RG"]["2.4GHz"],
            counts["EXT -> RG"]["5GHz"],
            counts["EXT -> RG"]["6GHz"],
            counts["total"],
            initial_state,
        ])

    workbook.save(OUTPUT_FILE)
    print(f"Report saved to {OUTPUT_FILE}")


# Main function
def main():
    roaming_events = []
    roaming_counts = defaultdict(
        lambda: {
            "RG -> EXT": {"2.4GHz": 0, "5GHz": 0, "6GHz": 0},
            "EXT -> RG": {"2.4GHz": 0, "5GHz": 0, "6GHz": 0},
            "total": 0,
        }
    )
    previous_states = {}
    initial_states = {}

    print("Starting roaming detection...")
    print(f"Monitoring MAC addresses: {MAC_ADDRESSES}")
    print(f"Polling interval: {POLLING_INTERVAL} seconds")
    print(f"Output file: {OUTPUT_FILE}")

    # Detect initial state
    for device_ip, device_name in [(RG_IP, "RG"), (EXT_IP, "EXT")]:
        for radio in RADIOS:
            output = ssh_execute(device_ip, f"wlanconfig {radio} list sta")
            clients = parse_wlanconfig(output)

            # Validate client count
            parsed_clients = len(clients)
            print(f"Radio {radio}: Expected clients: {parsed_clients}")

            for mac, stats in clients.items():
                if mac in MAC_ADDRESSES:
                    initial_state = f"{device_name}, {radio}, {RADIO_FREQUENCIES[radio]}"
                    initial_states[mac] = initial_state
                    previous_states[mac] = {
                        "device": device_name,
                        "radio": radio,
                        "frequency": RADIO_FREQUENCIES[radio],
                        "rssi": stats["RSSI"],
                        "snr": stats.get("SNR", "N/A"),
                    }
                    print(f"Initial state for {mac}: {initial_state}")

    while True:
        try:
            current_states = {}
            for device_ip, device_name in [(RG_IP, "RG"), (EXT_IP, "EXT")]:
                for radio in RADIOS:
                    output = ssh_execute(device_ip, f"wlanconfig {radio} list sta")
                    clients = parse_wlanconfig(output)
                    for mac, stats in clients.items():
                        if mac in MAC_ADDRESSES:
                            current_states[mac] = {
                                "device": device_name,
                                "radio": radio,
                                "frequency": RADIO_FREQUENCIES[radio],
                                "rssi": stats["RSSI"],
                                "snr": stats.get("SNR", "N/A"),
                            }

            # Detect roaming
            for mac in MAC_ADDRESSES:
                prev = previous_states.get(mac, {})
                curr = current_states.get(mac)

                if curr and prev:
                    if curr["device"] != prev["device"] or curr["radio"] != prev["radio"]:
                        roaming_event = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "mac": mac,
                            "from_device": prev["device"],
                            "to_device": curr["device"],
                            "from_radio": prev["radio"],
                            "to_radio": curr["radio"],
                            "from_frequency": prev["frequency"],
                            "to_frequency": curr["frequency"],
                            "rssi_before": prev["rssi"],
                            "rssi_after": curr["rssi"],
                            "snr_before": prev.get("snr", "N/A"),
                            "snr_after": curr.get("snr", "N/A"),
                        }
                        roaming_events.append(roaming_event)

                        # Update roaming counters
                        if prev["device"] == "RG" and curr["device"] == "EXT":
                            roaming_counts[mac]["RG -> EXT"][curr["frequency"]] += 1
                        elif prev["device"] == "EXT" and curr["device"] == "RG":
                            roaming_counts[mac]["EXT -> RG"][curr["frequency"]] += 1
                        roaming_counts[mac]["total"] += 1

                        print(
                            f"[{roaming_event['timestamp']}] MAC: {mac} roamed from "
                            f"{prev['device']} ({prev['radio']}, {prev['frequency']}) to "
                            f"{curr['device']} ({curr['radio']}, {curr['frequency']}) "
                            f"SNR: {prev.get('snr', 'N/A')} -> {curr.get('snr', 'N/A')}"
                        )

                # Delay updating previous_states until after processing all transitions
                previous_states[mac] = curr

            time.sleep(POLLING_INTERVAL)

        except KeyboardInterrupt:
            print("Stopping roaming detection...")
            save_to_excel(roaming_events, roaming_counts, initial_states)
            break

if __name__ == "__main__":
    main()
