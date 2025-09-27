# Railway Production Setup

## Required Environment Variables

Configure these in Railway dashboard (`Settings > Variables`):

### Core API Variables
```bash
# Already configured
API_KEY=your-secret-api-key
DATABASE_URL=postgresql://user:pass@host:port/database
```

### New Variables for Audio Pipeline
```bash
# OpenAI API for Whisper transcription
OPENAI_API_KEY=sk-your-openai-api-key

# Webhook for notifications (optional)
WEBHOOK_URL=https://hooks.slack.com/your-webhook-url

# Processing settings
AUDIO_CHUNK_SIZE=600000          # 10 minutes in milliseconds
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
MAX_AUDIO_SIZE_MB=100           # Maximum audio file size to process
```

### PostgreSQL Extensions Required
```sql
-- Run this in your Railway PostgreSQL database
CREATE EXTENSION IF NOT EXISTS vector;
```

### Database Migration
```bash
# Run the migration in Railway PostgreSQL
cat migrations/create_earnings_calls_tables.sql | railway run psql $DATABASE_URL
```

## Railway CLI Commands

### Deploy to Railway:
```bash
# Login to Railway
railway login

# Link to existing project
railway link

# Deploy current code
railway up

# Set environment variables
railway variables set OPENAI_API_KEY=sk-your-key
railway variables set WEBHOOK_URL=your-webhook
```

### Check status:
```bash
# View logs
railway logs

# Check variables
railway variables

# Run database migration
railway run psql $DATABASE_URL -f migrations/create_earnings_calls_tables.sql
```

## Manual Testing in Production

### Test semantic search:
```bash
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/search?query=petroleo&limit=5"
```

### Test processing endpoint:
```bash
curl -X POST -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/process?mode=latest&company=PETR4"
```

### Test sentiment timeline:
```bash
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/PETR4/sentiment-timeline"
```

## Automated Processing Schedule

The GitHub Actions workflow runs automatically:
- **Quarterly**: 15th of January, April, July, October at 10:00 UTC
- **Manual**: Can be triggered manually from Actions tab

## Monitoring

### Railway Dashboard:
- Monitor CPU/Memory usage during processing
- Check logs for processing errors
- Database metrics and connections

### GitHub Actions:
- Processing logs uploaded as artifacts
- Email notifications on failures
- Success/failure status in commits

## Expected Resource Usage

### During Processing:
- **CPU**: High (transcription and ML processing)
- **Memory**: 2-4GB (large audio files and ML models)
- **Disk**: 500MB-2GB temporary files
- **Network**: High (downloading audio files)

### Normal Operation:
- **CPU**: Low (API requests only)
- **Memory**: 512MB (FastAPI + database connections)
- **Disk**: 100MB (code and logs)
- **Network**: Low (API responses)

## Troubleshooting

### Common Issues:

1. **Audio download fails**:
   - Check internet connectivity
   - Verify Petrobras API URLs are still valid

2. **Transcription fails**:
   - Verify OPENAI_API_KEY is set correctly
   - Check OpenAI account credits
   - Fall back to local Whisper if needed

3. **Database connection issues**:
   - Verify DATABASE_URL format
   - Check PostgreSQL service status
   - Ensure pgvector extension is installed

4. **Memory issues during processing**:
   - Increase Railway plan memory limits
   - Process files one at a time
   - Implement chunking for large files

## Production URLs

- **API Base**: https://financialbreakfast-production.up.railway.app
- **Health Check**: https://financialbreakfast-production.up.railway.app/api/health
- **Documentation**: https://financialbreakfast-production.up.railway.app/api/docs
- **Semantic Search**: https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/search