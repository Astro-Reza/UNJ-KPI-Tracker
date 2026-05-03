#!/usr/bin/env python3
"""
Firebase Database URL Extractor
Automatically finds and extracts your Firestore database URL
"""

import json
import os
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def find_service_account_key():
    """Find the service account key file"""
    possible_paths = [
        './serviceAccountKey.json',
        'serviceAccountKey.json',
        os.path.expanduser('~/serviceAccountKey.json'),
        os.path.expanduser('~/Downloads/serviceAccountKey.json'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def extract_database_url(key_file_path):
    """Extract database URL from service account key"""
    try:
        with open(key_file_path, 'r') as f:
            data = json.load(f)
        
        if 'databaseURL' in data:
            return data['databaseURL']
        else:
            return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def create_env_entry(db_url, project_id):
    """Create .env entry"""
    return f"""
# Add this to your .env file:
DATABASE_URL={db_url}
FIREBASE_PROJECT_ID={project_id}
"""

def main():
    print("🔍 Firebase Database URL Extractor")
    print("=" * 50)
    
    # Try to find the service account key
    key_path = find_service_account_key()
    
    if not key_path:
        print("\n serviceAccountKey.json not found!")
        print("\nPlease make sure:")
        print("1. You downloaded serviceAccountKey.json from Firebase Console")
        print("2. It's in your project root directory")
        print("3. The filename is exactly: serviceAccountKey.json")
        print("\nLooking in:")
        for path in ['./serviceAccountKey.json', '~/serviceAccountKey.json']:
            print(f"  - {path}")
        return
    
    print(f"\n✓ Found: {key_path}")
    
    # Extract the database URL
    db_url = extract_database_url(key_path)
    
    if not db_url:
        print("\n Database URL not found in serviceAccountKey.json")
        print("\nThis might mean:")
        print("1. Your service account key is invalid or corrupted")
        print("2. You didn't create a Firestore database yet")
        print("\nTo create a Firestore database:")
        print("1. Go to https://console.firebase.google.com/")
        print("2. Select your project")
        print("3. Click 'Firestore Database' in the left sidebar")
        print("4. Click 'Create database'")
        print("5. Follow the setup wizard")
        print("6. Download the service account key again")
        return
    
    # Read the full key to get project_id
    with open(key_path, 'r') as f:
        data = json.load(f)
        project_id = data.get('project_id', 'unknown')
    
    print("\n SUCCESS! Found your database URL:")
    print("=" * 50)
    print(f"\n Database URL:")
    print(f"   {db_url}")
    print(f"\n Project ID:")
    print(f"   {project_id}")
    
    # Create .env entry
    env_entry = create_env_entry(db_url, project_id)
    print("\n" + "=" * 50)
    print(env_entry)
    print("=" * 50)
    
    # Try to update .env file
    print("\n Updating .env file...")
    env_file = '.env'
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        # Check if DATABASE_URL already exists
        if 'DATABASE_URL=' in env_content:
            # Replace existing
            lines = env_content.split('\n')
            updated_lines = []
            for line in lines:
                if line.startswith('DATABASE_URL='):
                    updated_lines.append(f'DATABASE_URL={db_url}')
                elif line.startswith('FIREBASE_PROJECT_ID='):
                    updated_lines.append(f'FIREBASE_PROJECT_ID={project_id}')
                else:
                    updated_lines.append(line)
            
            with open(env_file, 'w') as f:
                f.write('\n'.join(updated_lines))
            
            print("Updated DATABASE_URL in .env")
        else:
            # Append to .env
            with open(env_file, 'a') as f:
                f.write(f'\n\n# Firebase Configuration (Added automatically)\n')
                f.write(f'DATABASE_URL={db_url}\n')
                f.write(f'FIREBASE_PROJECT_ID={project_id}\n')
            
            print("Added DATABASE_URL to .env")
    else:
        # Create new .env file
        with open(env_file, 'w') as f:
            f.write(f'# Firebase Configuration\n')
            f.write(f'DATABASE_URL={db_url}\n')
            f.write(f'FIREBASE_PROJECT_ID={project_id}\n')
            f.write(f'\n# Add other required variables:\n')
            f.write(f'SECRET_KEY=your-secret-key-here\n')
            f.write(f'ADMIN_USERNAME=admin\n')
            f.write(f'ADMIN_PASSWORD_HASH=your-hashed-password\n')
            f.write(f'FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json\n')
        
        print("✓ Created .env file")
    
    print("\n" + "=" * 50)
    print("All done! You can now run your Flask app:")
    print("   python app.py")
    print("=" * 50)

if __name__ == '__main__':
    main()