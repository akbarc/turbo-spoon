# Georgia Dashboard - Local Access via Tailscale

## Quick Start

Run this single command to start the dashboard:

```bash
./start_dashboard.sh
```

The script will:
- Show all available access URLs (localhost, local network, Tailscale)
- Automatically activate your Python virtual environment
- Start the Flask server on port 8080

## Access Methods

### 1. Local Access (same computer)
```
http://localhost:8080
```

### 2. Tailscale Access (from any device on your Tailscale network)
```
http://100.x.x.x:8080
```
The startup script will show your Tailscale IP (starts with 100.x.x.x)

### 3. Local Network Access
```
http://10.x.x.x:8080
```
Access from other devices on the same network

## Requirements

- Python 3.8+
- Virtual environment with dependencies installed
- Tailscale installed and running (optional, for remote access)
- SQL Server accessible at 10.1.10.105

## Starting Tailscale

If Tailscale isn't running, start it:
1. Click the Tailscale icon in your menu bar
2. Click "Connect"

Or use the command line:
```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale up
```

## Stopping the Dashboard

Press `Ctrl+C` in the terminal to stop the server

## Troubleshooting

### Can't access via Tailscale?
1. Check Tailscale is running: `/Applications/Tailscale.app/Contents/MacOS/Tailscale status`
2. Check your Tailscale IP: `ifconfig | grep "inet " | grep "100\."`
3. Make sure firewall allows port 8080

### Database connection errors?
1. Check you're on the right network (office or VPN)
2. Verify SQL Server is accessible: `telnet 10.1.10.105 1433`

### Port 8080 already in use?
Change the port in `.env`:
```
PORT=8081
```

## Configuration Files

- `.env` - Database and Flask configuration
- `run.py` - Server startup script
- `start_dashboard.sh` - Convenience startup script
