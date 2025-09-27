# Financial Data API - Brazilian Companies

Production API for Brazilian financial data (PETR4, VALE3) deployed on Railway.

## 🚀 Production URL

```
https://financialbreakfast-production.up.railway.app
```

## 📊 API Documentation

- **Swagger UI**: https://financialbreakfast-production.up.railway.app/api/docs
- **ReDoc**: https://financialbreakfast-production.up.railway.app/api/redoc
- **Health Check**: https://financialbreakfast-production.up.railway.app/api/health

## 🔑 API Keys

Demo keys for testing:
- **Free Tier**: `demo-key-12345` (100 requests/hour)
- **Pro Tier**: `pro-key-67890` (1000 requests/hour)
- **Enterprise**: `enterprise-key-abc` (unlimited)

## 📈 Available Data

### Companies
- **PETR4** - Petróleo Brasileiro S.A. (Petrobras)
- **VALE3** - Vale S.A.

### Financial Metrics
- `net_revenue` - Receita Líquida (Net Revenue)
- `ebitda` - EBITDA
- `net_income` - Lucro Líquido (Net Income)
- `capex` - CAPEX (Capital Expenditure)
- `net_debt` - Dívida Líquida (Net Debt)

### Historical Periods
22 quarters of data (2020-2025):
- **2025**: 1T25, 2T25
- **2024**: 1T24, 2T24, 3T24, 4T24
- **2023**: 1T23, 2T23, 3T23, 4T23
- **2022**: 1T22, 2T22, 3T22, 4T22
- **2021**: 1T21, 2T21, 3T21, 4T21
- **2020**: 1T20, 2T20, 3T20, 4T20

## 🔗 API Endpoints

### List Companies
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://financialbreakfast-production.up.railway.app/api/v1/companies
```

### Get Company Details
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://financialbreakfast-production.up.railway.app/api/v1/companies/PETR4
```

### Get Financial Data
```bash
# All data for PETR4
curl -H "X-API-Key: demo-key-12345" \
  https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4

# Filter by specific metrics
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4?metrics=ebitda,net_income"

# Filter by years
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4?years=2024,2025"
```

### Get Time Series Data
```bash
# Revenue time series for PETR4
curl -H "X-API-Key: demo-key-12345" \
  https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4/metric/net_revenue

# With limit
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4/metric/net_revenue?limit=5"
```

### Get Available Metrics
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://financialbreakfast-production.up.railway.app/api/v1/financial-data/PETR4/metrics
```

## 🏗️ Project Structure

```
financialbreakfast-api/
├── api/
│   ├── index.py                    # Main FastAPI application
│   ├── database.py                 # PostgreSQL integration (optional)
│   ├── real_data.py               # Data validation utilities
│   └── petrobras_complete_historical.json  # Historical data
├── requirements.txt                # Python dependencies
├── Procfile                       # Railway deployment config
├── railway.json                   # Railway project config
└── README.md                      # This file
```

## 🚄 Deployment

This API is deployed on Railway with:
- Automatic deployments from GitHub
- Built-in SSL/TLS
- Auto-scaling capabilities
- PostgreSQL database support (optional)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn api.index:app --reload --host 0.0.0.0 --port 8000

# Access at http://localhost:8000
```

### Environment Variables

Create a `.env` file based on `.env.example`:
```env
API_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@host/db  # Optional
```

## 📦 MCP Server Integration

This API powers the Financial Data MCP server available at:
- **Repository**: https://github.com/lucianfialho/financialbreakfast-mcp
- **DXT Download**: https://github.com/lucianfialho/financialbreakfast-mcp/releases/latest/download/financial-data-mcp.dxt

## 🔒 Authentication

All API endpoints (except `/`, `/api/health`) require an API key header:
```
X-API-Key: your-api-key
```

## ⚡ Performance

- **Response time**: <500ms (warm)
- **Uptime**: 99.9% SLA
- **Rate limits**: Based on API key tier
- **Data source**: Official quarterly reports from CVM

## 📝 License

MIT License - See repository for details

## 🤝 Support

- **Issues**: https://github.com/lucianfialho/financialbreakfast-api/issues
- **API Status**: https://financialbreakfast-production.up.railway.app/api/health