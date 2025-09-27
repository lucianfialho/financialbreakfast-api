-- Railway PostgreSQL Setup Script
-- Este script será executado após provisionar o banco no Railway

-- Tabela de empresas
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(3) NOT NULL,
    sector VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'BRL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de períodos financeiros
CREATE TABLE IF NOT EXISTS financial_periods (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    period_label VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year, quarter)
);

-- Tabela de métricas financeiras
CREATE TABLE IF NOT EXISTS financial_metrics (
    id SERIAL PRIMARY KEY,
    period_id INTEGER REFERENCES financial_periods(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL,
    metric_label VARCHAR(100) NOT NULL,
    value DECIMAL(20, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'BRL',
    unit VARCHAR(20) DEFAULT 'millions',
    metric_category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_id, metric_name)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_financial_periods_company_year ON financial_periods(company_id, year DESC);
CREATE INDEX IF NOT EXISTS idx_financial_periods_year_quarter ON financial_periods(year DESC, quarter DESC);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_period ON financial_metrics(period_id);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_name ON financial_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_category ON financial_metrics(metric_category);

-- View materializada para consultas rápidas
CREATE MATERIALIZED VIEW IF NOT EXISTS metric_time_series AS
SELECT
    c.symbol,
    c.name as company_name,
    fp.year,
    fp.quarter,
    fp.period_label,
    fm.metric_name,
    fm.metric_label,
    fm.value,
    fm.currency,
    fm.unit,
    fm.metric_category
FROM companies c
JOIN financial_periods fp ON c.id = fp.company_id
JOIN financial_metrics fm ON fp.id = fm.period_id
ORDER BY c.symbol, fp.year DESC, fp.quarter DESC;

-- Índice na view materializada
CREATE INDEX IF NOT EXISTS idx_metric_time_series_symbol_metric ON metric_time_series(symbol, metric_name);