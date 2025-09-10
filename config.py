"""
Configuration management for VULTR Dynamic DNS Updater
"""
import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DomainConfig:
    """Configuration for a single domain"""
    domain: str
    subdomain: str
    record_type: str = 'A'
    ttl: int = 300
    
    @property
    def full_domain(self) -> str:
        """Get the full domain name"""
        if self.subdomain:
            return f"{self.subdomain}.{self.domain}"
        return self.domain


@dataclass
class Config:
    """Main configuration"""
    api_key: str
    domains: List[DomainConfig]
    check_interval: int = 300  # seconds
    retry_interval: int = 60  # seconds
    max_retries: int = 3
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary"""
        domains = [DomainConfig(**d) for d in data.get('domains', [])]
        return cls(
            api_key=data['api_key'],
            domains=domains,
            check_interval=data.get('check_interval', 300),
            retry_interval=data.get('retry_interval', 60),
            max_retries=data.get('max_retries', 3)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary"""
        return {
            'api_key': self.api_key,
            'domains': [asdict(d) for d in self.domains],
            'check_interval': self.check_interval,
            'retry_interval': self.retry_interval,
            'max_retries': self.max_retries
        }


class ConfigManager:
    """Manage application configuration"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config: Config = None
        
    def load(self) -> Config:
        """Load configuration from file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.config = Config.from_dict(data)
            logger.info(f"Configuration loaded from {self.config_file}")
            logger.info(f"Managing {len(self.config.domains)} domain(s)")
            
            return self.config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}")
    
    def save(self, config: Config = None) -> None:
        """Save configuration to file"""
        if config:
            self.config = config
        
        if not self.config:
            raise ValueError("No configuration to save")
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Configuration saved to {self.config_file}")
    
    def create_sample_config(self) -> None:
        """Create a sample configuration file"""
        sample_config = {
            "api_key": "YOUR_VULTR_API_KEY_HERE",
            "domains": [
                {
                    "domain": "example.com",
                    "subdomain": "",
                    "record_type": "A",
                    "ttl": 300
                },
                {
                    "domain": "example.com",
                    "subdomain": "blog",
                    "record_type": "A",
                    "ttl": 300
                }
            ],
            "check_interval": 300,
            "retry_interval": 60,
            "max_retries": 3
        }
        
        sample_file = 'config.sample.json'
        with open(sample_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sample configuration created: {sample_file}")
        print(f"Sample configuration file created: {sample_file}")
        print(f"Please copy it to {self.config_file} and update with your settings.")