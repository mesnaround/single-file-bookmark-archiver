#!/usr/bin/env python3

"""
Bookmark Archiver - Automatically archive Firefox bookmarks using SingleFile

Usage: python bookmark_archiver.py [config-file]

If no config file is provided, it will look for config.json in the same directory
"""

import configparser
import json
import os
import sys
import subprocess
import yaml
import lz4.block
from pathlib import Path
from datetime import datetime
from typing import Set, List, Dict, Optional


def load_yaml_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


class BookmarkArchiver:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self.load_config(config_path)
        self.processed_urls: Set[str] = set()
        
    def load_config(self, config_path: Optional[str] = None) -> dict:
        """Load configuration from file or use defaults"""
        default_config = {
            "firefox_profile": None,  # Auto-detect if None
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config_all = yaml.safe_load(f)
                user_config = user_config_all["single_file_bookmark_archiver"]
                return {**default_config, **user_config}
        else:
            raise RuntimeError(f'config_path is a required argument and must exist, but found {config_path}')
        
        return default_config
    

    def find_firefox_profile(self) -> Path:
        """Find Firefox profile directory"""
        if self.config["firefox_profile"]:
            return Path(self.config["firefox_profile"])
        
        firefox_dir = Path.home() / ".mozilla" / "firefox"
        
        if not firefox_dir.exists():
            raise FileNotFoundError(f"Firefox directory not found at {firefox_dir}")
        
        # Read profiles.ini to find the default profile
        profiles_ini = firefox_dir / "profiles.ini"
        if not profiles_ini.exists():
            raise FileNotFoundError(f"profiles.ini not found at {profiles_ini}")
        
        config = configparser.ConfigParser()
        config.read(profiles_ini)
        
        # Look for the profile marked as Default=1
        for section in config.sections():
            if config.get(section, 'Default', fallback='0') == '1':
                path = config.get(section, 'Path')
                is_relative = config.get(section, 'IsRelative', fallback='1') == '1'
                
                if is_relative:
                    return firefox_dir / path
                else:
                    return Path(path)
        
        raise FileNotFoundError("No default Firefox profile found in profiles.ini")

    def get_latest_bookmark_backup(self, profile_dir: Path) -> Path:
        """Get the most recent bookmark backup file"""
        backup_dir = profile_dir / "bookmarkbackups"
        
        if not backup_dir.exists():
            raise FileNotFoundError(f"Bookmark backup directory not found at {backup_dir}")
        
        backups = [
            f for f in backup_dir.iterdir()
            if f.is_file() and (f.name.endswith('.jsonlz4') or f.name.endswith('.json'))
        ]
        
        if not backups:
            raise FileNotFoundError("No bookmark backups found")
        
        # Sort by modification time, most recent first
        backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return backups[0]
    
    def read_bookmark_backup(self, backup_path: Path) -> dict:
        """Read and decompress Firefox bookmark backup"""
        # If it's already JSON, just read it
        if backup_path.suffix == '.json':
            with open(backup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # For .jsonlz4 files, decompress
        # Format: 8 bytes magic number "mozLz40\0" + LZ4 compressed JSON
        try:
            with open(backup_path, 'rb') as f:
                data = f.read()
            
            # Check magic number
            magic = data[:8]
            if not magic.startswith(b'mozLz40'):
                raise ValueError("Invalid jsonlz4 file format")
            
            # Decompress the rest
            decompressed = lz4.block.decompress(data[8:])
            return json.loads(decompressed.decode('utf-8'))
            
        except ImportError:
            raise ImportError(
                "lz4 package required for reading compressed backups.\n"
                "Install with: pip install lz4"
            )
        except Exception as e:
            raise Exception(f"Failed to read bookmark backup: {e}")
    
    def find_bookmark_folder(self, node: dict, folder_name: str) -> Optional[dict]:
        """Recursively find a bookmark folder by name"""
        # NOTE debug lines
        #if (node.get('type') == 'text/x-moz-place-container'):
        #    print(node.get('title'))
 
        if (node.get('type') == 'text/x-moz-place-container' and 
            node.get('title') == folder_name):
            return node
        
        if 'children' in node:
            for child in node['children']:
                found = self.find_bookmark_folder(child, folder_name)
                if found:
                    return found
        
        return None
    
    def extract_urls(self, folder: Optional[dict]) -> List[Dict[str, str]]:
        """Extract all URLs from a bookmark folder"""
        if not folder or 'children' not in folder:
            return []
        
        urls = []
        for item in folder['children']:
            if item.get('type') == 'text/x-moz-place' and 'uri' in item:
                urls.append({
                    'url': item['uri'],
                    'title': item.get('title', 'Untitled')
                })
        
        return urls
    
    def load_processed_urls(self):
        """Load previously processed URLs from log file"""
        log_path = Path(self.config["processed_urls_log"])
        if log_path.exists():
            with open(log_path, 'r') as f:
                self.processed_urls = {
                    line.strip() for line in f if line.strip()
                }
    
    def mark_as_processed(self, url: str):
        """Mark a URL as processed by appending to log"""
        self.processed_urls.add(url)
        with open(self.config["processed_urls_log"], 'a') as f:
            f.write(url + '\n')
    
    def archive_url(self, url: str, title: str) -> bool:
        """Archive a URL using SingleFile CLI"""
        print(f"Archiving: {title or url}")
        
        try:
            # Create safe filename
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            safe_title = "".join(
                c if c.isalnum() or c in (' ', '-', '_') else '-' 
                for c in (title or 'untitled')
            )[:100]
            filename = f"{timestamp}_{safe_title}.html"
            output_path = Path(self.config["archive_destination"]) / filename
            
            # Run SingleFile CLI
            subprocess.run(
                ['npx', 'single-file', url, str(output_path)],
                check=True,
                capture_output=True,
                text=True
            )
            
            self.mark_as_processed(url)
            print(f"✓ Saved: {filename}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to archive {url}: {e.stderr}")
            return False
        except Exception as e:
            print(f"✗ Error archiving {url}: {e}")
            return False
    
    def run(self):
        """Main archive process"""
        print("Starting bookmark archiver...\n")
        
        # Ensure archive destination exists
        archive_dir = Path(self.config["archive_destination"])
        archive_dir.mkdir(parents=True, exist_ok=True)
        print(f"Archive directory: {archive_dir}")
        
        # Ensure log directory exists
        log_path = Path(self.config["processed_urls_log"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load processed URLs
        self.load_processed_urls()
        print(f"Loaded {len(self.processed_urls)} previously processed URLs\n")
        
        # Find Firefox profile
        try:
            profile_dir = self.find_firefox_profile()
            print(f"Firefox profile: {profile_dir}")
        except Exception as e:
            print(f"Error finding Firefox profile: {e}")
            return
        
        # Get latest bookmark backup
        try:
            backup_path = self.get_latest_bookmark_backup(profile_dir)
            print(f"Bookmark backup: {backup_path.name}")
        except Exception as e:
            print(f"Error finding bookmark backup: {e}")
            return
        
        # Read bookmarks
        try:
            bookmarks = self.read_bookmark_backup(backup_path)
            print("Successfully loaded bookmarks\n")
        except Exception as e:
            print(f"Error reading bookmarks: {e}")
            return
        
        # Find target folder
        folder = self.find_bookmark_folder(
            bookmarks, 
            self.config["bookmark_folder_name"]
        )
        
        if not folder:
            print(f"Bookmark folder '{self.config['bookmark_folder_name']}' not found")
            return

        
        # Extract URLs
        urls = self.extract_urls(folder)
        print(f"Found {len(urls)} bookmarks in folder\n")
        
        # Filter out already processed URLs
        new_urls = [
            item for item in urls 
            if item['url'] not in self.processed_urls
        ]

        if not new_urls:
            print("No new URLs to archive")
            return
        
        print(f"Archiving {len(new_urls)} new URLs...\n")
        
        # Archive each URL
        success_count = 0
        for item in new_urls:
            if self.archive_url(item['url'], item['title']):
                success_count += 1
        
        print(f"\n✓ Successfully archived {success_count}/{len(new_urls)} URLs")


def main():
    config_path = sPath(ys.argv[1]) if len(sys.argv) > 1 else Path(os.getenv('SINGLE_FILE_BOOKMARK_ARCHIVER_CONFIG'))

    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    archiver = BookmarkArchiver(config_path)
    archiver.run()


if __name__ == "__main__":
    main()
