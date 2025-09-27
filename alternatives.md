# 🔄 Alternativas à OpenAI API

## Opção 1: Usar apenas Sentence Transformers (Gratuito)

### Para Embeddings:
- **Já implementado**: O código já usa `sentence-transformers` como fallback
- **Modelo**: `paraphrase-multilingual-mpnet-base-v2`
- **100% gratuito** e roda localmente
- Qualidade similar para português

### Para Transcrição:
- **Whisper Local**: Instalar e usar whisper localmente
- **Mais lento** mas gratuito
- Requer mais recursos de CPU/GPU

```python
# Instalar whisper local
pip install openai-whisper

# Usar no código
import whisper
model = whisper.load_model("base")
result = model.transcribe("audio.mp3")
```

## Opção 2: APIs Alternativas Mais Baratas

### Groq API (Muito mais barato)
- **Whisper**: $0.05 por hora de áudio (vs $0.36 na OpenAI)
- **Rápido**: Processamento super rápido
- **Créditos gratuitos**: $10 grátis ao criar conta

```python
# Modificar transcription_service.py
from groq import Groq

client = Groq(api_key="gsk_...")
transcription = client.audio.transcriptions.create(
    file=audio_file,
    model="whisper-large-v3"
)
```

### Replicate API
- **Whisper**: ~$0.004 por minuto
- **Pay-as-you-go**: Sem mensalidade
- **Créditos iniciais** gratuitos

## Opção 3: Solução Híbrida (Recomendado)

1. **Embeddings**: Usar sentence-transformers (grátis)
2. **Transcrição**: Groq API (muito barato)
3. **Custo total**: ~$0.50 para processar 10 horas de áudio

## 🎯 Modificações Necessárias no Código

### 1. Remover dependência da OpenAI para embeddings:

```python
# Em analysis_service.py
def generate_embeddings(self, text: str) -> List[float]:
    # Sempre usar sentence-transformers
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    embedding = model.encode(text)
    return embedding.tolist()
```

### 2. Usar Groq para transcrição:

```python
# Em transcription_service.py
def transcribe_with_groq(self, audio_file_path: str) -> str:
    from groq import Groq

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language="pt"
        )

    return transcription.text
```

## 📊 Comparação de Custos

| Serviço | Transcrição (10h áudio) | Embeddings (10k textos) | Total |
|---------|------------------------|------------------------|-------|
| OpenAI | $3.60 | $0.13 | $3.73 |
| Groq + Local | $0.50 | $0 (local) | $0.50 |
| Tudo Local | $0 | $0 | $0 |

## 🚀 Setup Rápido sem OpenAI

1. **Criar conta Groq**: https://console.groq.com/
2. **Pegar API key** (gsk_...)
3. **Configurar**:
   ```bash
   export GROQ_API_KEY="gsk_..."
   # Não precisa de OPENAI_API_KEY
   ```

## 💡 Recomendação

Para seu caso (earnings calls trimestrais):
- **Use Groq**: Muito barato, rápido e confiável
- **Embeddings locais**: Já está implementado como fallback
- **Custo anual**: < $5 para processar todos os áudios

Quer que eu modifique o código para usar Groq em vez de OpenAI?