# 🔐 Configurar GitHub Secrets

## Método 1: Via GitHub CLI (Rápido)

### 1. Configure OPENAI_API_KEY:
```bash
gh secret set OPENAI_API_KEY --body "sk-sua-chave-aqui" --repo lucianfialho/financialbreakfast-api
```

### 2. Configure DATABASE_URL:
```bash
# Cole aqui a URL do PostgreSQL do Railway
gh secret set DATABASE_URL --body "postgresql://user:pass@host:port/railway" --repo lucianfialho/financialbreakfast-api
```

### 3. Verificar se foram configurados:
```bash
gh secret list --repo lucianfialho/financialbreakfast-api
```

## Método 2: Via GitHub Web

### 1. Acesse o repositório:
https://github.com/lucianfialho/financialbreakfast-api

### 2. Vá em Settings → Secrets and variables → Actions:
https://github.com/lucianfialho/financialbreakfast-api/settings/secrets/actions

### 3. Clique em "New repository secret" e adicione:

**Secret 1:**
- Name: `OPENAI_API_KEY`
- Value: `sk-sua-chave-da-openai`

**Secret 2:**
- Name: `DATABASE_URL`
- Value: `postgresql://user:password@host:port/railway`

## Como pegar o DATABASE_URL do Railway:

1. **Acesse Railway**: https://railway.app/
2. **Vá no projeto**: `financialbreakfast`
3. **Clique no PostgreSQL**
4. **Aba Variables**
5. **Copie DATABASE_URL**

Deve ser algo como:
```
postgresql://postgres:senha123@viaduct-fra1-12345.railway.app:5432/railway
```

## Verificar se os secrets estão funcionando:

### Disparar o workflow para testar:
```bash
gh workflow run "🎙️ Quarterly Earnings Call Processor" \
  --repo lucianfialho/financialbreakfast-api \
  -f company=PETR4 \
  -f mode=latest
```

### Monitorar execução:
```bash
# Ver status
gh run list --repo lucianfialho/financialbreakfast-api --limit 1

# Ver logs detalhados
gh run view --log --repo lucianfialho/financialbreakfast-api
```

## ⚠️ Importantes:

1. **Nunca commite** esses valores no código
2. **GitHub Secrets são criptografados** e seguros
3. **Só aparecem nos logs** como `***`
4. **Workflow precisa dos dois** para funcionar completamente

## 🧪 Teste rápido:

Após configurar, o workflow deve:
1. ✅ Conectar no PostgreSQL (não mais erro de socket)
2. ✅ Usar OpenAI para transcrição (não mais warning)
3. ✅ Processar e salvar no banco
4. ✅ Habilitar busca semântica na API

## 🎯 Resultado esperado:

Depois do processamento bem-sucedido, você pode testar:

```bash
# Busca semântica funcionando
curl -H "X-API-Key: demo-key-12345" \
  "https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/search?query=receita+crescimento&limit=3"
```

Deve retornar segmentos das transcrições relacionados à query!