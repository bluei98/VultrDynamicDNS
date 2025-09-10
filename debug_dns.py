#!/usr/bin/env python3
"""
Debug script to list all DNS records
"""
from config import ConfigManager
from vultr_api import VultrAPIClient

def main():
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load()
    
    # Initialize API client
    api_client = VultrAPIClient(config.api_key)
    
    print(f"Domain: {config.domains[0].domain}")
    print(f"Subdomain: '{config.domains[0].subdomain}'")
    print("=" * 50)
    
    # List all DNS records
    records = api_client.list_dns_records(config.domains[0].domain)
    
    print("All DNS records:")
    for i, record in enumerate(records):
        print(f"{i+1}. ID: {record.id}")
        print(f"   Name: '{record.name}'")
        print(f"   Type: {record.type}")
        print(f"   Data: {record.data}")
        print(f"   TTL: {record.ttl}")
        print()

if __name__ == '__main__':
    main()