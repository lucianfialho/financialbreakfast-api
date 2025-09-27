#!/usr/bin/env python3
"""
Script para migrar dados financeiros para PostgreSQL no Railway
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pathlib import Path

def get_db_config():
    """Obtém configuração do banco a partir da DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        raise ValueError("DATABASE_URL não configurada")

    # Railway usa postgres:// mas psycopg2 espera postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    return database_url

def load_json_data():
    """Carrega dados do arquivo JSON"""
    json_path = Path(__file__).parent / 'api' / 'petrobras_complete_historical.json'

    if not json_path.exists():
        # Tenta caminho alternativo
        json_path = Path(__file__).parent / 'petrobras_complete_historical.json'

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_database(cursor):
    """Cria tabelas se não existirem"""
    with open('railway_setup.sql', 'r') as f:
        sql = f.read()
        cursor.execute(sql)
    print("✅ Tabelas criadas/verificadas")

def get_or_create_company(cursor, symbol, company_data):
    """Insere ou busca empresa existente"""
    cursor.execute("""
        SELECT id FROM companies WHERE symbol = %s
    """, (symbol,))

    result = cursor.fetchone()
    if result:
        return result['id']

    cursor.execute("""
        INSERT INTO companies (symbol, name, country, sector, currency)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE
        SET name = EXCLUDED.name
        RETURNING id
    """, (
        symbol,
        company_data['name'],
        company_data['country'],
        company_data['sector'],
        company_data['currency']
    ))

    return cursor.fetchone()['id']

def insert_period_and_metrics(cursor, company_id, period_data):
    """Insere período e suas métricas"""
    cursor.execute("""
        INSERT INTO financial_periods (company_id, year, quarter, period_label)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (company_id, year, quarter) DO UPDATE
        SET period_label = EXCLUDED.period_label
        RETURNING id
    """, (
        company_id,
        period_data['year'],
        period_data['quarter'],
        period_data['period_label']
    ))
    period_id = cursor.fetchone()['id']

    # Remove métricas antigas se existirem
    cursor.execute("""
        DELETE FROM financial_metrics WHERE period_id = %s
    """, (period_id,))

    # Insere métricas do período
    metrics_count = 0
    for metric in period_data['financial_data']:
        cursor.execute("""
            INSERT INTO financial_metrics
            (period_id, metric_name, metric_label, value, currency, unit, metric_category)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            period_id,
            metric['metric_name'],
            metric['metric_label'],
            metric['value'],
            metric['currency'],
            metric['unit'],
            metric['metric_category']
        ))
        metrics_count += 1

    return metrics_count

def migrate_data():
    """Executa migração completa dos dados"""
    print("🚀 Iniciando migração dos dados para Railway PostgreSQL...")
    print("=" * 60)

    # Carrega dados JSON
    json_data = load_json_data()

    # Conecta ao banco
    database_url = get_db_config()
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cursor = conn.cursor()

    try:
        # Setup inicial do banco
        setup_database(cursor)
        conn.commit()

        total_periods = 0
        total_metrics = 0

        # Processa cada empresa
        for symbol, data in json_data.items():
            print(f"\n📊 Processando {symbol}: {data['company']['name']}")

            # Insere ou busca empresa
            company_id = get_or_create_company(cursor, symbol, data['company'])
            print(f"   ✅ Empresa ID: {company_id}")

            # Processa cada período
            for period in data['periods']:
                metrics_count = insert_period_and_metrics(cursor, company_id, period)
                total_periods += 1
                total_metrics += metrics_count
                print(f"   📈 {period['period_label']}: {metrics_count} métricas inseridas")

        # Atualiza view materializada
        print("\n🔄 Atualizando view materializada...")
        cursor.execute("REFRESH MATERIALIZED VIEW metric_time_series")

        # Commit das transações
        conn.commit()

        # Estatísticas finais
        print("\n" + "=" * 60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"   📊 Total de períodos: {total_periods}")
        print(f"   📈 Total de métricas: {total_metrics}")

        # Verifica dados inseridos
        cursor.execute("""
            SELECT
                c.symbol,
                COUNT(DISTINCT fp.id) as periods,
                COUNT(DISTINCT fm.id) as metrics
            FROM companies c
            JOIN financial_periods fp ON c.id = fp.company_id
            JOIN financial_metrics fm ON fp.id = fm.period_id
            GROUP BY c.symbol
        """)

        print("\n📋 Resumo por empresa:")
        for row in cursor.fetchall():
            print(f"   {row['symbol']}: {row['periods']} períodos, {row['metrics']} métricas")

    except Exception as e:
        print(f"\n❌ Erro durante migração: {e}")
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal"""
    migrate_data()
    print("\n🎉 Banco de dados Railway configurado com sucesso!")

if __name__ == "__main__":
    main()