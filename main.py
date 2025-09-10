#!/usr/bin/env python3
"""
VULTR Dynamic DNS Updater
Main application entry point
"""
import sys
import time
import signal
import logging
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import ConfigManager
from vultr_api import VultrAPIClient, VultrAPIError
from ip_monitor import IPMonitor
from dns_updater import DNSUpdater

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add file handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def run_daemon(config_manager: ConfigManager):
    """Run the DNS updater as a daemon"""
    global shutdown_requested
    
    logger.info("Starting VULTR Dynamic DNS Updater daemon")
    
    # Load configuration
    try:
        config = config_manager.load()
    except FileNotFoundError:
        logger.error(f"Configuration file not found. Creating sample configuration...")
        config_manager.create_sample_config()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Get config file modification time
    config_path = Path(config_manager.config_file)
    config_mtime = config_path.stat().st_mtime if config_path.exists() else 0
    
    # Initialize components
    api_client = VultrAPIClient(config.api_key)
    ip_monitor = IPMonitor()
    dns_updater = DNSUpdater(config, api_client, ip_monitor)
    
    # Test API connection
    logger.info("Testing VULTR API connection...")
    if not api_client.test_connection():
        logger.error("Failed to connect to VULTR API. Please check your API key.")
        sys.exit(1)
    
    logger.info("API connection successful")
    logger.info("Configuration file monitoring enabled - changes will be auto-reloaded")
    
    # Initial check and update
    logger.info("Performing initial IP check and DNS update...")
    if not dns_updater.check_and_update():
        logger.warning("Initial update had some failures, will retry in next cycle")
    
    # Main loop
    logger.info(f"Starting monitoring loop (check interval: {config.check_interval} seconds)")
    consecutive_failures = 0
    config_check_counter = 0
    check_count = 0
    
    while not shutdown_requested:
        try:
            # Wait for the check interval
            for i in range(config.check_interval):
                if shutdown_requested:
                    break
                time.sleep(1)
                
                # Check config file changes every 10 seconds
                if i % 10 == 0 and config_path.exists():
                    current_mtime = config_path.stat().st_mtime
                    if current_mtime != config_mtime:
                        logger.info("Configuration file changed, reloading...")
                        try:
                            new_config = config_manager.load()
                            
                            # Update components if config loaded successfully
                            config = new_config
                            config_mtime = current_mtime
                            
                            # Re-initialize API client if API key changed
                            if api_client.api_key != config.api_key:
                                logger.info("API key changed, re-initializing API client...")
                                api_client = VultrAPIClient(config.api_key)
                                if not api_client.test_connection():
                                    logger.error("Failed to connect with new API key, keeping old configuration")
                                    config = dns_updater.config  # Restore old config
                                else:
                                    logger.info("Successfully connected with new API key")
                            
                            # Update DNS updater config
                            dns_updater.config = config
                            logger.info(f"Configuration reloaded successfully. Managing {len(config.domains)} domain(s)")
                            logger.info(f"New check interval: {config.check_interval} seconds")
                            
                        except Exception as e:
                            logger.error(f"Failed to reload configuration: {e}")
                            logger.warning("Continuing with previous configuration")
            
            if shutdown_requested:
                break
            
            # Check and update
            check_count += 1
            logger.info(f"Performing scheduled check #{check_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if dns_updater.check_and_update():
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(f"Update failed (consecutive failures: {consecutive_failures})")
                
                # If too many consecutive failures, wait longer before retry
                if consecutive_failures >= config.max_retries:
                    logger.error(f"Max consecutive failures reached ({config.max_retries}), waiting {config.retry_interval} seconds...")
                    time.sleep(config.retry_interval)
                    consecutive_failures = 0
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            shutdown_requested = True
            break
        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")
            consecutive_failures += 1
            
            if consecutive_failures >= config.max_retries:
                logger.error(f"Too many errors, waiting {config.retry_interval} seconds before retry...")
                time.sleep(config.retry_interval)
                consecutive_failures = 0
    
    logger.info("VULTR Dynamic DNS Updater stopped")


def run_once(config_manager: ConfigManager, force: bool = False):
    """Run a single update check"""
    logger.info("Running single update check")
    
    # Load configuration
    try:
        config = config_manager.load()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Initialize components
    api_client = VultrAPIClient(config.api_key)
    ip_monitor = IPMonitor()
    dns_updater = DNSUpdater(config, api_client, ip_monitor)
    
    # Test API connection
    if not api_client.test_connection():
        logger.error("Failed to connect to VULTR API")
        sys.exit(1)
    
    if force:
        logger.info("Forcing DNS update...")
        results = dns_updater.force_update()
        for result in results:
            print(str(result))
    else:
        logger.info("Checking for IP changes...")
        if dns_updater.check_and_update():
            logger.info("Update completed successfully")
        else:
            logger.error("Update failed")
            sys.exit(1)


def verify_dns(config_manager: ConfigManager):
    """Verify current DNS records"""
    logger.info("Verifying DNS records")
    
    # Load configuration
    try:
        config = config_manager.load()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Initialize components
    api_client = VultrAPIClient(config.api_key)
    ip_monitor = IPMonitor()
    dns_updater = DNSUpdater(config, api_client, ip_monitor)
    
    # Get current IP
    current_ip = ip_monitor.get_public_ip()
    print(f"\nCurrent public IP: {current_ip}")
    
    # Verify DNS records
    print("\nDNS Records:")
    print("-" * 50)
    
    results = dns_updater.verify_dns_records()
    for result in results:
        if result['exists']:
            status = "✓" if result.get('current_ip') == current_ip else "✗"
            print(f"{status} {result['domain']}: {result.get('current_ip', 'N/A')} (TTL: {result.get('ttl', 'N/A')})")
        else:
            print(f"✗ {result['domain']}: {result.get('error', 'Not found')}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='VULTR Dynamic DNS Updater')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--log-file', help='Log file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Daemon mode (default)
    daemon_parser = subparsers.add_parser('daemon', help='Run as daemon (default)')
    
    # Run once mode
    once_parser = subparsers.add_parser('once', help='Run single update check')
    once_parser.add_argument('--force', action='store_true', help='Force update even if IP unchanged')
    
    # Verify mode
    verify_parser = subparsers.add_parser('verify', help='Verify current DNS records')
    
    # Create sample config
    sample_parser = subparsers.add_parser('init', help='Create sample configuration file')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    global logger
    logger = logging.getLogger(__name__)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize config manager
    config_manager = ConfigManager(args.config)
    
    # Execute command
    command = args.command or 'daemon'
    
    if command == 'init':
        config_manager.create_sample_config()
    elif command == 'verify':
        verify_dns(config_manager)
    elif command == 'once':
        run_once(config_manager, args.force)
    else:  # daemon
        run_daemon(config_manager)


if __name__ == '__main__':
    main()