# 🗄️ Setup PostgreSQL Database for Audio Pipeline

## 1. Railway Dashboard Setup

### Add PostgreSQL to your Railway project:

1. **Open Railway Dashboard**: https://railway.app/
2. **Navigate to your project**: `financialbreakfast`
3. **Click**: `+ New` → `Database` → `Add PostgreSQL`
4. Railway will automatically provision a PostgreSQL instance

### Get Database Credentials:

1. Click on the PostgreSQL service
2. Go to `Variables` tab
3. Copy the `DATABASE_URL` (it will look like: `postgresql://user:password@host:port/railway`)

## 2. Enable pgvector Extension

Once PostgreSQL is created, connect to it and run:

```bash
# Using Railway CLI
railway run psql $DATABASE_URL

# Or using the connection string directly
psql "postgresql://user:password@host:port/railway"
```

Then execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 3. Run Database Migration

Execute the migration to create all required tables:

```bash
# From the project directory
psql $DATABASE_URL -f migrations/create_earnings_calls_tables.sql

# Or use Railway CLI
railway run psql $DATABASE_URL -f migrations/create_earnings_calls_tables.sql
```

## 4. Set Environment Variables

### In Railway Dashboard:

1. Go to your main service (financialbreakfast)
2. Click `Variables`
3. Add these variables:

```env
DATABASE_URL=<copy from PostgreSQL service>
OPENAI_API_KEY=sk-your-openai-api-key
WEBHOOK_URL=https://hooks.slack.com/your-webhook (optional)
```

### In GitHub Secrets (for Actions):

```bash
# Set DATABASE_URL
gh secret set DATABASE_URL --body "postgresql://user:password@host:port/railway" \
  --repo lucianfialho/financialbreakfast-api

# Set OpenAI API Key
gh secret set OPENAI_API_KEY --body "sk-your-openai-api-key" \
  --repo lucianfialho/financialbreakfast-api

# Set Webhook URL (optional)
gh secret set WEBHOOK_URL --body "https://hooks.slack.com/your-webhook" \
  --repo lucianfialho/financialbreakfast-api
```

## 5. Test Database Connection

### Local Test:
```bash
# Export the DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:port/railway"

# Test with Python
python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Database connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

### Test pgvector:
```sql
-- Connect to database and run:
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Should return one row if pgvector is installed
```

## 6. Verify Tables Created

```sql
-- List all tables
\dt

-- You should see:
-- earnings_calls
-- call_segments
-- call_insights

-- Check vector column
\d call_segments

-- Should show embedding column with type vector(768)
```

## 7. Test Audio Processing Pipeline

Once database is configured:

```bash
# Test locally
export DATABASE_URL="your-connection-string"
export OPENAI_API_KEY="your-api-key"

# Run the processor
python scripts/quarterly_processor.py

# Or trigger GitHub Actions manually
gh workflow run "🎙️ Quarterly Earnings Call Processor" \
  --repo lucianfialho/financialbreakfast-api \
  -f company=PETR4 \
  -f mode=latest
```

## 8. Production API Test

After configuration, test the semantic search:

```bash
# Test semantic search endpoint
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/search?query=petroleo&limit=5"

# Should return results once audio is processed
```

## 📊 Database Schema Overview

- **earnings_calls**: Stores metadata about each call
- **call_segments**: Stores transcribed segments with embeddings
- **call_insights**: Stores analysis results (sentiment, keywords, etc.)

## 🔒 Security Notes

- Never commit DATABASE_URL or API keys to git
- Use environment variables for all sensitive data
- Railway automatically handles SSL/TLS for database connections
- GitHub Secrets are encrypted and safe for CI/CD

## 🚀 Next Steps

1. Add PostgreSQL to Railway ✅
2. Run migrations ✅
3. Set environment variables ✅
4. Test connection ✅
5. Run audio processor ✅
6. Verify semantic search ✅

Once complete, the pipeline will automatically:
- Download audio files every quarter
- Transcribe using OpenAI Whisper
- Generate embeddings for semantic search
- Store everything in PostgreSQL with pgvector
- Enable semantic search through the API