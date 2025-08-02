#!/usr/bin/env python3

import json
import hashlib
import zlib
import os
import configparser
from pathlib import Path
import re

def sanitize_filename(filename):
    """Remove or replace invalid filename characters"""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove trailing dots and spaces
    sanitized = sanitized.rstrip('. ')
    return sanitized

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (FileNotFoundError, PermissionError):
        return None

def validate_app_image_path(image_path):
    """Validate and return image path, fallback to default if invalid"""
    DEFAULT_APP_IMAGE_PATH = "default_image.png"
    
    if not image_path or not os.path.exists(image_path):
        return DEFAULT_APP_IMAGE_PATH
    return image_path

def calculate_crc32(data):
    """Calculate CRC32 of string data"""
    return zlib.crc32(data.encode('utf-8')) & 0xffffffff

def calculate_app_id(app_name, app_image_path, index):
    """Generate app ID by hashing name with image data"""
    DEFAULT_APP_IMAGE_PATH = "default_image.png"
    
    to_hash = [app_name]
    
    # Validate image path
    file_path = validate_app_image_path(app_image_path)
    
    if file_path != DEFAULT_APP_IMAGE_PATH:
        # Try to calculate file hash
        file_hash = calculate_sha256(file_path)
        if file_hash:
            to_hash.append(file_hash)
        else:
            # Fallback to just hashing image path
            to_hash.append(file_path)
    
    # Create combined string for hash
    input_no_index = ''.join(to_hash)
    input_with_index = input_no_index + str(index)
    
    # CRC32 then truncate to signed 32-bit range
    id_no_index = str(abs((calculate_crc32(input_no_index) ^ 0x80000000) - 0x80000000))
    id_with_index = str(abs((calculate_crc32(input_with_index) ^ 0x80000000) - 0x80000000))
    
    return id_no_index, id_with_index

def load_config():
    """Load configuration from settings.ini"""
    config = configparser.ConfigParser()
    
    if not os.path.exists('settings.ini'):
        # Create default config file
        config['DEFAULT'] = {
            'json_file_path': 'apps.json',
            'output_directory': './moonlight_files',
            'use_index_in_id': 'false'
        }
        with open('settings.ini', 'w') as f:
            config.write(f)
        print("Created default settings.ini file")
    
    config.read('settings.ini')
    return config

def load_apps_json(json_path):
    """Load and parse the apps JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('apps', [])
    except FileNotFoundError:
        print(f"Error: JSON file '{json_path}' not found")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
        return []

def create_moonlight_files(apps, output_dir, use_index):
    """Create .moonlight files for each app"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    created_files = 0
    
    for index, app in enumerate(apps):
        app_name = app.get('name', f'App_{index}')
        app_image_path = app.get('image-path', '')
        
        # Calculate app ID
        id_no_index, id_with_index = calculate_app_id(app_name, app_image_path, index)
        
        # Choose which ID to use
        app_id = id_with_index if use_index else id_no_index
        
        # Sanitize filename
        safe_filename = sanitize_filename(app_name)
        file_path = os.path.join(output_dir, f"{safe_filename}.moonlight")
        
        try:
            # Write app ID to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(app_id)
            
            print(f"Created: {file_path} (ID: {app_id})")
            created_files += 1
            
        except Exception as e:
            print(f"Error creating file for '{app_name}': {e}")
    
    return created_files

def main():
    """Main function"""
    print("Moonlight App ID Generator")
    print("-" * 30)
    
    # Load configuration
    config = load_config()
    json_path = config.get('DEFAULT', 'json_file_path', fallback='apps.json')
    output_dir = config.get('DEFAULT', 'output_directory', fallback='./moonlight_files')
    use_index = config.getboolean('DEFAULT', 'use_index_in_id', fallback=False)
    
    print(f"JSON file: {json_path}")
    print(f"Output directory: {output_dir}")
    print(f"Use index in ID: {use_index}")
    print()
    
    # Load apps from JSON
    apps = load_apps_json(json_path)
    if not apps:
        print("No apps found or failed to load JSON file")
        return
    
    print(f"Found {len(apps)} apps in JSON file")
    print()
    
    # Create moonlight files
    created = create_moonlight_files(apps, output_dir, use_index)
    
    print()
    print(f"Successfully created {created} .moonlight files")

if __name__ == "__main__":
    main()