import subprocess
import configparser
import os
import sys
from datetime import datetime

LOG_FILE = "update_ovh_ddns.log"
IPV6_FILE = "ipv6addr.txt"
VERSION = "1.0"

# Global flag for verbosity
VERBOSE = "--verbose" in sys.argv


def log(message):
    """Keep only the last 10 log entries. Optionally print to console if verbose."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = f"[{timestamp}] {message}\n"

    # Read existing log lines
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = []

    # Append and keep only the last 10 entries
    lines.append(new_entry)
    lines = lines[-10:]

    # Overwrite the log file
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Print to console if verbose mode is on
    if VERBOSE:
        print(new_entry.strip())


def read_config(config_file="config.txt"):
    """Reads the configuration file."""
    if not os.path.exists(config_file):
        log(f"Error: Config file '{config_file}' not found.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        username = config.get("ovh", "username")
        password = config.get("ovh", "password")
        hostname = config.get("ovh", "hostname")
        url_lookup = config.get("ovh", "url_lookup", fallback="http://ipconfig.io")
        ipv6 = config.get("ovh", "ipv6", fallback="").strip()
    except Exception as e:
        log(f"Error reading config file: {e}")
        sys.exit(1)

    return username, password, hostname, url_lookup, ipv6


def get_ipv6_from_site(url_lookup):
    """Gets the public IPv6 address using curl from the specified URL."""
    try:
        result = subprocess.run(
            ["curl", "-6", "-s", url_lookup],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        ipv6 = result.stdout.strip()
        log(f"Obtained IPv6 from {url_lookup}: {ipv6}")
        return ipv6
    except subprocess.CalledProcessError as e:
        log(f"Error fetching IPv6 address: {e}")
        sys.exit(1)


def update_ovh_dns(username, password, hostname, ipv6):
    """Updates the OVH DNS record using curl."""
    update_url = f"https://dns.eu.ovhapis.com/nic/update?system=dyndns&hostname={hostname}&myip={ipv6}"
    log(f"Updating OVH DDNS for {hostname} -> {ipv6}")

    try:
        subprocess.run(
            ["curl", "-u", f"{username}:{password}", update_url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        log("OVH DDNS update complete.")
    except subprocess.CalledProcessError as e:
        log(f"Failed to update OVH DDNS: {e}")
        sys.exit(1)


def read_last_ipv6():
    """Reads the last stored IPv6 address if the file exists."""
    if os.path.exists(IPV6_FILE):
        with open(IPV6_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def write_current_ipv6(ipv6):
    """Stores the current IPv6 address in the ipv6addr.txt file."""
    with open(IPV6_FILE, "w", encoding="utf-8") as f:
        f.write(ipv6.strip())


def main():
    # Handle --version argument first (print version and exit)
    if "--version" in sys.argv:
        print(f"update_ovh_ddns version {VERSION}")
        sys.exit(0)

    username, password, hostname, url_lookup, ipv6 = read_config()

    if not ipv6:
        ipv6 = get_ipv6_from_site(url_lookup)

    last_ipv6 = read_last_ipv6()

    if last_ipv6 and ipv6 == last_ipv6:
        log(f"No IPv6 change detected ({ipv6}). Skipping update.")
        sys.exit(0)

    update_ovh_dns(username, password, hostname, ipv6)
    write_current_ipv6(ipv6)
    log(f"Stored new IPv6 address: {ipv6}")


if __name__ == "__main__":
    main()
