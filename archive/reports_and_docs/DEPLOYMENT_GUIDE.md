# 🚀 Georgia Auto Dashboard - Deployment Guide

## Overview
This guide covers deployment options for the Georgia Auto Dashboard application across different environments.

## 🏠 Local Development Deployment

### Prerequisites
- Python 3.8 or higher
- Access to SQL Server 2008 R2 database (10.1.10.105)
- Network connectivity to database server

### Quick Start
```bash
# 1. Clone/navigate to project directory
cd georgiadashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional)
cp env.example .env
# Edit .env with your database credentials if different from defaults

# 4. Run the application
python3 unified_dashboard.py
```

### Access
- **URL:** http://localhost:8080
- **API Base:** http://localhost:8080/api/
- **Health Check:** http://localhost:8080/api/health

## ☁️ Vercel Serverless Deployment

### Configuration Files
The application is pre-configured for Vercel deployment:

- `vercel.json` - Deployment configuration
- `api/index.py` - Serverless function entry point
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification

### Deployment Steps

#### Option 1: Vercel CLI
```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy from project directory
vercel

# 4. Follow prompts for project setup
```

#### Option 2: GitHub Integration
1. Push code to GitHub repository
2. Connect repository to Vercel dashboard
3. Configure build settings:
   - **Framework Preset:** Other
   - **Build Command:** (leave empty)
   - **Output Directory:** (leave empty)
   - **Install Command:** `pip install -r requirements.txt`

### Important Limitations
⚠️ **Database Access**: Vercel serverless functions cannot access local network databases (10.1.10.105)

**Solutions:**
- **Cloud Database Migration**: Move to Azure SQL Database, AWS RDS, or similar
- **VPN Tunnel**: Set up secure tunnel for cloud-to-local database access
- **Hybrid Approach**: Use Vercel for static content, local server for database operations

## 🐳 Docker Deployment

### Dockerfile
Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    freetds-dev \
    freetds-bin \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8080

CMD ["python3", "unified_dashboard.py"]
```

### Docker Compose (Optional)
Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DB_SERVER=10.1.10.105
      - DB_DATABASE=YourDatabase
      - DB_USERNAME=YourUsername
      - DB_PASSWORD=YourPassword
    network_mode: host  # For local database access
```

### Deploy with Docker
```bash
# Build and run
docker build -t ga-dashboard .
docker run -p 8080:8080 ga-dashboard

# Or use Docker Compose
docker-compose up --build
```

## 🖥️ Traditional Server Deployment

### WSGI Server (Gunicorn)
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn --bind 0.0.0.0:8080 --workers 4 unified_dashboard:app
```

### Apache/Nginx Proxy
Configure reverse proxy to forward requests to the Python application.

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔧 Environment Configuration

### Environment Variables
Create `.env` file with:

```bash
# Database Configuration
DB_SERVER=10.1.10.105
DB_DATABASE=YourDatabase
DB_USERNAME=YourUsername  
DB_PASSWORD=YourPassword
DB_DRIVER=SQL Server

# Application Configuration  
FLASK_ENV=production
FLASK_DEBUG=false
PORT=8080

# Optional: Analytics Configuration
ENABLE_CACHING=true
CACHE_TIMEOUT=300
```

### Production Considerations

#### Security
- [ ] Use environment variables for sensitive data
- [ ] Enable HTTPS in production
- [ ] Configure CORS policies
- [ ] Implement rate limiting
- [ ] Regular security updates

#### Performance  
- [ ] Enable query result caching
- [ ] Configure database connection pooling
- [ ] Implement CDN for static assets
- [ ] Set up monitoring and logging
- [ ] Database query optimization

#### Reliability
- [ ] Set up health checks
- [ ] Configure automatic restarts
- [ ] Implement graceful shutdowns  
- [ ] Database backup strategy
- [ ] Error monitoring and alerting

## 📊 Monitoring and Maintenance

### Health Checks
The application provides several monitoring endpoints:

- `/api/health` - Application health status
- `/api/database/status` - Database connectivity
- `/api/serverless-status` - Deployment environment info

### Logging
Monitor application logs for:
- Database connection issues
- Query execution errors  
- API endpoint performance
- User access patterns

### Performance Monitoring
Track key metrics:
- Response times for API endpoints
- Database query execution times
- Memory and CPU usage
- Active user sessions

## 🔍 Troubleshooting

### Common Deployment Issues

#### Port Already in Use
```bash
# Find and kill process using port 8080
lsof -ti:8080 | xargs kill -9
```

#### Database Connection Failures
1. Verify network connectivity to database server
2. Check database credentials in environment variables
3. Confirm SQL Server authentication is enabled
4. Test database connection independently

#### Module Import Errors
1. Ensure all dependencies are in `requirements.txt`
2. Check Python version compatibility
3. Verify module paths and import statements
4. Review virtual environment setup

#### Static File Serving Issues
1. Check Flask static file configuration
2. Verify file permissions on static directory
3. Configure web server for static file serving
4. Review CORS settings for cross-origin requests

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# 1. Backup current version
cp -r georgiadashboard georgiadashboard_backup

# 2. Pull updates
git pull origin main

# 3. Update dependencies  
pip install -r requirements.txt --upgrade

# 4. Restart application
python3 unified_dashboard.py
```

### Database Maintenance
- Regular backup of historical cache files
- Monitor database performance and query optimization
- Update statistics and rebuild indexes as needed
- Review and archive old transaction data

---

**Need Help?** Check the troubleshooting section in `TECHNICAL_DOCUMENTATION.md` or review application logs for specific error messages.