# 🚀 Alternativas de Deploy para Financial API

O plano Vercel atingiu o limite. Aqui estão alternativas gratuitas:

## 🟣 **1. Railway (Recomendado)**

### Deploy:
```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Deploy
railway up
```

### Vantagens:
- **$5 grátis/mês**
- **PostgreSQL incluído**
- **Domínio automático**
- **Zero config**

---

## 🟠 **2. Render**

### Deploy:
1. Conectar GitHub repo
2. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.index:app --host 0.0.0.0 --port $PORT`

### Vantagens:
- **Completamente grátis**
- **PostgreSQL gratuito**
- **SSL automático**

---

## 🔵 **3. Fly.io**

### Deploy:
```bash
# 1. Instalar flyctl
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth login

# 3. Deploy
fly launch
```

### Vantagens:
- **Grátis até 3 apps**
- **Global edge**
- **PostgreSQL incluído**

---

## 🟢 **4. PythonAnywhere**

### Deploy manual:
1. Upload files via web
2. Configure WSGI
3. Set environment

### Vantagens:
- **Sempre grátis**
- **MySQL incluído**
- **Fácil setup**

---

## ⚡ **Quick Deploy - Railway**

```bash
# Se você tem Railway CLI:
cd vercel-api
railway up

# URL será: https://financialbreakfast-production.up.railway.app
```

## 🔗 **URLs de Exemplo (Railway)**

Substitua `your-app` pelo seu domínio Railway:

```bash
# Base
https://your-app.up.railway.app/api

# Docs
https://your-app.up.railway.app/api/docs

# Companies
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.up.railway.app/api/v1/companies

# Petrobras Data
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.up.railway.app/api/v1/financial-data/PETR4
```

## 🎯 **Recomendação**

**Use Railway** - É o mais similar à Vercel mas sem limites restritivos:
1. Deploy em segundos
2. Banco de dados incluído
3. Monitoramento automático
4. $5 grátis mensais (suficiente para API)

Quer que eu ajude com o deploy no Railway?