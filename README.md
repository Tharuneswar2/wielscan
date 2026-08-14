# WiFi Password Recovery Tool

A multi-platform tool for recovering forgotten WiFi passwords from your own devices.

## ⚠️ IMPORTANT DISCLAIMER

**This tool is for educational purposes and authorized security testing only.**

- Use only on networks you own or have explicit written permission to test
- Unauthorized access to computer networks is illegal and unethical
- The authors are not responsible for misuse of this tool
- Always follow your local laws and regulations regarding network security testing

## 📋 Features

- **WPA Handshake Capture & Crack** (Linux/macOS/WSL)
  - Capture WPA/WPA2 handshakes using aircrack-ng
  - Crack handshakes using hashcat (GPU-accelerated)
  - Deauthentication attacks to force handshake capture

- **Windows Saved Profile Extraction**
  - Extract saved WiFi passwords from Windows
  - Export all passwords to JSON
  - No external tools required

- **macOS Keychain Extraction**
  - Extract WiFi passwords from macOS Keychain
  - Search by SSID or list all entries
  - Uses built-in `security` command

## 🚀 Quick Start

### Prerequisites

1. **Linux/macOS**: WiFi adapter that supports monitor mode
2. **Windows**: Administrator privileges (optional)
3. **Wordlist**: Download a dictionary file (e.g., rockyou.txt)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd wifi-craker

# Run setup script (Linux/macOS)
sudo ./setup.sh
```

### Usage

#### Method 1: WPA Handshake Capture (Linux/macOS/WSL)

```bash
# Check dependencies
python3 wifi_cracker.py check

# Scan for networks
sudo python3 wifi_cracker.py wpa --interface wlan0

# Capture and crack (after identifying target)
sudo python3 wifi_cracker.py wpa --interface wlan0 --bssid XX:XX:XX:XX:XX:XX --channel 6 --deauth

# Crack existing capture file
python3 wifi_cracker.py wpa --capture captures/handshake.cap --wordlist wordlists/rockyou.txt
```

#### Method 2: Windows Saved Profiles

```powershell
# Extract all saved passwords
python wifi_cracker.py windows

# Extract specific SSID
python wifi_cracker.py windows --ssid "MyHomeWiFi"

# Export to JSON
python wifi_cracker.py windows --export
```

#### Method 3: macOS Keychain

```bash
# Search for specific SSID
python3 wifi_cracker.py macos --ssid "MyHomeWiFi"

# List all WiFi keychains
python3 wifi_cracker.py macos --list-all
```

## 📁 Project Structure

```
wifi-craker/
├── wifi_cracker.py          # Main Python script
├── setup.sh                 # Setup/installation script
├── config.json              # Configuration file
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── wpa_handshake.sh     # WPA capture script (Linux/macOS)
│   ├── windows_extract.ps1  # Windows extraction script
│   └── macos_keychain.sh    # macOS keychain script
├── wordlists/               # Wordlists directory
├── captures/                # Captured handshakes
└── logs/                    # Log files
```

## 🔧 Dependencies

### Linux
```bash
sudo apt-get install aircrack-ng hashcat python3
```

### macOS
```bash
brew install aircrack-ng hashcat
```

### Windows
- Built-in `netsh` command
- Python 3.x

## 📚 Wordlists

Download wordlists for cracking:

```bash
# RockYou (popular password list)
wget https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz
tar -xzf rockyou.txt.tar.gz
mv rockyou.txt wordlists/
```

## 🛡️ Security Considerations

1. **Only test networks you own** - Unauthorized access is illegal
2. **Use strong passwords** - Avoid common passwords in your networks
3. **Enable WPA3** - Use the latest security protocols
4. **Monitor your networks** - Regularly check for unauthorized access

## 🐛 Troubleshooting

### Monitor mode not working
```bash
# Kill interfering processes
sudo airmon-ng check kill

# Try different interface names
ip link show
```

### Hashcat not finding GPU
```bash
# Check GPU drivers
sudo hashcat -I

# Install OpenCL
sudo apt-get install ocl-icd-opencl-dev
```

### Windows access denied
```powershell
# Run PowerShell as Administrator
# Right-click → Run as Administrator
```

## 📄 License

This project is for educational purposes only. Use responsibly and ethically.

## 🤝 Contributing

Contributions are welcome for:
- Bug fixes
- Documentation improvements
- Additional platform support
- Security enhancements

## ⚖️ Legal Notice

By using this software, you agree to:
1. Only use it on networks you own or have permission to test
2. Comply with all applicable local, state, and federal laws
3. Take full responsibility for your actions
4. Not use this tool for any illegal activities

**The developers assume no liability and are not responsible for any misuse or damage caused by this program.**
