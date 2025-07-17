# RetroPie System State Management Specification

## Overview
Enhanced system state tracking for RetroPie installations, expanding beyond gaming to include comprehensive system administration capabilities while maintaining focus on emulation.

## Schema Version
- **Current**: v1.0 (gaming-focused)
- **Proposed**: v2.0 (comprehensive system state)

## Core Schema Structure

### System Information
```json
"system": {
  "hostname": "raspberrypi",
  "cpu_temperature": 46.6,
  "memory_total": "15.8GB",
  "memory_used": "2.1GB",
  "uptime": "2 days, 14:23:45",
  "load_average": [0.5, 0.3, 0.2],
  "last_updated": "2025-07-17T16:56:11"
}
```

### Hardware Configuration
```json
"hardware": {
  "model": "Raspberry Pi 5 Model B Rev 1.1",
  "revision": "e04171",
  "storage": [
    {
      "device": "/dev/sda1",
      "mount": "/",
      "size": "500GB",
      "used": "45GB",
      "type": "SSD"
    }
  ],
  "gpio_usage": {
    "614": "fan_control",
    "573": "argon_button"
  },
  "cooling": {
    "fan_active": true,
    "case": "Argon Neo V5",
    "fan_speed": 65
  }
}
```

### Network Configuration
```json
"network": {
  "interfaces": [
    {
      "name": "eth0",
      "ip": "192.168.1.100",
      "status": "up",
      "speed": "1000Mbps"
    },
    {
      "name": "wlan0",
      "ip": "192.168.1.101",
      "status": "up",
      "ssid": "HomeNetwork",
      "signal": -45
    }
  ],
  "primary_interface": "eth0"
}
```

### Software Environment
```json
"software": {
  "os": {
    "name": "Debian GNU/Linux",
    "version": "12 (bookworm)",
    "kernel": "6.1.0-rpi7-rpi-v8"
  },
  "python": {
    "version": "3.13.5",
    "path": "/usr/bin/python3"
  },
  "docker": {
    "version": "28.3.2",
    "status": "active",
    "containers": ["mealie"]
  },
  "retropie": {
    "version": "4.8.5",
    "status": "inactive"
  }
}
```

### System Services
```json
"services": {
  "systemd": [
    {
      "name": "docker.service",
      "status": "active",
      "enabled": true,
      "description": "Docker Application Container Engine"
    },
    {
      "name": "mealie.service",
      "status": "active",
      "enabled": true,
      "description": "Mealie Recipe Manager"
    }
  ],
  "docker_containers": [
    {
      "name": "mealie",
      "image": "ghcr.io/mealie-recipes/mealie:latest",
      "status": "running",
      "ports": ["9925:9000"],
      "uptime": "2 hours"
    }
  ]
}
```

### Gaming Configuration (Existing + Enhanced)
```json
"gaming": {
  "emulators": [
    {
      "name": "mupen64plus",
      "system": "n64",
      "version": "2.5.9",
      "rom_count": 45,
      "status": "configured"
    }
  ],
  "controllers": [
    {
      "name": "PlayStation 5 Controller",
      "type": "ps5",
      "connection": "usb",
      "configured": true
    }
  ],
  "roms": {
    "directories": ["/home/pi/RetroPie/roms"],
    "systems": {
      "n64": {"count": 45, "size": "2.1GB"},
      "gba": {"count": 120, "size": "890MB"}
    },
    "total_size": "15.6GB"
  }
}
```

### User Notes & History
```json
"notes": [
  {
    "date": "2025-07-17T16:50:00",
    "action": "install_mealie",
    "description": "Installed Mealie recipe manager via Docker on port 9925",
    "user": "nbhansen"
  },
  {
    "date": "2025-07-17T15:30:00",
    "action": "configure_fan",
    "description": "Configured fan control for Pi 5 + Argon case",
    "user": "nbhansen"
  }
]
```

## Implementation Considerations

### Performance
- Cache expensive operations (hardware detection, service status)
- Incremental updates for frequently changing data
- Configurable scan intervals

### Extensibility
- Plugin system for custom state collectors
- JSON schema validation
- Backward compatibility with v1.0

### Security
- Sanitize sensitive information (passwords, API keys)
- User permission levels for different state sections
- Audit trail for state modifications

## API Operations

### Core Operations
- `load()` - Retrieve cached state
- `save(force_scan=false)` - Update state with optional full scan
- `update(path, value)` - Modify specific field
- `compare()` - Detect configuration drift

### New Operations
- `export()` - Export state for backup/migration
- `import(state)` - Import state from backup
- `diff(other_state)` - Compare with another state
- `watch(path)` - Monitor specific field changes

## Use Cases

### System Administration
- Monitor service health and resource usage
- Track configuration changes over time
- Automated alerting for issues
- Backup and restore configurations

### Gaming Management
- ROM collection management
- Controller configuration tracking
- Performance monitoring per emulator
- Save state backup coordination

### Development & Debugging
- System state snapshots before/after changes
- Configuration drift detection
- Automated testing of system states
- Documentation generation