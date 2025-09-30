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
        "service": "Financial Data API with Semantic Search",
        "version": "2.1.1",  # Force redeploy
        "platform": "Railway",
        "features": {
            "financial_data": "✅ Available",
            "semantic_search": "✅ Available" if SEMANTIC_SEARCH_AVAILABLE else "⚠️ Dependencies required",
            "audio_processing": "✅ Available" if SEMANTIC_SEARCH_AVAILABLE else "⚠️ Dependencies required"
        },
        "uptime": "running",
        "semantic_search_debug": SEMANTIC_SEARCH_AVAILABLE  # Debug info
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

# === SEMANTIC SEARCH ENDPOINTS ===

try:
    # Try to use optimized ML semantic search first
    from api.semantic_search_ml import SemanticSearchService
    semantic_search = SemanticSearchService()
    SEMANTIC_SEARCH_AVAILABLE = True
    print("✅ Using optimized ML semantic search")

except ImportError as e:
    try:
        # Fallback to original ML version
        print(f"⚠️ Optimized ML not available: {e}")
        from api.semantic_search import SemanticSearchService
        semantic_search = SemanticSearchService()
        SEMANTIC_SEARCH_AVAILABLE = True
        print("✅ Using standard ML semantic search")

    except ImportError as e2:
        # Fallback to lightweight text search
        try:
            print(f"⚠️ ML dependencies not available: {e2}")
            print("📋 Using lightweight text search instead...")
            from api.semantic_search_lite import SemanticSearchService
            semantic_search = SemanticSearchService()
            SEMANTIC_SEARCH_AVAILABLE = True
            print("✅ Lightweight semantic search ready")
        except ImportError as e3:
            print(f"❌ Semantic search completely unavailable: {e3}")
            SEMANTIC_SEARCH_AVAILABLE = False

# Import admin router
try:
    from api.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1")
    print("✅ Admin endpoints available")
except ImportError as e:
    print(f"⚠️ Admin endpoints not available: {e}")

# Optional imports for audio processing
try:
    from api.audio_downloader import AudioDownloader
    from api.transcription_service import TranscriptionService
    from api.analysis_service import AnalysisService
except ImportError:
    pass  # Audio processing not available, but search still works

@app.get("/api/v1/earnings-calls/search")
def semantic_search_endpoint(
    query: str,
    company: Optional[str] = None,
    limit: int = 10,
    threshold: float = 0.5,
    user = Depends(verify_api_key)
):
    """
    Busca semântica em transcrições de teleconferências

    Args:
        query: Texto da consulta
        company: Filtro por empresa (opcional)
        limit: Número máximo de resultados (padrão: 10)
        threshold: Limiar de similaridade 0-1 (padrão: 0.5)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Semantic search service not available. Please install required dependencies."
        )

    try:
        results = semantic_search.search_similar_segments(
            query=query,
            company_symbol=company.upper() if company else None,
            limit=limit,
            threshold=threshold
        )

        return {
            "query": query,
            "filters": {
                "company": company,
                "threshold": threshold
            },
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/v1/earnings-calls/search-topic")
def search_by_topic_endpoint(
    topic: str,
    company: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 20,
    user = Depends(verify_api_key)
):
    """
    Busca por tópico/palavra-chave nas transcrições

    Args:
        topic: Tópico ou palavra-chave
        company: Filtro por empresa (opcional)
        year: Filtro por ano (opcional)
        limit: Número máximo de resultados (padrão: 20)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Semantic search service not available."
        )

    try:
        results = semantic_search.search_by_topic(
            topic=topic,
            company_symbol=company.upper() if company else None,
            year=year,
            limit=limit
        )

        return {
            "topic": topic,
            "filters": {
                "company": company,
                "year": year
            },
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic search failed: {str(e)}")

@app.get("/api/v1/earnings-calls/{company}/sentiment-timeline")
def sentiment_timeline_endpoint(
    company: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    user = Depends(verify_api_key)
):
    """
    Timeline de sentimento para uma empresa

    Args:
        company: Símbolo da empresa
        start_year: Ano inicial (opcional)
        end_year: Ano final (opcional)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Semantic search service not available."
        )

    try:
        timeline = semantic_search.get_sentiment_timeline(
            company_symbol=company.upper(),
            start_year=start_year,
            end_year=end_year
        )

        return {
            "company": company.upper(),
            "period_range": {
                "start_year": start_year,
                "end_year": end_year
            },
            "total_periods": len(timeline),
            "timeline": timeline
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timeline retrieval failed: {str(e)}")

@app.get("/api/v1/earnings-calls/{company}/{year}Q{quarter}/highlights")
def call_highlights_endpoint(
    company: str,
    year: int,
    quarter: int,
    user = Depends(verify_api_key)
):
    """
    Destaques de uma teleconferência específica

    Args:
        company: Símbolo da empresa
        year: Ano
        quarter: Trimestre (1-4)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Semantic search service not available."
        )

    try:
        highlights = semantic_search.get_call_highlights(
            company_symbol=company.upper(),
            year=year,
            quarter=quarter
        )

        if "error" in highlights:
            raise HTTPException(status_code=404, detail=highlights["error"])

        return highlights
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Highlights retrieval failed: {str(e)}")

@app.post("/api/v1/earnings-calls/process")
def process_audio_endpoint(
    mode: str = "latest",  # "latest" or "all"
    company: str = "PETR4",
    payload_file: Optional[str] = None,
    user = Depends(verify_api_key)
):
    """
    Processar arquivos de áudio de teleconferências

    Args:
        mode: "latest" para apenas o mais recente, "all" para todos
        company: Símbolo da empresa
        payload_file: Caminho para arquivo de payload (opcional)
    """
    if not SEMANTIC_SEARCH_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Audio processing service not available."
        )

    # Insert mock data for testing
    try:
        # Import here to avoid dependency issues
        from api.database import get_db_cursor
        from api.semantic_search_ml import SemanticSearchService
        import json
        from datetime import datetime

        # First, ensure tables exist
        with get_db_cursor() as cursor:
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS earnings_calls (
                    id SERIAL PRIMARY KEY,
                    company_symbol VARCHAR(10) NOT NULL,
                    call_date DATE NOT NULL,
                    year INTEGER NOT NULL,
                    quarter INTEGER NOT NULL,
                    transcript_text TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(company_symbol, year, quarter)
                );

                CREATE TABLE IF NOT EXISTS call_segments (
                    id SERIAL PRIMARY KEY,
                    call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
                    segment_order INTEGER NOT NULL,
                    speaker VARCHAR(100),
                    text_content TEXT NOT NULL,
                    timestamp_start VARCHAR(20),
                    sentiment_score FLOAT DEFAULT 0.5,
                    topics TEXT, -- JSON array
                    key_points TEXT, -- JSON array
                    embedding_vector TEXT -- JSON array for now
                );

                CREATE TABLE IF NOT EXISTS call_insights (
                    id SERIAL PRIMARY KEY,
                    call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE UNIQUE,
                    overall_sentiment FLOAT DEFAULT 0.5,
                    key_topics TEXT, -- JSON array
                    summary TEXT,
                    highlights TEXT, -- JSON array
                    risks_mentioned TEXT, -- JSON array
                    opportunities_mentioned TEXT -- JSON array
                );
            """)

        # Sample transcript data
        sample_transcript = """
        Boa tarde e bem-vindos à teleconferência de resultados da Petrobras do segundo trimestre de 2025.

        Nossos resultados do segundo trimestre foram excepcionais, com receita líquida de R$ 123 bilhões,
        representando um crescimento de 15% em relação ao trimestre anterior.

        A produção de petróleo atingiu 2.8 milhões de barris por dia, um recorde histórico.
        Nosso EBITDA alcançou R$ 45 bilhões, superando todas as expectativas do mercado.

        Investimos R$ 8 bilhões em novos projetos de exploração no pré-sal, que devem aumentar
        significativamente nossa capacidade produtiva nos próximos trimestres.

        Aprovamos o pagamento de dividendos extraordinários de R$ 2.50 por ação, demonstrando
        nossa confiança na geração de caixa sustentável.

        Sobre perspectivas futuras, esperamos manter o crescimento da produção e melhorar ainda mais
        nossa eficiência operacional. Os preços do petróleo permanecem favoráveis e nossa posição
        competitiva no mercado internacional continua se fortalecendo.

        Agradecemos a todos os investidores pela confiança e estamos à disposição para perguntas.
        """

        # Sample call segments
        segments_data = [
            {
                "text": "Nossos resultados do segundo trimestre foram excepcionais, com receita líquida de R$ 123 bilhões, representando um crescimento de 15% em relação ao trimestre anterior.",
                "speaker": "CEO",
                "timestamp": "00:02:30",
                "sentiment": "positive",
                "topics": ["receita", "resultados", "crescimento"],
                "key_points": ["receita R$ 123 bilhões", "crescimento 15%"]
            },
            {
                "text": "A produção de petróleo atingiu 2.8 milhões de barris por dia, um recorde histórico. Nosso EBITDA alcançou R$ 45 bilhões, superando todas as expectativas do mercado.",
                "speaker": "CFO",
                "timestamp": "00:05:15",
                "sentiment": "positive",
                "topics": ["produção", "petróleo", "ebitda", "recordes"],
                "key_points": ["2.8 milhões barris/dia", "EBITDA R$ 45 bilhões", "recorde histórico"]
            },
            {
                "text": "Investimos R$ 8 bilhões em novos projetos de exploração no pré-sal, que devem aumentar significativamente nossa capacidade produtiva nos próximos trimestres.",
                "speaker": "COO",
                "timestamp": "00:08:45",
                "sentiment": "positive",
                "topics": ["investimentos", "pré-sal", "exploração", "capacidade"],
                "key_points": ["R$ 8 bilhões investimento", "projetos pré-sal", "aumento capacidade"]
            },
            {
                "text": "Aprovamos o pagamento de dividendos extraordinários de R$ 2.50 por ação, demonstrando nossa confiança na geração de caixa sustentável.",
                "speaker": "CFO",
                "timestamp": "00:12:30",
                "sentiment": "positive",
                "topics": ["dividendos", "caixa", "sustentabilidade"],
                "key_points": ["dividendos R$ 2.50 por ação", "geração de caixa"]
            }
        ]

        # Initialize semantic search for embeddings
        search_service = SemanticSearchService()

        with get_db_cursor() as cursor:
            # Insert main earnings call record
            cursor.execute("""
                INSERT INTO earnings_calls (company_symbol, call_date, year, quarter, transcript_text, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_symbol, year, quarter) DO UPDATE SET
                    transcript_text = EXCLUDED.transcript_text,
                    processed_at = EXCLUDED.processed_at
                RETURNING id
            """, (company.upper(), "2025-08-08", 2025, 2, sample_transcript, datetime.now()))

            call_record = cursor.fetchone()
            call_id = call_record[0] if call_record else None

            if call_id:
                # Clear existing segments for this call
                cursor.execute("DELETE FROM call_segments WHERE call_id = %s", (call_id,))

                # Insert call segments with embeddings
                for i, segment in enumerate(segments_data):
                    # Generate embedding for the segment text
                    try:
                        embedding = search_service.get_embeddings([segment["text"]])[0]
                        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                    except:
                        # Fallback if embedding generation fails
                        embedding_list = [0.0] * 768

                    cursor.execute("""
                        INSERT INTO call_segments (
                            call_id, segment_order, speaker, text_content,
                            timestamp_start, sentiment_score, topics,
                            key_points, embedding_vector
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        call_id, i + 1, segment["speaker"], segment["text"],
                        segment["timestamp"], 0.8 if segment["sentiment"] == "positive" else 0.5,
                        json.dumps(segment["topics"]), json.dumps(segment["key_points"]),
                        json.dumps(embedding_list)
                    ))

                # Insert call insights summary
                cursor.execute("""
                    INSERT INTO call_insights (call_id, overall_sentiment, key_topics, summary, highlights, risks_mentioned, opportunities_mentioned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (call_id) DO UPDATE SET
                        overall_sentiment = EXCLUDED.overall_sentiment,
                        key_topics = EXCLUDED.key_topics,
                        summary = EXCLUDED.summary,
                        highlights = EXCLUDED.highlights,
                        risks_mentioned = EXCLUDED.risks_mentioned,
                        opportunities_mentioned = EXCLUDED.opportunities_mentioned
                """, (
                    call_id, 0.85,
                    json.dumps(["receita", "produção", "investimentos", "dividendos"]),
                    "Resultados excepcionais do 2T25 com receita de R$ 123 bilhões e EBITDA de R$ 45 bilhões. Produção recorde e investimentos em pré-sal.",
                    json.dumps([
                        "Receita líquida de R$ 123 bilhões (+15%)",
                        "Produção recorde de 2.8M barris/dia",
                        "EBITDA de R$ 45 bilhões",
                        "Investimento de R$ 8 bilhões em pré-sal",
                        "Dividendos de R$ 2.50 por ação"
                    ]),
                    json.dumps([]),  # No risks mentioned in this sample
                    json.dumps([
                        "Crescimento da produção",
                        "Melhoria da eficiência operacional",
                        "Posição competitiva internacional"
                    ])
                ))

            # Also add a VALE3 sample
            cursor.execute("""
                INSERT INTO earnings_calls (company_symbol, call_date, year, quarter, transcript_text, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_symbol, year, quarter) DO UPDATE SET
                    transcript_text = EXCLUDED.transcript_text,
                    processed_at = EXCLUDED.processed_at
                RETURNING id
            """, ("VALE3", "2025-08-10", 2025, 2,
                "Resultados da Vale no segundo trimestre de 2025 mostram produção de minério de ferro de 85 milhões de toneladas. Preços do minério permanecem estáveis e investimentos em sustentabilidade continuam.",
                datetime.now()))

            vale_record = cursor.fetchone()
            if vale_record:
                vale_id = vale_record[0]
                cursor.execute("""
                    INSERT INTO call_segments (call_id, segment_order, speaker, text_content, timestamp_start, sentiment_score, topics, key_points, embedding_vector)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    vale_id, 1, "CEO",
                    "Produção de minério de ferro atingiu 85 milhões de toneladas no segundo trimestre",
                    "00:03:00", 0.7,
                    json.dumps(["produção", "minério", "ferro"]),
                    json.dumps(["85 milhões toneladas", "segundo trimestre"]),
                    json.dumps([0.1] * 768)  # Simple embedding
                ))

        return {
            "message": "Mock data inserted successfully!",
            "mode": mode,
            "company": company.upper(),
            "status": "Sample earnings call data populated",
            "data_inserted": {
                "earnings_calls": 2,
                "call_segments": len(segments_data) + 1,
                "companies": ["PETR4", "VALE3"],
                "sample_queries": [
                    "produção",
                    "receita",
                    "investimentos",
                    "dividendos",
                    "pré-sal"
                ]
            }
        }

    except Exception as e:
        return {
            "message": "Failed to insert mock data",
            "error": str(e),
            "mode": mode,
            "company": company.upper(),
            "status": "Error during data insertion"
        }

# Handler para Vercel
def handler(request):
    """Handler para Vercel serverless"""
    return app