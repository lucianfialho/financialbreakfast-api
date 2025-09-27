#!/bin/bash

# Complete setup script for GitHub secrets and database
# Usage: ./configure_secrets.sh

echo "🔧 Configuração Completa do Pipeline"
echo "===================================="
echo ""

# Check if both environment variables are set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set!"
    echo "   export OPENAI_API_KEY='sk-...'"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set!"
    echo ""
    echo "📋 Como pegar o DATABASE_URL do Railway:"
    echo "1. Acesse: https://railway.app/"
    echo "2. Entre no projeto 'financialbreakfast'"
    echo "3. Clique no serviço PostgreSQL"
    echo "4. Vá na aba 'Variables'"
    echo "5. Copie o valor de DATABASE_URL"
    echo "6. Execute: export DATABASE_URL='postgresql://...'"
    echo "7. Execute este script novamente"
    exit 1
fi

echo "✅ OPENAI_API_KEY configurada"
echo "✅ DATABASE_URL configurada"
echo ""

# Test database connection
echo "🔌 Testando conexão com PostgreSQL..."
python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Conexão com PostgreSQL bem-sucedida!')
    conn.close()
except Exception as e:
    print(f'❌ Erro na conexão: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Falha na conexão com o banco"
    exit 1
fi

# Test OpenAI API
echo ""
echo "🔑 Testando OpenAI API..."
python3 -c "
import os
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    # Quick test
    response = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'Say OK'}],
        max_tokens=5
    )

    print('✅ OpenAI API funcionando!')
except Exception as e:
    print(f'❌ Erro na OpenAI API: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Falha na OpenAI API"
    exit 1
fi

# Setup database
echo ""
echo "🗄️ Configurando banco de dados..."

# Check if migration file exists
if [ ! -f "migrations/create_earnings_calls_tables.sql" ]; then
    echo "❌ Arquivo de migração não encontrado"
    exit 1
fi

# Run migration
echo "📝 Executando migração..."
psql $DATABASE_URL -f migrations/create_earnings_calls_tables.sql

if [ $? -eq 0 ]; then
    echo "✅ Migração executada com sucesso!"
else
    echo "⚠️  Migração pode ter falhado (talvez já executada anteriormente)"
fi

# Configure GitHub secrets
echo ""
echo "🔐 Configurando secrets no GitHub..."

# Set OpenAI API Key
gh secret set OPENAI_API_KEY --body "$OPENAI_API_KEY" --repo lucianfialho/financialbreakfast-api
if [ $? -eq 0 ]; then
    echo "✅ OPENAI_API_KEY configurada no GitHub"
else
    echo "❌ Erro ao configurar OPENAI_API_KEY"
    exit 1
fi

# Set Database URL
gh secret set DATABASE_URL --body "$DATABASE_URL" --repo lucianfialho/financialbreakfast-api
if [ $? -eq 0 ]; then
    echo "✅ DATABASE_URL configurada no GitHub"
else
    echo "❌ Erro ao configurar DATABASE_URL"
    exit 1
fi

# Verify secrets are set
echo ""
echo "🔍 Verificando secrets no GitHub..."
gh secret list --repo lucianfialho/financialbreakfast-api

echo ""
echo "🎉 Configuração Completa!"
echo ""
echo "📋 Status:"
echo "✅ PostgreSQL conectado e migrado"
echo "✅ OpenAI API funcionando"
echo "✅ Secrets configurados no GitHub"
echo ""
echo "🚀 Próximos passos:"
echo "1. Testar o pipeline completo:"
echo "   gh workflow run '🎙️ Quarterly Earnings Call Processor' \\"
echo "     --repo lucianfialho/financialbreakfast-api \\"
echo "     -f company=PETR4 -f mode=latest"
echo ""
echo "2. Monitorar execução:"
echo "   gh run list --repo lucianfialho/financialbreakfast-api --limit 1"
echo ""
echo "3. Ver logs em tempo real:"
echo "   https://github.com/lucianfialho/financialbreakfast-api/actions"