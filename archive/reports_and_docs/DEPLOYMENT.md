# GA Dashboard Deployment Guide

## Vercel Deployment

This project is configured for deployment on Vercel with the following files:

- `vercel.json` - Vercel configuration
- `runtime.txt` - Python runtime specification
- `api/index.py` - Serverless function entry point
- `requirements.txt` - Python dependencies

### Steps to Deploy

1. **Fork/Clone the repository** to your GitHub account

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Connect your GitHub account
   - Import the `georgiadashboard` repository

3. **Configure Environment Variables** in Vercel Dashboard:
   - Go to your project settings in Vercel
   - Navigate to "Environment Variables"
   - Add the following variables:

   ```
   DB_SERVER=your-sql-server-host
   DB_PORT=1433
   DB_USERNAME=your-database-username
   DB_PASSWORD=your-database-password
   DB_DATABASE=your-database-name
   TDS_VERSION=7.0
   DB_TIMEOUT=30
   DB_LOGIN_TIMEOUT=30
   FLASK_ENV=production
   ```

4. **Deploy**:
   - Vercel will automatically deploy when you push to master
   - You can also trigger manual deployments from the Vercel dashboard

### Local Development

To run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python3 unified_dashboard.py
```

The dashboard will be available at `http://localhost:9090`

### Project Structure

```
├── api/
│   └── index.py          # Vercel serverless entry point
├── templates/
│   └── unified_dashboard.html  # Main dashboard template
├── static/
│   ├── styles.css        # Dashboard styles
│   └── dashboard.js      # Dashboard JavaScript
├── unified_dashboard.py  # Main Flask application
├── database_pymssql.py   # Database connection module
├── vercel.json          # Vercel configuration
├── runtime.txt          # Python version specification
└── requirements.txt     # Python dependencies
```

### Features

- **Main Dashboard**: Sales, profit, inventory, and AR metrics
- **Sales Analytics**: Detailed sales analysis with charts
- **Daily Operations**: Transaction and payment tracking
- **AR Investigation Portal**: Customer analysis and risk assessment
- **Responsive Design**: Works on desktop and mobile devices

### Troubleshooting

1. **404 Error**: Ensure `vercel.json` is properly configured and `api/index.py` exists
2. **Database Connection Issues**: Verify environment variables are set correctly
3. **Import Errors**: Check that all dependencies are listed in `requirements.txt`
4. **Timeout Issues**: Increase `maxDuration` in `vercel.json` if needed

### Database Requirements

The dashboard connects to a SQL Server database with the following tables:
- Customer
- Transaction
- TransactionEntry
- TenderEntry
- Product
- Category
- And other business tables

See `DATABASE_DIRECTORY.md` for complete schema information. 