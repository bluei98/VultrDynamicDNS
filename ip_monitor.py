"""
IP Address monitoring service
"""
import requests
import socket
import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class IPMonitor:
    """Monitor and detect IP address changes"""
    
    # Public IP detection services
    IP_SERVICES = [
        'https://api.ipify.org',
        'https://ipapi.co/ip',
        'https://checkip.amazonaws.com',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://ident.me'
    ]
    
    def __init__(self):
        self.current_ip: Optional[str] = None
        self.last_check: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        
    def get_public_ip(self) -> Optional[str]:
        """Get current public IP address"""
        for service in self.IP_SERVICES:
            try:
                logger.debug(f"Checking IP using {service}")
                response = requests.get(service, timeout=5)
                response.raise_for_status()
                
                ip = response.text.strip()
                
                # Validate IP format
                if self._validate_ip(ip):
                    logger.debug(f"Got IP {ip} from {service}")
                    return ip
                else:
                    logger.warning(f"Invalid IP format from {service}: {ip}")
                    
            except requests.RequestException as e:
                logger.warning(f"Failed to get IP from {service}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error getting IP from {service}: {e}")
                continue
        
        logger.error("Failed to get public IP from all services")
        return None
    
    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            # Try to parse as IPv4
            parts = ip.split('.')
            if len(parts) == 4:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False
                return True
            
            # Try to parse as IPv6
            socket.inet_pton(socket.AF_INET6, ip)
            return True
            
        except (ValueError, socket.error):
            return False
    
    def check_ip_change(self) -> tuple[bool, Optional[str]]:
        """
        Check if IP has changed
        Returns: (has_changed, new_ip)
        """
        self.last_check = datetime.now()
        new_ip = self.get_public_ip()
        
        if new_ip is None:
            logger.error("Could not determine current IP address")
            return False, None
        
        if self.current_ip is None:
            # First run
            self.current_ip = new_ip
            logger.info(f"Initial IP address: {new_ip}")
            return True, new_ip
        
        if new_ip != self.current_ip:
            old_ip = self.current_ip
            self.current_ip = new_ip
            logger.info(f"IP address changed: {old_ip} -> {new_ip}")
            return True, new_ip
        
        logger.info(f"IP address unchanged: {new_ip}")
        return False, new_ip
    
    def get_local_ips(self) -> List[str]:
        """Get all local IP addresses (for debugging)"""
        local_ips = []
        
        try:
            # Get hostname
            hostname = socket.gethostname()
            
            # Get all IPs for hostname
            ips = socket.gethostbyname_ex(hostname)[2]
            local_ips.extend(ips)
            
            # Also try to get IP by connecting to external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip not in local_ips:
                    local_ips.append(local_ip)
            except:
                pass
            finally:
                s.close()
                
        except Exception as e:
            logger.warning(f"Error getting local IPs: {e}")
        
        return local_ips
    
    def reset(self) -> None:
        """Reset the monitor state"""
        self.current_ip = None
        self.last_check = None
        self.last_update = None
        logger.info("IP monitor state reset")