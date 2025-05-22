#!/usr/bin/env python3
"""
Dataset Backup and Restore Script

This script provides functionality to backup and restore provider datasets via the API.
It can backup all providers or a specific provider, and restore from backup files.
"""

import argparse
import datetime
import json
import os
import sys
import requests
from typing import Dict, List, Optional, Union, Any

class DatasetManager:
    def __init__(self, host: str, username: str, password: str, backup_dir: str):
        """Initialize the DatasetManager with API credentials and backup directory."""
        self.api_base = f"{host}/api/v1"
        self.username = username
        self.password = password
        self.backup_dir = backup_dir
        self.access_token = None
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            print(f"Created backup directory: {self.backup_dir}")
    
    def authenticate(self) -> bool:
        """Authenticate to the API and get access token."""
        print("Authenticating to API...")
        
        # Get CSRF token first
        try:
            csrf_response = requests.get(f"{self.api_base}/csrf-token")
            csrf_token = csrf_response.json().get('csrf_token')
            
            # Login request with CSRF token
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRF-Token': csrf_token
            }
            
            response = requests.post(
                f"{self.api_base}/auth-token",
                data=login_data,
                headers=headers
            )
            
            if response.status_code != 200:
                print("Error: Authentication failed. Incorrect username or password.")
                print(f"Response: {response.text}")
                return False
            
            data = response.json()
            self.access_token = data.get('access_token')
            
            if not self.access_token:
                print("Error: No access token received.")
                return False
            
            print("Authentication successful")
            return True
            
        except Exception as e:
            print(f"Error during authentication: {str(e)}")
            return False
    
    def get_providers(self) -> Optional[List[Dict]]:
        """Get all providers from the API."""
        print("Fetching providers...")
        
        headers = {'Authorization': f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(f"{self.api_base}/data-providers", headers=headers)
            
            if response.status_code != 200:
                print(f"Error: Failed to fetch providers. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            providers = response.json()
            print(f"Retrieved {len(providers)} providers successfully")
            return providers
            
        except Exception as e:
            print(f"Error fetching providers: {str(e)}")
            return None
    
    def get_provider(self, provider_id: int) -> Optional[Dict]:
        """Get a specific provider from the API."""
        print(f"Fetching provider {provider_id}...")
        
        headers = {'Authorization': f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(f"{self.api_base}/data-providers/{provider_id}", headers=headers)
            
            if response.status_code != 200:
                print(f"Error: Failed to fetch provider {provider_id}. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            provider = response.json()
            print(f"Provider {provider_id} retrieved successfully")
            return provider
            
        except Exception as e:
            print(f"Error fetching provider {provider_id}: {str(e)}")
            return None
    
    def backup_provider(self, provider_id: int) -> bool:
        """Backup a specific provider to a JSON file."""
        print(f"Backing up provider {provider_id}...")
        
        provider_data = self.get_provider(provider_id)
        
        if not provider_data:
            return False
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"provider_{provider_id}_{timestamp}.json")
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(provider_data, f, indent=2)
            
            print(f"Provider {provider_id} backed up to {backup_file}")
            return True
            
        except Exception as e:
            print(f"Error backing up provider {provider_id}: {str(e)}")
            return False
    
    def backup_all_providers(self) -> bool:
        """Backup all providers to JSON files."""
        print("Backing up all providers...")
        
        providers = self.get_providers()
        
        if not providers:
            return False
        
        # Create a single backup file for all providers
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        all_providers_file = os.path.join(self.backup_dir, f"all_providers_{timestamp}.json")
        
        try:
            with open(all_providers_file, 'w') as f:
                json.dump(providers, f, indent=2)
            
            print(f"All providers backed up to {all_providers_file}")
            
            # Also backup each provider individually
            success = True
            for provider in providers:
                provider_id = provider.get('id')
                if provider_id:
                    if not self.backup_provider(provider_id):
                        success = False
            
            return success
            
        except Exception as e:
            print(f"Error backing up all providers: {str(e)}")
            return False
    
    def restore_provider(self, backup_file: str) -> bool:
        """Restore a provider from a backup file."""
        print(f"Restoring from {backup_file}...")
        
        if not os.path.exists(backup_file):
            print(f"Error: Backup file does not exist: {backup_file}")
            return False
        
        try:
            with open(backup_file, 'r') as f:
                provider_data = json.load(f)
            
            # Get CSRF token for the restore request
            csrf_response = requests.get(f"{self.api_base}/csrf-token")
            csrf_token = csrf_response.json().get('csrf_token')
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.access_token}",
                'X-CSRF-Token': csrf_token
            }
            
            # Check if it's a single provider or multiple providers
            if isinstance(provider_data, list):
                # It's a list of providers
                print(f"Restoring {len(provider_data)} providers from backup...")
                
                success = True
                for provider in provider_data:
                    provider_id = provider.get('id')
                    if not provider_id:
                        print("Warning: Provider in backup has no ID, skipping...")
                        continue
                    
                    print(f"Restoring provider {provider_id}...")
                    
                    # Check if provider exists
                    check_response = requests.get(
                        f"{self.api_base}/data-providers/{provider_id}",
                        headers={'Authorization': f"Bearer {self.access_token}"}
                    )
                    
                    if check_response.status_code == 404:
                        # Provider doesn't exist, create it
                        response = requests.post(
                            f"{self.api_base}/data-providers",
                            headers=headers,
                            json=provider
                        )
                        
                        if response.status_code not in [200, 201]:
                            print(f"Error creating provider {provider_id}: {response.text}")
                            success = False
                        else:
                            print(f"Created new provider {provider_id}")
                    else:
                        # Provider exists, update it
                        response = requests.put(
                            f"{self.api_base}/data-providers/{provider_id}",
                            headers=headers,
                            json=provider
                        )
                        
                        if response.status_code not in [200, 201]:
                            print(f"Error updating provider {provider_id}: {response.text}")
                            success = False
                        else:
                            print(f"Updated existing provider {provider_id}")
                
                return success
                
            else:
                # It's a single provider
                provider_id = provider_data.get('id')
                if not provider_id:
                    print("Error: Provider in backup has no ID")
                    return False
                
                print(f"Restoring provider {provider_id}...")
                
                # Check if provider exists
                check_response = requests.get(
                    f"{self.api_base}/data-providers/{provider_id}",
                    headers={'Authorization': f"Bearer {self.access_token}"}
                )
                
                if check_response.status_code == 404:
                    # Provider doesn't exist, create it
                    response = requests.post(
                        f"{self.api_base}/data-providers",
                        headers=headers,
                        json=provider_data
                    )
                    
                    if response.status_code not in [200, 201]:
                        print(f"Error creating provider {provider_id}: {response.text}")
                        return False
                    else:
                        print(f"Created new provider {provider_id}")
                else:
                    # Provider exists, update it
                    response = requests.put(
                        f"{self.api_base}/data-providers/{provider_id}",
                        headers=headers,
                        json=provider_data
                    )
                    
                    if response.status_code not in [200, 201]:
                        print(f"Error updating provider {provider_id}: {response.text}")
                        return False
                    else:
                        print(f"Updated existing provider {provider_id}")
                
                print("Restore completed successfully")
                return True
                
        except Exception as e:
            print(f"Error restoring from backup: {str(e)}")
            return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Backup and restore dataset providers")
    parser.add_argument('--action', required=True, choices=['backup', 'restore'],
                        help="Action to perform: backup or restore")
    parser.add_argument('--username', required=True, help="API username")
    parser.add_argument('--password', required=True, help="API password")
    parser.add_argument('--host', default="http://localhost:8000",
                        help="API host URL (default: http://localhost:8000)")
    parser.add_argument('--dir', default="./backups",
                        help="Backup directory (default: ./backups)")
    parser.add_argument('--provider', type=int, help="Provider ID (for backup)")
    parser.add_argument('--file', help="Backup file to restore from (for restore)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.action == 'restore' and not args.file:
        parser.error("--file is required when action is 'restore'")
    
    return args

def main():
    """Main function to run the script."""
    args = parse_args()
    
    # Initialize DatasetManager
    manager = DatasetManager(args.host, args.username, args.password, args.dir)
    
    # Authenticate to the API
    if not manager.authenticate():
        sys.exit(1)
    
    # Perform the requested action
    if args.action == 'backup':
        if args.provider:
            success = manager.backup_provider(args.provider)
        else:
            success = manager.backup_all_providers()
    else:  # restore
        success = manager.restore_provider(args.file)
    
    if success:
        print("Operation completed successfully")
        sys.exit(0)
    else:
        print("Operation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
