#!/bin/bash
# =============================================================================
# WiFi Password Recovery Tool - Setup Script
# =============================================================================
# This script helps install required dependencies for the tool.
#
# USAGE:
#   sudo ./setup.sh
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;6m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║       WiFi Password Recovery Tool - Setup Script            ║"
    echo "║                         v1.0                                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[!] This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_VERSION=$(sw_vers -productVersion)
    else
        OS="unknown"
        OS_VERSION="unknown"
    fi
    
    echo -e "${BLUE}[*] Detected OS: $OS $OS_VERSION${NC}"
}

install_ubuntu_debian() {
    echo -e "${BLUE}[*] Installing dependencies for Ubuntu/Debian...${NC}"
    
    apt-get update
    
    # Install aircrack-ng suite
    apt-get install -y aircrack-ng
    
    # Install hashcat
    apt-get install -y hashcat
    
    # Install additional tools
    apt-get install -y wireless-tools iw
    
    # Install Python 3 and pip
    apt-get install -y python3 python3-pip
    
    echo -e "${GREEN}[✓] Dependencies installed successfully${NC}"
}

install_fedora_rhel() {
    echo -e "${BLUE}[*] Installing dependencies for Fedora/RHEL...${NC}"
    
    # Install aircrack-ng suite
    dnf install -y aircrack-ng
    
    # Install hashcat
    dnf install -y hashcat
    
    # Install additional tools
    dnf install -y wireless-tools iw
    
    # Install Python 3 and pip
    dnf install -y python3 python3-pip
    
    echo -e "${GREEN}[✓] Dependencies installed successfully${NC}"
}

install_arch() {
    echo -e "${BLUE}[*] Installing dependencies for Arch Linux...${NC}"
    
    # Install aircrack-ng suite
    pacman -S --noconfirm aircrack-ng
    
    # Install hashcat
    pacman -S --noconfirm hashcat
    
    # Install additional tools
    pacman -S --noconfirm wireless-tools iw
    
    # Install Python 3 and pip
    pacman -S --noconfirm python python-pip
    
    echo -e "${GREEN}[✓] Dependencies installed successfully${NC}"
}

install_macos() {
    echo -e "${BLUE}[*] Installing dependencies for macOS...${NC}"
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}[*] Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install aircrack-ng
    brew install aircrack-ng
    
    # Install hashcat
    brew install hashcat
    
    echo -e "${GREEN}[✓] Dependencies installed successfully${NC}"
}

install_wordlists() {
    echo -e "${BLUE}[*] Setting up wordlists...${NC}"
    
    mkdir -p wordlists
    
    if [[ ! -f wordlists/rockyou.txt ]]; then
        echo -e "${YELLOW}[*] Downloading rockyou.txt wordlist...${NC}"
        echo -e "${YELLOW}[*] Note: This is a large file (~140MB compressed)${NC}"
        
        # Download and extract
        cd wordlists
        wget -q --show-progress https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz
        tar -xzf rockyou.txt.tar.gz
        rm rockyou.txt.tar.gz
        cd ..
        
        echo -e "${GREEN}[✓] Wordlist downloaded${NC}"
    else
        echo -e "${GREEN}[✓] Wordlist already exists${NC}"
    fi
}

setup_directories() {
    echo -e "${BLUE}[*] Setting up directories...${NC}"
    
    mkdir -p captures
    mkdir -p logs
    mkdir -p wordlists
    
    # Make scripts executable
    chmod +x scripts/*.sh
    chmod +x wifi_cracker.py
    
    echo -e "${GREEN}[✓] Directories created${NC}"
}

verify_installation() {
    echo -e "${BLUE}[*] Verifying installation...${NC}"
    
    local tools=("airmon-ng" "aireplay-ng" "airodump-ng" "hashcat" "python3")
    local all_good=true
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            echo -e "${GREEN}  [✓] $tool${NC}"
        else
            echo -e "${RED}  [✗] $tool${NC}"
            all_good=false
        fi
    done
    
    if $all_good; then
        echo -e "${GREEN}[✓] All tools installed successfully!${NC}"
    else
        echo -e "${YELLOW}[!] Some tools may not be installed correctly${NC}"
    fi
}

print_usage() {
    echo -e "${CYAN}"
    echo "Setup complete! Here's how to use the tool:"
    echo ""
    echo "1. Linux/macOS - WPA Handshake Capture:"
    echo "   sudo ./wifi_cracker.py wpa --interface wlan0"
    echo ""
    echo "2. Windows - Extract Saved Profiles:"
    echo "   .\\wifi_cracker.py windows"
    echo ""
    echo "3. macOS - Extract from Keychain:"
    echo "   ./wifi_cracker.py macos --ssid MyNetwork"
    echo ""
    echo "For more options, run:"
    echo "   python3 wifi_cracker.py --help"
    echo -e "${NC}"
}

# Main execution
print_banner
check_root
detect_os

# Install based on OS
case $OS in
    ubuntu|debian|linuxmint)
        install_ubuntu_debian
        ;;
    fedora|rhel|centos|rocky|alma)
        install_fedora_rhel
        ;;
    arch|manjaro|endeavouros)
        install_arch
        ;;
    macos)
        install_macos
        ;;
    *)
        echo -e "${RED}[!] Unsupported OS: $OS${NC}"
        echo -e "${YELLOW}[*] Please install manually:${NC}"
        echo "    - aircrack-ng"
        echo "    - hashcat"
        echo "    - python3"
        exit 1
        ;;
esac

# Setup directories and wordlists
setup_directories
install_wordlists

# Verify installation
verify_installation

# Print usage instructions
print_usage
