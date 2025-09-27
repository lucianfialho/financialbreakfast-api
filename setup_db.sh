#!/bin/bash

# PostgreSQL Database Setup Script for Audio Pipeline
# Usage: ./setup_db.sh

echo "🗄️ PostgreSQL Setup for Audio Pipeline"
echo "======================================="
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set!"
    echo ""
    echo "📋 Instructions:"
    echo "1. Go to Railway Dashboard: https://railway.app/"
    echo "2. Add PostgreSQL to your project"
    echo "3. Copy the DATABASE_URL from PostgreSQL service variables"
    echo "4. Run: export DATABASE_URL='your-connection-string'"
    echo "5. Run this script again"
    exit 1
fi

echo "✅ DATABASE_URL found"
echo ""

# Test connection
echo "🔌 Testing database connection..."
python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Could not connect to database"
    exit 1
fi

# Run migration
echo ""
echo "📝 Running database migration..."
if [ -f "migrations/create_earnings_calls_tables.sql" ]; then
    psql $DATABASE_URL -f migrations/create_earnings_calls_tables.sql

    if [ $? -eq 0 ]; then
        echo "✅ Migration completed successfully!"
    else
        echo "❌ Migration failed"
        exit 1
    fi
else
    echo "❌ Migration file not found: migrations/create_earnings_calls_tables.sql"
    exit 1
fi

# Verify tables
echo ""
echo "🔍 Verifying tables..."
psql $DATABASE_URL -c "\dt" | grep -E "(earnings_calls|call_segments|call_insights)"

if [ $? -eq 0 ]; then
    echo "✅ All tables created successfully!"
else
    echo "⚠️  Some tables might be missing"
fi

# Check pgvector extension
echo ""
echo "🔍 Checking pgvector extension..."
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep vector

if [ $? -eq 0 ]; then
    echo "✅ pgvector extension is installed!"
else
    echo "⚠️  pgvector extension not found - installing..."
    psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"
fi

echo ""
echo "🎉 Database setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set OPENAI_API_KEY environment variable"
echo "2. Add secrets to GitHub repository:"
echo "   gh secret set DATABASE_URL --body '$DATABASE_URL'"
echo "   gh secret set OPENAI_API_KEY --body 'your-api-key'"
echo "3. Deploy to Railway: railway up"
echo "4. Run processor: python scripts/quarterly_processor.py"