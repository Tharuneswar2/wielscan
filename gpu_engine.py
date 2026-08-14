#!/usr/bin/env python3
"""
GPU Engine Module - Multi-GPU Management for WiFi Cracker
=========================================================
Handles GPU detection, distribution, and parallel attack execution
for systems with multiple GPUs (NVIDIA/AMD).
"""

import subprocess
import os
import sys
import json
import platform
import re
import multiprocessing
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import shutil
import tempfile

@dataclass
class GPUInfo:
    """Information about a single GPU."""
    id: int
    name: str
    vendor: str  # NVIDIA, AMD, Intel
    memory: int  # MB
    cuda_cores: Optional[int] = None
    compute_capability: Optional[str] = None
    is_available: bool = True

class GPUEngine:
    """Multi-GPU engine for hashcat operations."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.gpus: List[GPUInfo] = []
        self.hashcat_path = self._find_hashcat()
        self.workers = self.config.get('max_workers', multiprocessing.cpu_count())
        self.gpu_mode = self.config.get('gpu_mode', 'parallel')
        
    def _find_hashcat(self) -> str:
        """Find hashcat executable path."""
        if platform.system() == 'Windows':
            # Check common Windows locations
            paths = [
                r"C:\Program Files\hashcat\hashcat.exe",
                r"C:\hashcat\hashcat.exe",
                os.path.expanduser(r"~\hashcat\hashcat.exe"),
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            # Try PATH
            return "hashcat.exe"
        else:
            # Linux/macOS
            result = subprocess.run(["which", "hashcat"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            return "hashcat"
    
    def detect_gpus(self) -> List[GPUInfo]:
        """Detect available GPUs using hashcat -I."""
        self.gpus = []
        
        try:
            result = subprocess.run(
                [self.hashcat_path, "-I"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            # Parse NVIDIA GPUs
            nvidia_pattern = r'CUDA\.(\d+)\s+:\s+(.+?)\s+.*?Memory:\s+(\d+)\s+MB'
            for match in re.finditer(nvidia_pattern, output):
                gpu = GPUInfo(
                    id=int(match.group(1)),
                    name=match.group(2).strip(),
                    vendor='NVIDIA',
                    memory=int(match.group(3))
                )
                self.gpus.append(gpu)
            
            # Parse AMD GPUs (OpenCL)
            amd_pattern = r'OpenCL\.(\d+)\s+:\s+(.+?)\s+.*?Memory:\s+(\d+)\s+MB'
            for match in re.finditer(amd_pattern, output):
                gpu = GPUInfo(
                    id=int(match.group(1)),
                    name=match.group(2).strip(),
                    vendor='AMD',
                    memory=int(match.group(3))
                )
                self.gpus.append(gpu)
            
            # If no GPUs found via parsing, check for basic availability
            if not self.gpus:
                # Check if any CUDA/OpenCL devices exist
                if 'CUDA' in output or 'OpenCL' in output:
                    # Assume at least one GPU
                    self.gpus.append(GPUInfo(
                        id=0,
                        name="Unknown GPU",
                        vendor="Unknown",
                        memory=0
                    ))
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"[!] Error detecting GPUs: {e}")
        
        return self.gpus
    
    def get_gpu_count(self) -> int:
        """Get number of available GPUs."""
        if not self.gpus:
            self.detect_gpus()
        return len(self.gpus)
    
    def get_gpu_ids(self) -> List[int]:
        """Get list of GPU IDs."""
        if not self.gpus:
            self.detect_gpus()
        return [gpu.id for gpu in self.gpus]
    
    def split_wordlist(self, wordlist_path: str, num_chunks: int) -> List[str]:
        """Split wordlist into chunks for parallel processing."""
        if not os.path.exists(wordlist_path):
            raise FileNotFoundError(f"Wordlist not found: {wordlist_path}")
        
        # Create temp directory for chunks
        temp_dir = tempfile.mkdtemp(prefix="hashcat_")
        chunk_files = []
        
        # Count lines
        with open(wordlist_path, 'r', errors='ignore') as f:
            line_count = sum(1 for _ in f)
        
        lines_per_chunk = line_count // num_chunks
        remainder = line_count % num_chunks
        
        with open(wordlist_path, 'r', errors='ignore') as f:
            for i in range(num_chunks):
                chunk_file = os.path.join(temp_dir, f"chunk_{i}.txt")
                chunk_files.append(chunk_file)
                
                chunk_size = lines_per_chunk + (1 if i < remainder else 0)
                
                with open(chunk_file, 'w') as chunk_f:
                    for j in range(chunk_size):
                        line = f.readline()
                        if line:
                            chunk_f.write(line)
        
        return chunk_files
    
    def cleanup_chunks(self, chunk_files: List[str]):
        """Clean up temporary chunk files."""
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        # Remove temp directory
        temp_dir = os.path.dirname(chunk_files[0]) if chunk_files else None
        if temp_dir and os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass
    
    def build_hashcat_command(
        self,
        hash_file: str,
        wordlist: str,
        hash_mode: int = 22000,
        attack_mode: int = 0,
        gpu_ids: List[int] = None,
        rules: List[str] = None,
        extra_args: List[str] = None
    ) -> List[str]:
        """Build hashcat command with GPU configuration."""
        cmd = [
            self.hashcat_path,
            "-m", str(hash_mode),
            "-a", str(attack_mode),
            "-w", "3",  # High workload
            "--force"
        ]
        
        # Add GPU devices
        if gpu_ids:
            device_str = ",".join(str(g) for g in gpu_ids)
            cmd.extend(["-d", device_str])
        
        # Add rules
        if rules:
            for rule in rules:
                cmd.extend(["-r", rule])
        
        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)
        
        # Add hash file and wordlist
        cmd.extend([hash_file, wordlist])
        
        return cmd
    
    def launch_parallel_attack(
        self,
        hash_file: str,
        wordlist_path: str,
        hash_mode: int = 22000,
        gpu_count: int = None,
        rules: List[str] = None
    ) -> List[subprocess.Popen]:
        """Launch parallel hashcat instances across multiple GPUs."""
        if not self.gpus:
            self.detect_gpus()
        
        if not gpu_count:
            gpu_count = len(self.gpus)
        
        if gpu_count == 0:
            print("[!] No GPUs detected, falling back to CPU")
            gpu_count = 1
        
        print(f"[*] Launching {gpu_count} parallel workers...")
        
        # Split wordlist
        chunk_files = self.split_wordlist(wordlist_path, gpu_count)
        
        processes = []
        
        for i in range(gpu_count):
            gpu_id = self.gpus[i].id if i < len(self.gpus) else i
            
            cmd = self.build_hashcat_command(
                hash_file=hash_file,
                wordlist=chunk_files[i],
                hash_mode=hash_mode,
                gpu_ids=[gpu_id],
                rules=rules
            )
            
            print(f"[*] Worker {i}: GPU {gpu_id} -> {os.path.basename(chunk_files[i])}")
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append(proc)
        
        return processes, chunk_files
    
    def monitor_processes(self, processes: List[subprocess.Popen]) -> Dict[int, dict]:
        """Monitor running hashcat processes."""
        results = {}
        
        for i, proc in enumerate(processes):
            poll = proc.poll()
            if poll is not None:
                # Process finished
                stdout, stderr = proc.communicate()
                results[i] = {
                    'status': 'completed' if poll == 0 else 'failed',
                    'returncode': poll,
                    'output': stdout,
                    'error': stderr
                }
            else:
                results[i] = {
                    'status': 'running',
                    'pid': proc.pid
                }
        
        return results
    
    def stop_all(self, processes: List[subprocess.Popen]):
        """Stop all running processes."""
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    
    def extract_password_from_output(self, output: str) -> Optional[str]:
        """Extract cracked password from hashcat output."""
        # Hashcat outputs the password after a colon
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

class AdvancedWordlistGenerator:
    """Generate advanced wordlists using patterns and rules."""
    
    def __init__(self):
        self.john_path = self._find_john()
        self.cewl_path = self._find_cewl()
    
    def _find_john(self) -> Optional[str]:
        """Find John the Ripper executable."""
        if platform.system() == 'Windows':
            paths = [
                r"C:\Program Files\john\john.exe",
                r"C:\john\john.exe",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        else:
            result = subprocess.run(["which", "john"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        return None
    
    def _find_cewl(self) -> Optional[str]:
        """Find cewl executable."""
        result = subprocess.run(["which", "cewl"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def generate_with_rules(
        self,
        input_wordlist: str,
        output_wordlist: str,
        rules: List[str] = None
    ) -> str:
        """Generate wordlist using hashcat rules."""
        if not rules:
            rules = ["best64.rule", "d3ad0ne.rule", "dive.rule"]
        
        # Check if hashcat is available
        hashcat_path = "hashcat.exe" if platform.system() == 'Windows' else "hashcat"
        
        cmd = [
            hashcat_path,
            "-r", ",".join(rules),
            "--stdout",
            input_wordlist
        ]
        
        with open(output_wordlist, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        return output_wordlist
    
    def generate_patterns(
        self,
        output_wordlist: str,
        min_length: int = 8,
        max_length: int = 16
    ) -> str:
        """Generate password patterns using mask attacks."""
        hashcat_path = "hashcat.exe" if platform.system() == 'Windows' else "hashcat"
        
        # Common password patterns
        masks = [
            "?l?l?l?l?l?l?d?d",      # 6 lowercase + 2 digits
            "?u?l?l?l?l?d?d?d",      # 1 upper + 4 lower + 3 digits
            "?l?l?l?l?l?l?l?d",      # 7 lowercase + 1 digit
            "?u?l?l?l?l?l?l?d",      # 1 upper + 6 lower + 1 digit
            "?l?l?l?l?l?d?d?d?d",    # 5 lower + 4 digits
        ]
        
        with open(output_wordlist, 'w') as f:
            for mask in masks:
                cmd = [
                    hashcat_path,
                    "-a", "3",
                    "--stdout",
                    mask
                ]
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        return output_wordlist
    
    def crawl_website(
        self,
        url: str,
        output_wordlist: str,
        depth: int = 3,
        min_word_length: int = 4
    ) -> str:
        """Crawl website to generate custom wordlist using cewl."""
        if not self.cewl_path:
            raise FileNotFoundError("cewl not found. Install with: gem install cewl")
        
        cmd = [
            self.cewl_path,
            "-d", str(depth),
            "-m", str(min_word_length),
            "--lowercase",
            "-o", output_wordlist,
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"cewl failed: {result.stderr}")
        
        return output_wordlist

def optimize_for_ram(wordlist_path: str, max_size_mb: int = 100) -> str:
    """Optimize wordlist for limited RAM by removing duplicates and sorting."""
    output_path = wordlist_path + ".optimized"
    
    # Read and deduplicate
    seen = set()
    with open(wordlist_path, 'r', errors='ignore') as f:
        for line in f:
            word = line.strip()
            if word and word not in seen:
                seen.add(word)
    
    # Check size
    estimated_size_mb = len(seen) * 20 / (1024 * 1024)  # Assume ~20 bytes per word
    
    if estimated_size_mb > max_size_mb:
        # Truncate to fit
        max_words = int(max_size_mb * 1024 * 1024 / 20)
        words = list(seen)[:max_words]
    else:
        words = list(seen)
    
    # Write optimized wordlist
    with open(output_path, 'w') as f:
        for word in sorted(words):
            f.write(word + '\n')
    
    return output_path
