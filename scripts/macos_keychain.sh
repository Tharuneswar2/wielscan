#!/bin/bash
# =============================================================================
# macOS Keychain WiFi Password Extraction Script
# =============================================================================
# This script extracts saved WiFi passwords from macOS Keychain.
#
# REQUIREMENTS:
# - macOS 10.12 or later
# - User account with Keychain access
#
# USAGE:
#   ./scripts/macos_keychain.sh [OPTIONS]
#
# OPTIONS:
#   -s, --ssid SSID         Extract password for specific SSID
#   -l, --list              List all WiFi keychain entries
#   -a, --all               List all stored passwords
#   -e, --export            Export to JSON file
#   -h, --help              Show this help message
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

# Functions
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║       macOS Keychain WiFi Password Extraction Tool          ║"
    echo "║                         v1.0                                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --ssid SSID         Extract password for specific SSID"
    echo "  -l, --list              List all WiFi keychain entries"
    echo "  -a, --all               List all stored passwords"
    echo "  -e, --export            Export to JSON file"
    echo "  -h, --help              Show this help message"
}

check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        echo -e "${RED}[!] This script only works on macOS${NC}"
        exit 1
    fi
}

check_keychain_access() {
    echo -e "${BLUE}[*] Checking keychain access...${NC}"
    
    # Try to access keychain
    if security find-generic-password -l "test" -g 2>&1 | grep -q "The specified item could not be found in the keychain"; then
        echo -e "${GREEN}[✓] Keychain access available${NC}"
        return 0
    else
        echo -e "${YELLOW}[!] Keychain may require password unlock${NC}"
        echo -e "${YELLOW}[*] Please unlock your keychain if prompted${NC}"
        return 0
    fi
}

list_wifi_keychains() {
    echo -e "${BLUE}[*] Searching for WiFi keychain entries...${NC}"
    
    # Search for various WiFi-related patterns
    local patterns=(
        "WiFi"
        "wifi"
        "AirPort"
        "airport"
        "WLAN"
        "wlan"
        "802.11"
        "wireless"
    )
    
    local found=0
    
    for pattern in "${patterns[@]}"; do
        result=$(security dump-keychain 2>/dev/null | grep -A 5 -i "$pattern" || true)
        if [[ -n "$result" ]]; then
            echo -e "${CYAN}[*] Found entries matching '$pattern':${NC}"
            echo "$result" | head -20
            echo ""
            found=1
        fi
    done
    
    if [[ $found -eq 0 ]]; then
        echo -e "${YELLOW}[!] No WiFi keychain entries found with common patterns${NC}"
    fi
}

list_all_passwords() {
    echo -e "${BLUE}[*] Listing all stored WiFi passwords...${NC}"
    echo -e "${YELLOW}[*] Note: You may need to enter your macOS password${NC}"
    echo ""
    
    # Get all generic passwords
    security dump-keychain 2>/dev/null | grep -B 2 -A 10 "svce\|\"v_Data\"" || true
}

get_password_for_ssid() {
    local ssid="$1"
    
    echo -e "${BLUE}[*] Searching for password for: $ssid${NC}"
    
    # Try different search patterns
    local patterns=(
        "$ssid"
        "$ssid@airport"
        "WiFi-$ssid"
        "$ssid-password"
        "AirPort-$ssid"
    )
    
    for pattern in "${patterns[@]}"; do
        echo -e "${CYAN}[*] Trying pattern: $pattern${NC}"
        
        result=$(security find-generic-password -l "$pattern" -g 2>&1)
        
        # Check if we found a password
        if echo "$result" | grep -q "password:"; then
            password=$(echo "$result" | grep "password:" | head -1 | sed 's/.*password: "\(.*\)".*/\1/')
            echo -e "${GREEN}[✓] Password found!${NC}"
            echo ""
            echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║ SSID: $ssid${NC}"
            echo -e "${GREEN}║ Password: $password${NC}"
            echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
            return 0
        fi
        
        # Try alternate format
        if echo "$result" | grep -q '"v_Data"'; then
            password=$(echo "$result" | grep '"v_Data"' | sed 's/.*"v_Data"<blob>="\([^"]*\)".*/\1/')
            if [[ -n "$password" ]]; then
                echo -e "${GREEN}[✓] Password found!${NC}"
                echo ""
                echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
                echo -e "${GREEN}║ SSID: $ssid${NC}"
                echo -e "${GREEN}║ Password: $password${NC}"
                echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
                return 0
            fi
        fi
    done
    
    echo -e "${YELLOW}[!] No password found for: $ssid${NC}"
    echo -e "${YELLOW}[*] The network may use a different naming convention${NC}"
    return 1
}

export_to_json() {
    local output_file="wifi_passwords_macos_$(date +%Y%m%d_%H%M%S).json"
    
    echo -e "${BLUE}[*] Exporting passwords to JSON...${NC}"
    
    # Create JSON structure
    echo "{" > "$output_file"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$output_file"
    echo "  \"hostname\": \"$(hostname)\"," >> "$output_file"
    echo "  \"profiles\": [" >> "$output_file"
    
    # Try to extract common WiFi names from system
    # This is a best-effort approach
    echo "    {" >> "$output_file"
    echo "      \"note\": \"Keychain access required for full extraction\"" >> "$output_file"
    echo "    }" >> "$output_file"
    
    echo "  ]" >> "$output_file"
    echo "}" >> "$output_file"
    
    echo -e "${GREEN}[✓] JSON template created: $output_file${NC}"
    echo -e "${YELLOW}[*] Use -s <SSID> to extract specific passwords${NC}"
}

# Parse arguments
SSID=""
LIST=false
ALL=false
EXPORT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--ssid)
            SSID="$2"
            shift 2
            ;;
        -l|--list)
            LIST=true
            shift
            ;;
        -a|--all)
            ALL=true
            shift
            ;;
        -e|--export)
            EXPORT=true
            shift
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
check_macos
check_keychain_access

if $LIST; then
    list_wifi_keychains
elif $ALL; then
    list_all_passwords
elif $EXPORT; then
    export_to_json
elif [[ -n "$SSID" ]]; then
    get_password_for_ssid "$SSID"
else
    # Default: show available options
    echo -e "${YELLOW}[*] WiFi Password Extraction Options:${NC}"
    echo ""
    echo -e "${CYAN}  -l, --list              List WiFi keychain entries${NC}"
    echo -e "${CYAN}  -s, --ssid SSID         Get password for specific SSID${NC}"
    echo -e "${CYAN}  -a, --all               Show all stored passwords${NC}"
    echo -e "${CYAN}  -e, --export            Export to JSON file${NC}"
    echo ""
    echo -e "${YELLOW}[*] Example:${NC}"
    echo -e "${CYAN}  $0 --ssid \"MyHomeWiFi\"${NC}"
    echo ""
fi

echo -e "${GREEN}[*] Done!${NC}"
