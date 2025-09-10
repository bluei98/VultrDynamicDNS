"""
DNS Update service with multi-domain support
"""
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
from config import Config, DomainConfig
from vultr_api import VultrAPIClient, VultrAPIError
from ip_monitor import IPMonitor

logger = logging.getLogger(__name__)


class DNSUpdateResult:
    """Result of DNS update operation"""
    
    def __init__(self, domain: str, subdomain: str, success: bool, 
                 old_ip: str = None, new_ip: str = None, error: str = None):
        self.domain = domain
        self.subdomain = subdomain
        self.success = success
        self.old_ip = old_ip
        self.new_ip = new_ip
        self.error = error
        self.timestamp = datetime.now()
    
    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.get_full_domain()}: {self.old_ip} -> {self.new_ip}"
        else:
            return f"✗ {self.get_full_domain()}: {self.error}"
    
    def get_full_domain(self) -> str:
        """Get the full domain name"""
        if self.subdomain:
            return f"{self.subdomain}.{self.domain}"
        return self.domain


class DNSUpdater:
    """DNS Updater service"""
    
    def __init__(self, config: Config, api_client: VultrAPIClient, ip_monitor: IPMonitor):
        self.config = config
        self.api_client = api_client
        self.ip_monitor = ip_monitor
        self.update_history: List[DNSUpdateResult] = []
        
    def update_all_domains(self, ip_address: str) -> List[DNSUpdateResult]:
        """Update all configured domains with new IP"""
        results = []
        
        logger.info(f"Updating {len(self.config.domains)} domain(s) to IP {ip_address}")
        
        for domain_config in self.config.domains:
            result = self._update_single_domain(domain_config, ip_address)
            results.append(result)
            self.update_history.append(result)
            
            # Log result
            if result.success:
                logger.info(str(result))
            else:
                logger.error(str(result))
            
            # Small delay between updates to avoid rate limiting
            if len(self.config.domains) > 1:
                time.sleep(1)
        
        return results
    
    def _update_single_domain(self, domain_config: DomainConfig, ip_address: str) -> DNSUpdateResult:
        """Update a single domain"""
        try:
            # Get current record if exists
            existing_record = self.api_client.find_dns_record(
                domain_config.domain,
                domain_config.subdomain,
                domain_config.record_type
            )
            
            old_ip = existing_record.data if existing_record else None
            
            # Update or create record
            self.api_client.update_or_create_dns_record(
                domain=domain_config.domain,
                subdomain=domain_config.subdomain,
                ip_address=ip_address,
                record_type=domain_config.record_type,
                ttl=domain_config.ttl
            )
            
            return DNSUpdateResult(
                domain=domain_config.domain,
                subdomain=domain_config.subdomain,
                success=True,
                old_ip=old_ip,
                new_ip=ip_address
            )
            
        except VultrAPIError as e:
            return DNSUpdateResult(
                domain=domain_config.domain,
                subdomain=domain_config.subdomain,
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Unexpected error updating {domain_config.full_domain}")
            return DNSUpdateResult(
                domain=domain_config.domain,
                subdomain=domain_config.subdomain,
                success=False,
                error=f"Unexpected error: {e}"
            )
    
    def check_and_update(self) -> bool:
        """Check for IP change and update if needed"""
        try:
            has_changed, new_ip = self.ip_monitor.check_ip_change()
            
            if has_changed and new_ip:
                logger.info(f"IP change detected, updating DNS records to {new_ip}")
                results = self.update_all_domains(new_ip)
                
                # Check if all updates succeeded
                success_count = sum(1 for r in results if r.success)
                total_count = len(results)
                
                if success_count == total_count:
                    logger.info(f"Successfully updated all {total_count} domain(s)")
                    self.ip_monitor.last_update = datetime.now()
                    return True
                elif success_count > 0:
                    logger.warning(f"Partially updated {success_count}/{total_count} domain(s)")
                    return False
                else:
                    logger.error(f"Failed to update any domains (0/{total_count})")
                    return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error during check and update: {e}")
            return False
    
    def force_update(self) -> List[DNSUpdateResult]:
        """Force update all domains with current IP"""
        current_ip = self.ip_monitor.get_public_ip()
        
        if not current_ip:
            logger.error("Cannot force update: unable to determine current IP")
            return []
        
        logger.info(f"Forcing update of all domains to {current_ip}")
        return self.update_all_domains(current_ip)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'current_ip': self.ip_monitor.current_ip,
            'last_check': self.ip_monitor.last_check.isoformat() if self.ip_monitor.last_check else None,
            'last_update': self.ip_monitor.last_update.isoformat() if self.ip_monitor.last_update else None,
            'domains': [d.full_domain for d in self.config.domains],
            'update_count': len(self.update_history)
        }
    
    def verify_dns_records(self) -> List[Dict[str, Any]]:
        """Verify current DNS records for all configured domains"""
        verification_results = []
        
        for domain_config in self.config.domains:
            try:
                record = self.api_client.find_dns_record(
                    domain_config.domain,
                    domain_config.subdomain,
                    domain_config.record_type
                )
                
                if record:
                    verification_results.append({
                        'domain': domain_config.full_domain,
                        'current_ip': record.data,
                        'ttl': record.ttl,
                        'type': record.type,
                        'exists': True
                    })
                else:
                    verification_results.append({
                        'domain': domain_config.full_domain,
                        'exists': False,
                        'error': 'Record not found'
                    })
                    
            except Exception as e:
                verification_results.append({
                    'domain': domain_config.full_domain,
                    'exists': False,
                    'error': str(e)
                })
        
        return verification_results