#!/usr/bin/env python3
"""
Wordlist Splitter Utility
=========================
Splits large wordlists into chunks for parallel processing across multiple GPUs.
Optimizes memory usage for systems with limited RAM.
"""

import os
import sys
import argparse
import tempfile
import hashlib
from pathlib import Path
from typing import List, Tuple
import math

class WordlistSplitter:
    """Split wordlists for parallel GPU processing."""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="wordlist_")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def count_lines(self, filepath: str) -> int:
        """Count lines in a file efficiently."""
        count = 0
        with open(filepath, 'r', errors='ignore') as f:
            for _ in f:
                count += 1
        return count
    
    def split_evenly(self, filepath: str, num_chunks: int) -> List[str]:
        """Split wordlist into equal-sized chunks."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Wordlist not found: {filepath}")
        
        total_lines = self.count_lines(filepath)
        lines_per_chunk = total_lines // num_chunks
        remainder = total_lines % num_chunks
        
        chunk_files = []
        
        with open(filepath, 'r', errors='ignore') as f:
            for i in range(num_chunks):
                chunk_file = os.path.join(self.output_dir, f"chunk_{i:03d}.txt")
                chunk_files.append(chunk_file)
                
                # Add extra line to first 'remainder' chunks
                chunk_size = lines_per_chunk + (1 if i < remainder else 0)
                
                with open(chunk_file, 'w') as chunk_f:
                    for _ in range(chunk_size):
                        line = f.readline()
                        if line:
                            chunk_f.write(line)
        
        return chunk_files
    
    def split_by_length(self, filepath: str, num_chunks: int) -> List[str]:
        """Split wordlist by password length (for optimized attacks)."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Wordlist not found: {filepath}")
        
        # First, categorize by length
        length_buckets = {}
        
        with open(filepath, 'r', errors='ignore') as f:
            for line in f:
                word = line.strip()
                if word:
                    length = len(word)
                    if length not in length_buckets:
                        length_buckets[length] = []
                    length_buckets[length].append(word)
        
        # Sort by length
        sorted_lengths = sorted(length_buckets.keys())
        
        # Distribute lengths across chunks
        chunk_files = []
        chunks_content = [[] for _ in range(num_chunks)]
        
        # Round-robin distribution
        for i, length in enumerate(sorted_lengths):
            chunk_idx = i % num_chunks
            chunks_content[chunk_idx].extend(length_buckets[length])
        
        # Write chunks
        for i, content in enumerate(chunks_content):
            chunk_file = os.path.join(self.output_dir, f"length_chunk_{i:03d}.txt")
            chunk_files.append(chunk_file)
            
            with open(chunk_file, 'w') as f:
                for word in content:
                    f.write(word + '\n')
        
        return chunk_files
    
    def split_by_charset(self, filepath: str, num_chunks: int) -> List[str]:
        """Split wordlist by character set (lowercase, uppercase, numeric, special)."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Wordlist not found: {filepath}")
        
        # Define character categories
        categories = {
            'lowercase': set('abcdefghijklmnopqrstuvwxyz'),
            'uppercase': set('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
            'numeric': set('0123456789'),
            'special': set('!@#$%^&*()_+-=[]{}|;:,.<>?'),
        }
        
        # Categorize words
        categorized = {cat: [] for cat in categories}
        categorized['mixed'] = []
        
        with open(filepath, 'r', errors='ignore') as f:
            for line in f:
                word = line.strip()
                if not word:
                    continue
                
                # Determine primary category
                has_lower = any(c in categories['lowercase'] for c in word)
                has_upper = any(c in categories['uppercase'] for c in word)
                has_digit = any(c in categories['numeric'] for c in word)
                has_special = any(c in categories['special'] for c in word)
                
                # Count character types
                char_types = sum([has_lower, has_upper, has_digit, has_special])
                
                if char_types > 2:
                    categorized['mixed'].append(word)
                elif has_lower and not has_upper and not has_digit and not has_special:
                    categorized['lowercase'].append(word)
                elif has_upper and not has_lower and not has_digit and not has_special:
                    categorized['uppercase'].append(word)
                elif has_digit and not has_lower and not has_upper and not has_special:
                    categorized['numeric'].append(word)
                else:
                    categorized['mixed'].append(word)
        
        # Distribute categories across chunks
        chunk_files = []
        chunks_content = [[] for _ in range(num_chunks)]
        
        category_list = list(categorized.keys())
        for i, category in enumerate(category_list):
            chunk_idx = i % num_chunks
            chunks_content[chunk_idx].extend(categorized[category])
        
        # Write chunks
        for i, content in enumerate(chunks_content):
            chunk_file = os.path.join(self.output_dir, f"charset_chunk_{i:03d}.txt")
            chunk_files.append(chunk_file)
            
            with open(chunk_file, 'w') as f:
                for word in content:
                    f.write(word + '\n')
        
        return chunk_files
    
    def create_optimized(self, filepath: str, max_ram_mb: int = 500) -> str:
        """Create optimized wordlist for limited RAM systems."""
        output_file = os.path.join(self.output_dir, "optimized.txt")
        
        # Read and deduplicate
        seen = set()
        words = []
        
        with open(filepath, 'r', errors='ignore') as f:
            for line in f:
                word = line.strip()
                if word and word not in seen:
                    seen.add(word)
                    words.append(word)
        
        # Estimate size (assume ~20 bytes per word)
        estimated_mb = len(words) * 20 / (1024 * 1024)
        
        if estimated_mb > max_ram_mb:
            # Truncate to fit
            max_words = int(max_ram_mb * 1024 * 1024 / 20)
            words = words[:max_words]
            print(f"[*] Truncated to {max_words} words for {max_ram_mb}MB RAM limit")
        
        # Sort and write
        with open(output_file, 'w') as f:
            for word in sorted(words):
                f.write(word + '\n')
        
        print(f"[✓] Optimized wordlist: {output_file}")
        print(f"    Words: {len(words)}")
        print(f"    Estimated size: {estimated_mb:.2f} MB")
        
        return output_file
    
    def merge_chunks(self, chunk_files: List[str], output_file: str):
        """Merge multiple chunk files into one."""
        with open(output_file, 'w') as outfile:
            for chunk_file in chunk_files:
                with open(chunk_file, 'r') as infile:
                    for line in infile:
                        outfile.write(line)
        
        print(f"[✓] Merged {len(chunk_files)} chunks into {output_file}")
    
    def cleanup(self, chunk_files: List[str]):
        """Clean up temporary chunk files."""
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        
        # Try to remove output directory if empty
        try:
            os.rmdir(self.output_dir)
        except OSError:
            pass

def main():
    parser = argparse.ArgumentParser(
        description='Split wordlists for parallel GPU processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split into 4 equal chunks for 4 GPUs
  python split_wordlist.py --input rockyou.txt --chunks 4
  
  # Split by password length
  python split_wordlist.py --input rockyou.txt --chunks 4 --method length
  
  # Optimize for 500MB RAM
  python split_wordlist.py --input rockyou.txt --optimize 500
  
  # Custom output directory
  python split_wordlist.py --input rockyou.txt --chunks 4 --output ./chunks/
        """
    )
    
    parser.add_argument('--input', '-i', required=True, help='Input wordlist file')
    parser.add_argument('--chunks', '-c', type=int, default=4, help='Number of chunks (default: 4)')
    parser.add_argument('--method', '-m', choices=['even', 'length', 'charset'], 
                        default='even', help='Splitting method (default: even)')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--optimize', '-opt', type=int, metavar='MB',
                        help='Optimize for limited RAM (specify max MB)')
    parser.add_argument('--cleanup', action='store_true', help='Clean up after merging')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Wordlist Splitter for Parallel GPU Processing")
    print("=" * 60)
    
    splitter = WordlistSplitter(args.output)
    
    # Get input file info
    input_file = args.input
    if not os.path.exists(input_file):
        print(f"[!] Error: Input file not found: {input_file}")
        sys.exit(1)
    
    total_lines = splitter.count_lines(input_file)
    print(f"\n[*] Input: {input_file}")
    print(f"[*] Total words: {total_lines}")
    print(f"[*] Chunks: {args.chunks}")
    print(f"[*] Method: {args.method}")
    
    # Optimize mode
    if args.optimize:
        print(f"\n[*] Optimizing for {args.optimize}MB RAM...")
        optimized_file = splitter.create_optimized(input_file, args.optimize)
        print(f"\n[✓] Optimized file ready: {optimized_file}")
        return
    
    # Split wordlist
    print(f"\n[*] Splitting wordlist...")
    
    if args.method == 'even':
        chunk_files = splitter.split_evenly(input_file, args.chunks)
    elif args.method == 'length':
        chunk_files = splitter.split_by_length(input_file, args.chunks)
    elif args.method == 'charset':
        chunk_files = splitter.split_by_charset(input_file, args.chunks)
    
    # Show results
    print(f"\n[✓] Split complete!")
    print(f"    Output directory: {splitter.output_dir}")
    print(f"    Chunk files:")
    
    for i, chunk_file in enumerate(chunk_files):
        chunk_lines = splitter.count_lines(chunk_file)
        print(f"      {i}: {os.path.basename(chunk_file)} ({chunk_lines} words)")
    
    # Generate hashcat commands
    print(f"\n[*] Hashcat commands for parallel execution:")
    for i, chunk_file in enumerate(chunk_files):
        print(f"    # GPU {i}")
        print(f"    hashcat -m 22000 -a 0 -d {i} -w 3 --force capture.hc22000 {chunk_file}")
    
    # Cleanup option
    if args.cleanup:
        print(f"\n[*] Cleaning up chunks...")
        splitter.cleanup(chunk_files)
        print(f"[✓] Cleanup complete")
    else:
        print(f"\n[*] Chunks saved. Use --cleanup to remove after cracking.")

if __name__ == '__main__':
    main()
