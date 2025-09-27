# 🚀 Financial Data API - Vercel

API para dados financeiros de empresas brasileiras rodando na Vercel.

## 📋 Deploy na Vercel

### 1. Instalar Vercel CLI
```bash
npm install -g vercel
```

### 2. Deploy
```bash
# No diretório vercel-api/
vercel --prod
```

### 3. Configurar domínio (opcional)
```bash
vercel --prod --alias your-api-domain.vercel.app
```

## 🔗 Endpoints Disponíveis

Substitua `your-app.vercel.app` pela sua URL do Vercel:

### Base URL
```
https://your-app.vercel.app
```

### 📚 Documentação
- **Swagger UI**: `https://your-app.vercel.app/api/docs`
- **ReDoc**: `https://your-app.vercel.app/api/redoc`

### 🔑 API Keys Demo
- **Free**: `demo-key-12345`
- **Pro**: `pro-key-67890`
- **Enterprise**: `enterprise-key-abc`

### 📊 Endpoints

#### Info da API
```bash
curl https://your-app.vercel.app/api
```

#### Health Check
```bash
curl https://your-app.vercel.app/api/health
```

#### Listar Empresas
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.vercel.app/api/v1/companies
```

#### Dados da Petrobras
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.vercel.app/api/v1/financial-data/PETR4
```

#### Dados da Vale
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.vercel.app/api/v1/financial-data/VALE3
```

#### Time Series - Receita Petrobras
```bash
curl -H "X-API-Key: demo-key-12345" \
  https://your-app.vercel.app/api/v1/financial-data/PETR4/metric/net_revenue
```

#### Filtrar por Métrica
```bash
curl -H "X-API-Key: demo-key-12345" \
  "https://your-app.vercel.app/api/v1/financial-data/PETR4?metrics=ebitda,net_income"
```

## 🏗️ Estrutura do Projeto

```
vercel-api/
├── api/
│   └── index.py          # FastAPI app
├── vercel.json           # Configuração Vercel
├── requirements.txt      # Dependências
└── README.md            # Documentação
```

## 📈 Dados Disponíveis

### Empresas
- **PETR4** - Petróleo Brasileiro S.A. (Petrobras)
- **VALE3** - Vale S.A.

### Métricas
- `net_revenue` - Receita Líquida
- `ebitda` - EBITDA
- `net_income` - Lucro Líquido
- `capex` - Investimentos
- `net_debt` - Dívida Líquida

### Períodos
- **2025**: 1T25, 2T25
- **2024**: 4T24

## 🔒 Autenticação

Todas as rotas da API (exceto `/` e `/api/health`) requerem API key:

```bash
curl -H "X-API-Key: demo-key-12345" [URL]
```

## ⚡ Performance

- **Cold start**: ~2-3s
- **Warm requests**: <500ms
- **Rate limiting**: Por plano (Free: 100/h, Pro: 1000/h)

## 🎯 Próximos Passos

1. **Banco de dados**: Adicionar PostgreSQL via Vercel
2. **Cache**: Implementar Redis via Upstash
3. **Dados reais**: Carregar 43+ arquivos Excel
4. **Monitoramento**: Analytics e logs