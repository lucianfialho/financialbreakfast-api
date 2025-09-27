from fastapi import FastAPI, HTTPException, Depends, Header
from typing import Optional, List
import secrets
import os

app = FastAPI(
    title="Financial Data API",
    version="2.0.0",
    description="API para dados financeiros de empresas brasileiras - PostgreSQL Edition",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Importa funções do banco de dados
try:
    from api.database import (
        test_connection,
        get_all_companies,
        get_company_by_symbol,
        get_financial_data,
        get_available_metrics,
        get_available_periods,
        get_metric_time_series
    )
    USE_DATABASE = test_connection()
except ImportError:
    try:
        from database import (
            test_connection,
            get_all_companies,
            get_company_by_symbol,
            get_financial_data,
            get_available_metrics,
            get_available_periods,
            get_metric_time_series
        )
        USE_DATABASE = test_connection()
    except ImportError:
        USE_DATABASE = False

if not USE_DATABASE:
    # Fallback para dados JSON se banco não estiver disponível
    try:
        from api.real_data import REAL_DATA
    except ImportError:
        from real_data import REAL_DATA
    SAMPLE_DATA = REAL_DATA
else:
    SAMPLE_DATA = None

# Mantém estrutura original para compatibilidade
_ORIGINAL_SAMPLE_DATA = {
    "PETR4": {
        "company": {
            "symbol": "PETR4",
            "name": "Petróleo Brasileiro S.A. - Petrobras",
            "country": "BRA",
            "sector": "Energy",
            "currency": "BRL"
        },
        "periods": [
            {
                "year": 2025,
                "quarter": 2,
                "period_label": "2T25",
                "financial_data": [
                    {
                        "metric_name": "net_revenue",
                        "metric_label": "Receita Líquida",
                        "value": 125000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "revenue"
                    },
                    {
                        "metric_name": "ebitda",
                        "metric_label": "EBITDA",
                        "value": 45000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    },
                    {
                        "metric_name": "net_income",
                        "metric_label": "Lucro Líquido",
                        "value": 28000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    },
                    {
                        "metric_name": "capex",
                        "metric_label": "Investimentos (CAPEX)",
                        "value": 15000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "investment"
                    },
                    {
                        "metric_name": "net_debt",
                        "metric_label": "Dívida Líquida",
                        "value": 85000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "debt"
                    }
                ]
            },
            {
                "year": 2025,
                "quarter": 1,
                "period_label": "1T25",
                "financial_data": [
                    {
                        "metric_name": "net_revenue",
                        "metric_label": "Receita Líquida",
                        "value": 118000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "revenue"
                    },
                    {
                        "metric_name": "ebitda",
                        "metric_label": "EBITDA",
                        "value": 42000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    },
                    {
                        "metric_name": "net_income",
                        "metric_label": "Lucro Líquido",
                        "value": 25000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    }
                ]
            },
            {
                "year": 2024,
                "quarter": 4,
                "period_label": "4T24",
                "financial_data": [
                    {
                        "metric_name": "net_revenue",
                        "metric_label": "Receita Líquida",
                        "value": 120000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "revenue"
                    },
                    {
                        "metric_name": "ebitda",
                        "metric_label": "EBITDA",
                        "value": 44000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    },
                    {
                        "metric_name": "net_income",
                        "metric_label": "Lucro Líquido",
                        "value": 26500.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    }
                ]
            }
        ]
    },
    "VALE3": {
        "company": {
            "symbol": "VALE3",
            "name": "Vale S.A.",
            "country": "BRA",
            "sector": "Mining",
            "currency": "BRL"
        },
        "periods": [
            {
                "year": 2025,
                "quarter": 2,
                "period_label": "2T25",
                "financial_data": [
                    {
                        "metric_name": "net_revenue",
                        "metric_label": "Receita Líquida",
                        "value": 45000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "revenue"
                    },
                    {
                        "metric_name": "ebitda",
                        "metric_label": "EBITDA",
                        "value": 18000.00,
                        "currency": "BRL",
                        "unit": "millions",
                        "metric_category": "profitability"
                    }
                ]
            }
        ]
    }
}

# API Keys válidas
VALID_API_KEYS = {
    "demo-key-12345": {"plan": "free", "rate_limit": 100},
    "pro-key-67890": {"plan": "pro", "rate_limit": 1000},
    "enterprise-key-abc": {"plan": "enterprise", "rate_limit": 10000}
}

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verificar API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required. Use header: X-API-Key")

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return VALID_API_KEYS[x_api_key]

# Endpoints

@app.get("/")
@app.get("/api")
def root():
    """Endpoint raiz com informações da API"""
    data_source = "PostgreSQL Database" if USE_DATABASE else "JSON File"
    return {
        "message": "🚀 Financial Data API - Powered by Vercel",
        "version": "2.0.0",
        "data_source": data_source,
        "description": "API para dados financeiros de empresas brasileiras",
        "docs": "/api/docs",
        "health": "/api/health",
        "companies": ["PETR4", "VALE3"],
        "endpoints": {
            "companies": "GET /api/v1/companies",
            "petrobras_data": "GET /api/v1/financial-data/PETR4",
            "vale_data": "GET /api/v1/financial-data/VALE3",
            "time_series": "GET /api/v1/financial-data/PETR4/metric/net_revenue"
        },
        "auth": {
            "header": "X-API-Key",
            "demo_keys": {
                "free": "demo-key-12345",
                "pro": "pro-key-67890",
                "enterprise": "enterprise-key-abc"
            }
        },
        "examples": {
            "curl_companies": "curl -H 'X-API-Key: demo-key-12345' 'https://your-app.vercel.app/api/v1/companies'",
            "curl_petrobras": "curl -H 'X-API-Key: demo-key-12345' 'https://your-app.vercel.app/api/v1/financial-data/PETR4'",
            "curl_time_series": "curl -H 'X-API-Key: demo-key-12345' 'https://your-app.vercel.app/api/v1/financial-data/PETR4/metric/net_revenue'"
        }
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Financial Data API",
        "version": "1.0.0",
        "platform": "Vercel",
        "uptime": "running"
    }

@app.post("/api/v1/auth/register")
def register_user(email: str):
    """Registrar novo usuário"""
    api_key = f"key-{secrets.token_hex(8)}"
    return {
        "email": email,
        "api_key": api_key,
        "plan": "free",
        "rate_limit_per_hour": 100,
        "message": "User registered successfully",
        "note": "This is a demo endpoint. In production, store in database."
    }

@app.get("/api/v1/companies")
def get_companies(user = Depends(verify_api_key)):
    """Listar empresas disponíveis"""
    if USE_DATABASE:
        return get_all_companies()
    else:
        companies = []
        for symbol, data in SAMPLE_DATA.items():
            companies.append(data["company"])
        return companies

@app.get("/api/v1/companies/{symbol}")
def get_company(symbol: str, user = Depends(verify_api_key)):
    """Obter detalhes de uma empresa"""
    symbol = symbol.upper()

    if USE_DATABASE:
        company = get_company_by_symbol(symbol)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return company
    else:
        if symbol not in SAMPLE_DATA:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return SAMPLE_DATA[symbol]["company"]

@app.get("/api/v1/financial-data/{symbol}")
def get_financial_data_endpoint(
    symbol: str,
    years: Optional[str] = None,
    metrics: Optional[str] = None,
    limit: int = 10,
    user = Depends(verify_api_key)
):
    """Obter dados financeiros de uma empresa"""
    symbol = symbol.upper()

    if USE_DATABASE:
        year_list = [int(y.strip()) for y in years.split(",")] if years else None
        metric_list = [m.strip() for m in metrics.split(",")] if metrics else None

        result = get_financial_data(symbol, year_list, metric_list, limit)
        if not result:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")

        result["applied_filters"] = {
            "years": years,
            "metrics": metrics,
            "limit": limit
        }
        return result
    else:
        if symbol not in SAMPLE_DATA:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")

        data = SAMPLE_DATA[symbol]
        periods = data["periods"].copy()

        # Filtros
        if years:
            year_list = [int(y.strip()) for y in years.split(",")]
            periods = [p for p in periods if p["year"] in year_list]

        if metrics:
            metric_list = [m.strip() for m in metrics.split(",")]
            for period in periods:
                period["financial_data"] = [
                    fd for fd in period["financial_data"]
                    if fd["metric_name"] in metric_list
                ]

        # Limit
        periods = periods[:limit]

        return {
            "company_symbol": data["company"]["symbol"],
            "company_name": data["company"]["name"],
            "periods": periods,
            "total_periods": len(periods),
            "applied_filters": {
                "years": years,
                "metrics": metrics,
                "limit": limit
            }
        }

@app.get("/api/v1/financial-data/{symbol}/metrics")
def get_available_metrics_endpoint(symbol: str, user = Depends(verify_api_key)):
    """Listar métricas disponíveis"""
    symbol = symbol.upper()

    if USE_DATABASE:
        metrics = get_available_metrics(symbol)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return metrics
    else:
        if symbol not in SAMPLE_DATA:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")

        metrics = set()
        for period in SAMPLE_DATA[symbol]["periods"]:
            for data in period["financial_data"]:
                metrics.add(data["metric_name"])

        return sorted(list(metrics))

@app.get("/api/v1/financial-data/{symbol}/periods")
def get_available_periods_endpoint(symbol: str, user = Depends(verify_api_key)):
    """Listar períodos disponíveis"""
    symbol = symbol.upper()

    if USE_DATABASE:
        periods = get_available_periods(symbol)
        if not periods:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")
        return periods
    else:
        if symbol not in SAMPLE_DATA:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")

        periods = []
        for period in SAMPLE_DATA[symbol]["periods"]:
            periods.append({
                "year": period["year"],
                "quarter": period["quarter"],
                "period_label": period["period_label"]
            })

        return periods

@app.get("/api/v1/financial-data/{symbol}/metric/{metric_name}")
def get_metric_time_series_endpoint(symbol: str, metric_name: str, user = Depends(verify_api_key)):
    """Obter série temporal de uma métrica"""
    symbol = symbol.upper()

    if USE_DATABASE:
        time_series = get_metric_time_series(symbol, metric_name)
        if not time_series:
            raise HTTPException(status_code=404, detail=f"Metric {metric_name} not found for {symbol}")
        return time_series
    else:
        if symbol not in SAMPLE_DATA:
            raise HTTPException(status_code=404, detail=f"Company {symbol} not found")

        time_series = []
        for period in SAMPLE_DATA[symbol]["periods"]:
            for data in period["financial_data"]:
                if data["metric_name"] == metric_name:
                    time_series.append({
                        "year": period["year"],
                        "quarter": period["quarter"],
                        "period": period["period_label"],
                        "value": data["value"],
                        "currency": data["currency"],
                        "unit": data["unit"],
                        "metric_label": data["metric_label"]
                    })

        if not time_series:
            raise HTTPException(status_code=404, detail=f"Metric {metric_name} not found for {symbol}")

        return time_series

# Handler para Vercel
def handler(request):
    """Handler para Vercel serverless"""
    return app