# VULTR Dynamic DNS Updater

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PM2 Compatible](https://img.shields.io/badge/PM2-compatible-orange)](https://pm2.keymetrics.io/)

🔄 **Automatic Dynamic DNS updater for VULTR** - Keep your DNS records synchronized with your changing IP address. Perfect for home servers, dynamic IP environments, and self-hosted services.

## ✨ Key Features

- 🌐 **Multi-Domain Support** - Manage multiple domains and subdomains
- 🔍 **Reliable IP Detection** - Multiple fallback IP detection services
- ♻️ **Auto-Configuration Reload** - Apply changes without restart
- 📊 **Comprehensive Logging** - Detailed logs with rotation support
- 🚀 **PM2 Integration** - Production-ready process management
- 🛡️ **Error Recovery** - Automatic retry and fallback mechanisms

## Installation

### 1. Requirements

- Python 3.7 or higher
- VULTR API key

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Create Configuration File

Create a sample configuration file:

```bash
python main.py init
```

### 2. Edit Configuration File

Copy `config.sample.json` to `config.json` and edit it:

```json
{
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
```

#### Configuration Options

- **api_key**: VULTR API key (get it from https://my.vultr.com/settings/#settingsapi)
- **domains**: List of domains to manage
  - **domain**: Base domain (e.g., example.com)
  - **subdomain**: Subdomain (empty string for root domain)
  - **record_type**: DNS record type (default: "A")
  - **ttl**: Time To Live in seconds (default: 300)
- **check_interval**: IP check interval in seconds (default: 300)
- **retry_interval**: Retry interval on failure in seconds (default: 60)
- **max_retries**: Maximum number of retries (default: 3)

## Usage

### Automatic Configuration Reload

The program automatically detects and applies configuration file changes while running:

- **Configuration File Monitoring**: Checks `config.json` for changes every 10 seconds
- **Automatic Reload**: Automatically applies new settings when file is modified
- **API Key Change Detection**: Tests new connection when API key changes
- **Domain List Updates**: Immediately reflects domain additions/removals
- **Error Recovery**: Automatically reverts to previous settings on invalid configuration

> **Note**: Maintain valid JSON format when editing the configuration file.

### Daemon Mode (Default)

Runs continuously in the background, periodically checking and updating IP:

```bash
python main.py daemon
```

Or simply:

```bash
python main.py
```

### Single Run Mode

Checks once and exits:

```bash
python main.py once
```

Force update (updates even if IP hasn't changed):

```bash
python main.py once --force
```

### Verify DNS Records

Check current DNS records:

```bash
python main.py verify
```

### Logging Options

Set log level:

```bash
python main.py --log-level DEBUG daemon
```

Save logs to file:

```bash
python main.py --log-file logs/vultr-ddns.log daemon
```

### Custom Configuration File

```bash
python main.py --config /path/to/custom-config.json daemon
```

## Run as Service

### PM2 (Recommended - Node.js Process Manager)

PM2 provides easy process management, automatic restart, and log management.

#### Install PM2

```bash
# Install via npm
npm install -g pm2

# Or install via yarn
yarn global add pm2
```

#### PM2 Log Rotation Setup

PM2 accumulates logs by default, so log rotation setup is necessary:

```bash
# Automatic log rotation setup (Linux/Mac)
./pm2-logrotate-setup.sh

# Automatic log rotation setup (Windows)
pm2-logrotate-setup.bat

# Or manual setup
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 30
pm2 set pm2-logrotate:compress true
```

#### Register Service with PM2

1. Create PM2 configuration file (`ecosystem.config.js`):

```javascript
module.exports = {
  apps: [{
    name: 'vultr-ddns',
    script: 'python3',
    args: 'main.py daemon',
    cwd: '/path/to/VultrDynamicDNS',
    interpreter: '/usr/bin/python3',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      PYTHONUNBUFFERED: 1
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_file: 'logs/pm2-combined.log',
    time: true
  }]
};
```

2. Start service with PM2:

```bash
# Start using configuration file
pm2 start ecosystem.config.js

# Or run directly
pm2 start main.py --name vultr-ddns --interpreter python3 -- daemon
```

3. PM2 management commands:

```bash
# Check service status
pm2 status vultr-ddns

# View logs
pm2 logs vultr-ddns

# Restart service
pm2 restart vultr-ddns

# Stop service
pm2 stop vultr-ddns

# Delete service
pm2 delete vultr-ddns

# Monitor (real-time)
pm2 monit
```

4. Configure automatic startup on system boot:

```bash
# Generate startup script
pm2 startup

# Save current PM2 process list
pm2 save

# Restore saved process list
pm2 resurrect
```

5. PM2 Web Dashboard (Optional):

```bash
# Connect PM2 Plus monitoring (free plan available)
pm2 link <secret_key> <public_key>

# Or local web interface
pm2 install pm2-web
pm2 web
```

### Linux (systemd)

1. Create service file:

```bash
sudo nano /etc/systemd/system/vultr-ddns.service
```

2. Add the following content:

```ini
[Unit]
Description=VULTR Dynamic DNS Updater
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/VultrDynamicDNS
ExecStart=/usr/bin/python3 /path/to/VultrDynamicDNS/main.py daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vultr-ddns
sudo systemctl start vultr-ddns
```

4. Check status:

```bash
sudo systemctl status vultr-ddns
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Select "Create Basic Task"
3. Enter name and description
4. Trigger: "When the computer starts"
5. Action: "Start a program"
6. Program: Path to `python.exe`
7. Arguments: `C:\path\to\VultrDynamicDNS\main.py daemon`
8. Start in: `C:\path\to\VultrDynamicDNS`

## Program Structure

- **main.py**: Main entry point
- **config.py**: Configuration management
- **vultr_api.py**: VULTR API client
- **ip_monitor.py**: IP address monitoring
- **dns_updater.py**: DNS update logic

## Troubleshooting

### API Key Errors

- Verify API key is active in VULTR dashboard
- Check if API key has DNS permissions

### IP Detection Failure

- Check internet connection
- Verify firewall is not blocking outbound HTTPS connections

### DNS Update Failure

- Verify domain is using VULTR DNS
- Check if domain configuration is correct

## License

MIT License