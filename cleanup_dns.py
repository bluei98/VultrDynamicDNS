#!/usr/bin/env python3
"""
Cleanup script to remove duplicate or old DNS records
"""
from config import ConfigManager
from vultr_api import VultrAPIClient
import sys

def main():
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load()
    
    # Initialize API client
    api_client = VultrAPIClient(config.api_key)
    
    domain = config.domains[0].domain
    print(f"Cleaning up DNS records for: {domain}")
    print("=" * 50)
    
    # List all DNS records
    records = api_client.list_dns_records(domain)
    
    # Find all A records with empty name (root domain)
    a_records = [r for r in records if r.type == 'A' and r.name == '']
    
    if len(a_records) <= 1:
        print("No duplicate A records found.")
        return
    
    print(f"Found {len(a_records)} A records for root domain:")
    for i, record in enumerate(a_records):
        print(f"{i+1}. ID: {record.id}")
        print(f"   IP: {record.data}")
        print(f"   TTL: {record.ttl}")
        print()
    
    if len(a_records) > 1:
        print("Multiple A records detected!")
        print("Which record would you like to keep?")
        
        while True:
            try:
                choice = input(f"Enter number (1-{len(a_records)}) or 'cancel': ").strip()
                if choice.lower() == 'cancel':
                    print("Operation cancelled.")
                    return
                
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(a_records):
                    break
                else:
                    print(f"Please enter a number between 1 and {len(a_records)}")
            except ValueError:
                print("Please enter a valid number or 'cancel'")
        
        keep_record = a_records[choice_num]
        delete_records = [r for r in a_records if r.id != keep_record.id]
        
        print(f"\nKeeping record: {keep_record.data} (ID: {keep_record.id})")
        print("Deleting records:")
        for record in delete_records:
            print(f"  - {record.data} (ID: {record.id})")
        
        confirm = input("\nConfirm deletion? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Operation cancelled.")
            return
        
        # Delete old records
        for record in delete_records:
            try:
                api_client.delete_dns_record(domain, record.id)
                print(f"✓ Deleted record: {record.data}")
            except Exception as e:
                print(f"✗ Failed to delete record {record.data}: {e}")
        
        print("\nCleanup completed!")

if __name__ == '__main__':
    main()