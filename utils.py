import csv
import subprocess

def get_wifi_ssid():
    """Gets the SSID of the currently connected Wi-Fi network (Linux/Debian)."""
    try:
        # Try iwgetid first (common on Debian/Raspberry Pi)
        ssid = subprocess.check_output(['iwgetid', '-r'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if ssid:
            return ssid
    except Exception:
        pass

    try:
        # Try nmcli as a fallback (NetworkManager)
        output = subprocess.check_output(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], stderr=subprocess.DEVNULL).decode('utf-8')
        for line in output.split('\n'):
            if line.startswith('yes:'):
                return line.split(':', 1)[1].strip()
    except Exception:
        pass

    return None

def read_wifi_networks_csv():
    """
    - Columns expected:
        - ssid (e.g. "NETGEAR420")
        - timezone (e.g. "America/Los_Angeles")
        - state (e.g. "CA")
        - city (e.g. "Death Valley")
    """
    with open("wifi_networks.csv", 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
    
def get_wifi_config():
    ssid = get_wifi_ssid()
    if ssid is None:
        return None
    return [wifi for wifi in read_wifi_networks_csv() if wifi['ssid'] == ssid][0]