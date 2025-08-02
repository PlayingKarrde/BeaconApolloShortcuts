#!/usr/bin/env python3

import json
import hashlib
import zlib
import os
import configparser
from pathlib import Path
import re
import uuid

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
            'source_folder': './config',
            'output_directory': './moonlight_files',
            'use_index_in_id': 'false',
            'clear_output_folder': 'true'
        }
        with open('settings.ini', 'w') as f:
            config.write(f)
        print("Created default settings.ini file")
    
    config.read('settings.ini')
    return config

def load_apps_json(source_folder):
    """Load and parse the apps JSON file from source folder"""
    json_path = os.path.join(source_folder, 'apps.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('apps', [])
    except FileNotFoundError:
        print(f"Error: apps.json not found in '{source_folder}'")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing apps.json: {e}")
        return []

def load_sunshine_uuid(source_folder):
    """Load UUID from sunshine_state.json"""
    json_path = os.path.join(source_folder, 'sunshine_state.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # The uniqueid is nested under root
        root_data = data.get('root', {})
        return root_data.get('uniqueid')
    except FileNotFoundError:
        print(f"Error: sunshine_state.json not found in '{source_folder}'")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing sunshine_state.json: {e}")
        return None

def clear_output_folder(output_dir):
    """Clear all .moonlight and .uuid files from output directory"""
    if not os.path.exists(output_dir):
        return 0
    
    deleted_count = 0
    try:
        for filename in os.listdir(output_dir):
            if filename.endswith('.moonlight') or filename == 'Moonlight.uuid':
                file_path = os.path.join(output_dir, filename)
                os.remove(file_path)
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"Cleared {deleted_count} existing files from output directory")
    except Exception as e:
        print(f"Error clearing output directory: {e}")
    
    return deleted_count
    """Create Moonlight.uuid file with the provided UUID"""
    uuid_file_path = os.path.join(output_dir, "Moonlight.uuid")
    
    try:
        with open(uuid_file_path, 'w', encoding='utf-8') as f:
            f.write(host_uuid)
        print(f"Created: {uuid_file_path} (UUID: {host_uuid})")
        return True
    except Exception as e:
        print(f"Error creating UUID file: {e}")
        return False

def create_uuid_file(output_dir, host_uuid):
    """Create Moonlight.uuid file with the provided UUID"""
    uuid_file_path = os.path.join(output_dir, "Moonlight.uuid")
    
    try:
        with open(uuid_file_path, 'w', encoding='utf-8') as f:
            f.write(host_uuid)
        print(f"Created: {uuid_file_path} (UUID: {host_uuid})")
        return True
    except Exception as e:
        print(f"Error creating UUID file: {e}")
        return False

def create_moonlight_files(apps, output_dir, use_index, host_uuid, clear_folder):
    """Create .moonlight files for each app and UUID file"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Clear existing files if requested
    if clear_folder:
        clear_output_folder(output_dir)
    
    # Create UUID file first
    if host_uuid:
        create_uuid_file(output_dir, host_uuid)
    else:
        print("Warning: No UUID found, skipping Moonlight.uuid creation")
    
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
            # Write app ID to file (this will overwrite existing files)
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
    source_folder = config.get('DEFAULT', 'source_folder', fallback='./config')
    output_dir = config.get('DEFAULT', 'output_directory', fallback='./moonlight_files')
    use_index = config.getboolean('DEFAULT', 'use_index_in_id', fallback=False)
    clear_folder = config.getboolean('DEFAULT', 'clear_output_folder', fallback=True)
    
    print(f"Source folder: {source_folder}")
    print(f"Output directory: {output_dir}")
    print(f"Use index in ID: {use_index}")
    print(f"Clear output folder: {clear_folder}")
    print()
    
    # Load UUID from sunshine_state.json
    host_uuid = load_sunshine_uuid(source_folder)
    if host_uuid:
        print(f"Found host UUID: {host_uuid}")
    else:
        print("Warning: Host UUID not found in sunshine_state.json")
    
    # Load apps from JSON
    apps = load_apps_json(source_folder)
    if not apps:
        print("No apps found or failed to load apps.json")
        return
    
    print(f"Found {len(apps)} apps in apps.json")
    print()
    
    # Create moonlight files
    created = create_moonlight_files(apps, output_dir, use_index, host_uuid, clear_folder)
    
    print()
    print(f"Successfully created {created} .moonlight files")
    if host_uuid:
        print("Created Moonlight.uuid file")

if __name__ == "__main__":
    main()