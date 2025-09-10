"""
VULTR API Client for DNS management
"""
import requests
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DNSRecord:
    """DNS Record representation"""
    id: str
    type: str
    name: str
    data: str
    ttl: int
    priority: int = None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'DNSRecord':
        """Create DNSRecord from API response"""
        return cls(
            id=data['id'],
            type=data['type'],
            name=data['name'],
            data=data['data'],
            ttl=data['ttl'],
            priority=data.get('priority')
        )


class VultrAPIError(Exception):
    """VULTR API Error"""
    pass


class VultrAPIClient:
    """VULTR API Client for DNS operations"""
    
    BASE_URL = "https://api.vultr.com/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"VULTR API error: {e}"
            if response.content:
                try:
                    error_data = response.json()
                    error_msg = f"VULTR API error: {error_data.get('error', str(e))}"
                except:
                    pass
            logger.error(error_msg)
            raise VultrAPIError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)
            raise VultrAPIError(error_msg)
    
    def list_domains(self) -> List[Dict[str, Any]]:
        """List all domains"""
        response = self._request('GET', '/domains')
        return response.get('domains', [])
    
    def get_domain(self, domain: str) -> Dict[str, Any]:
        """Get domain information"""
        return self._request('GET', f'/domains/{domain}')
    
    def list_dns_records(self, domain: str) -> List[DNSRecord]:
        """List all DNS records for a domain"""
        response = self._request('GET', f'/domains/{domain}/records')
        records = response.get('records', [])
        return [DNSRecord.from_api_response(r) for r in records]
    
    def get_dns_record(self, domain: str, record_id: str) -> DNSRecord:
        """Get a specific DNS record"""
        response = self._request('GET', f'/domains/{domain}/records/{record_id}')
        return DNSRecord.from_api_response(response['record'])
    
    def create_dns_record(self, domain: str, name: str, record_type: str, 
                         data: str, ttl: int = 300, priority: int = None) -> DNSRecord:
        """Create a new DNS record"""
        payload = {
            'name': name,
            'type': record_type,
            'data': data,
            'ttl': ttl
        }
        
        if priority is not None:
            payload['priority'] = priority
        
        response = self._request('POST', f'/domains/{domain}/records', json=payload)
        logger.info(f"Created DNS record: {name}.{domain} -> {data}")
        return DNSRecord.from_api_response(response['record'])
    
    def update_dns_record(self, domain: str, record_id: str, 
                         data: str = None, name: str = None, 
                         ttl: int = None, priority: int = None) -> None:
        """Update an existing DNS record"""
        payload = {}
        
        if data is not None:
            payload['data'] = data
        if name is not None:
            payload['name'] = name
        if ttl is not None:
            payload['ttl'] = ttl
        if priority is not None:
            payload['priority'] = priority
        
        if not payload:
            logger.warning("No fields to update")
            return
        
        self._request('PATCH', f'/domains/{domain}/records/{record_id}', json=payload)
        logger.info(f"Updated DNS record {record_id} for domain {domain}")
    
    def delete_dns_record(self, domain: str, record_id: str) -> None:
        """Delete a DNS record"""
        self._request('DELETE', f'/domains/{domain}/records/{record_id}')
        logger.info(f"Deleted DNS record {record_id} for domain {domain}")
    
    def find_dns_record(self, domain: str, subdomain: str, 
                       record_type: str = 'A') -> Optional[DNSRecord]:
        """Find a specific DNS record by subdomain and type"""
        records = self.list_dns_records(domain)
        
        # Normalize subdomain for comparison - VULTR uses different formats
        target_names = []
        if subdomain:
            target_names = [subdomain, f"{subdomain}.{domain}", f"{subdomain}."]
        else:
            # For root domain, VULTR typically uses empty string
            target_names = ['', '@', domain, f"{domain}."]
        
        logger.debug(f"Searching for DNS record: domain={domain}, subdomain='{subdomain}', type={record_type}")
        logger.debug(f"Target names to match: {target_names}")
        
        for record in records:
            logger.debug(f"Checking record: name='{record.name}', type={record.type}, data={record.data}")
            if record.type == record_type and record.name in target_names:
                logger.info(f"Found existing record: {record.name} -> {record.data} (ID: {record.id})")
                return record
        
        logger.info(f"No existing record found for {subdomain or '@'}.{domain} ({record_type})")
        return None
    
    def update_or_create_dns_record(self, domain: str, subdomain: str, 
                                   ip_address: str, record_type: str = 'A', 
                                   ttl: int = 300) -> None:
        """Update existing DNS record or create new one"""
        existing_record = self.find_dns_record(domain, subdomain, record_type)
        
        # Normalize subdomain
        name = subdomain if subdomain else '@'
        
        if existing_record:
            if existing_record.data != ip_address:
                # Use existing record's TTL if updating
                effective_ttl = existing_record.ttl
                if ttl != existing_record.ttl:
                    logger.info(f"Using existing TTL {existing_record.ttl} instead of configured {ttl} for {name}.{domain}")
                
                self.update_dns_record(domain, existing_record.id, data=ip_address)
                logger.info(f"Updated {name}.{domain}: {existing_record.data} -> {ip_address} (TTL: {effective_ttl})")
            else:
                logger.debug(f"No update needed for {name}.{domain} (IP unchanged: {ip_address})")
        else:
            # For new records, check if there are other records with different TTL
            try:
                all_records = self.list_dns_records(domain)
                if all_records:
                    # Use the TTL from the first existing record to maintain consistency
                    first_record_ttl = all_records[0].ttl
                    if ttl != first_record_ttl:
                        logger.info(f"Using existing domain TTL {first_record_ttl} instead of configured {ttl} for new record {name}.{domain}")
                        ttl = first_record_ttl
                
                self.create_dns_record(domain, name, record_type, ip_address, ttl)
                logger.info(f"Created new record {name}.{domain} -> {ip_address} (TTL: {ttl})")
                
            except VultrAPIError as e:
                # If we can't get existing records, try with configured TTL first
                # then retry with common TTL values if it fails
                logger.warning(f"Could not check existing records for TTL consistency: {e}")
                try:
                    self.create_dns_record(domain, name, record_type, ip_address, ttl)
                    logger.info(f"Created new record {name}.{domain} -> {ip_address} (TTL: {ttl})")
                except VultrAPIError as ttl_error:
                    if "TTL" in str(ttl_error):
                        # Try common TTL values
                        common_ttls = [3600, 1800, 7200, 300, 600]
                        for try_ttl in common_ttls:
                            if try_ttl != ttl:  # Don't retry the same TTL
                                try:
                                    logger.info(f"Retrying with TTL {try_ttl} for {name}.{domain}")
                                    self.create_dns_record(domain, name, record_type, ip_address, try_ttl)
                                    logger.info(f"Created new record {name}.{domain} -> {ip_address} (TTL: {try_ttl})")
                                    return
                                except VultrAPIError:
                                    continue
                    
                    # If all attempts failed, re-raise the original error
                    raise ttl_error
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            account = self._request('GET', '/account')
            logger.info(f"API connection successful. Account: {account.get('account', {}).get('email', 'Unknown')}")
            return True
        except VultrAPIError as e:
            logger.error(f"API connection failed: {e}")
            return False