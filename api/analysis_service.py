"""
Analysis Service for Sentiment Analysis and Embeddings
Processes transcribed text for semantic search and insights
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
from textblob import TextBlob
import nltk
from collections import Counter


class AnalysisService:
    """Service for analyzing transcribed text"""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
        """
        Initialize analysis service

        Args:
            model_name: Name of sentence transformer model (supports Portuguese)
        """
        self.embedding_model = SentenceTransformer(model_name)
        self._setup_nltk()

        # Financial keywords for context
        self.financial_keywords = {
            "positive": [
                "crescimento", "aumento", "alta", "lucro", "ganho", "positivo",
                "melhora", "recuperação", "expansão", "recorde", "sucesso",
                "oportunidade", "investimento", "retorno", "dividendo"
            ],
            "negative": [
                "queda", "perda", "baixa", "prejuízo", "declínio", "negativo",
                "risco", "desafio", "pressão", "volatilidade", "incerteza",
                "crise", "redução", "impacto", "dificuldade"
            ],
            "metrics": [
                "receita", "ebitda", "lucro líquido", "capex", "dívida",
                "margem", "fluxo de caixa", "produção", "vendas", "volume",
                "preço", "custo", "investimento", "resultado", "balanço"
            ],
            "guidance": [
                "projeção", "estimativa", "meta", "objetivo", "previsão",
                "expectativa", "guidance", "outlook", "cenário", "perspectiva"
            ]
        }

    def _setup_nltk(self):
        """Download required NLTK data"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
        except:
            pass

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text using TextBlob

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores
        """
        # Use TextBlob for basic sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1

        # Count financial keywords for context
        text_lower = text.lower()
        positive_count = sum(1 for word in self.financial_keywords["positive"] if word in text_lower)
        negative_count = sum(1 for word in self.financial_keywords["negative"] if word in text_lower)

        # Adjust sentiment based on financial context
        keyword_adjustment = (positive_count - negative_count) * 0.05
        adjusted_polarity = max(-1, min(1, polarity + keyword_adjustment))

        # Determine label
        if adjusted_polarity > 0.1:
            label = "positive"
        elif adjusted_polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return {
            "polarity": adjusted_polarity,
            "subjectivity": subjectivity,
            "label": label,
            "confidence": abs(adjusted_polarity),
            "positive_keywords": positive_count,
            "negative_keywords": negative_count
        }

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate sentence embedding for semantic search

        Args:
            text: Text to embed

        Returns:
            Numpy array with embedding vector (768 dimensions)
        """
        # Generate embedding
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from text

        Args:
            text: Text to analyze
            top_n: Number of top keywords to return

        Returns:
            List of keywords
        """
        # Simple keyword extraction based on frequency
        # Remove common words
        stopwords = {
            "o", "a", "os", "as", "de", "da", "do", "dos", "das", "em", "no", "na", "nos", "nas",
            "para", "com", "por", "que", "e", "é", "um", "uma", "foi", "ser", "são", "está",
            "como", "mais", "mas", "ou", "se", "não", "muito", "já", "também", "só", "pelo",
            "pela", "até", "isso", "ela", "ele", "tem", "tinha", "sido", "ter", "havia"
        }

        # Tokenize and filter
        words = re.findall(r'\b[a-záàâãéèêíïóôõöúçñ]+\b', text.lower())
        words = [w for w in words if len(w) > 3 and w not in stopwords]

        # Count frequency
        word_freq = Counter(words)

        # Add weight to financial keywords
        for word in word_freq:
            for category in self.financial_keywords.values():
                if word in category:
                    word_freq[word] *= 2

        # Return top keywords
        return [word for word, _ in word_freq.most_common(top_n)]

    def extract_entities(self, text: str) -> Dict:
        """
        Extract named entities from text

        Args:
            text: Text to analyze

        Returns:
            Dictionary of entities by type
        """
        entities = {
            "companies": [],
            "amounts": [],
            "percentages": [],
            "dates": [],
            "people": []
        }

        # Extract companies (simple pattern matching)
        company_patterns = [
            r"Petrobras", r"PETR4", r"Vale", r"VALE3", r"Petrobrás",
            r"BR Distribuidora", r"Braskem", r"Transpetro"
        ]
        for pattern in company_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                entities["companies"].append(pattern)

        # Extract amounts (R$ values)
        amount_pattern = r'R\$\s*[\d.,]+\s*(?:milhões|bilhões|mil)?'
        entities["amounts"] = re.findall(amount_pattern, text)

        # Extract percentages
        percentage_pattern = r'\d+[.,]?\d*%'
        entities["percentages"] = re.findall(percentage_pattern, text)

        # Extract quarters/years
        quarter_pattern = r'[1-4]T\d{2}'
        entities["dates"].extend(re.findall(quarter_pattern, text))

        return entities

    def identify_topics(self, text: str) -> List[str]:
        """
        Identify main topics in text

        Args:
            text: Text to analyze

        Returns:
            List of identified topics
        """
        topics = []
        text_lower = text.lower()

        # Topic patterns
        topic_patterns = {
            "produção": ["produção", "barril", "bpd", "exploração"],
            "resultados_financeiros": ["receita", "lucro", "ebitda", "resultado"],
            "investimentos": ["investimento", "capex", "projeto", "expansão"],
            "dividendos": ["dividendo", "distribuição", "acionista", "payout"],
            "endividamento": ["dívida", "alavancagem", "financiamento", "crédito"],
            "preços": ["preço", "brent", "commodity", "cotação"],
            "sustentabilidade": ["sustentável", "carbono", "emissão", "renovável"],
            "governance": ["governança", "compliance", "transparência", "ética"]
        }

        for topic, keywords in topic_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        return topics

    def analyze_risk_mentions(self, text: str) -> Dict:
        """
        Analyze risk mentions in text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with risk analysis
        """
        risk_keywords = [
            "risco", "incerteza", "volatilidade", "pressão", "desafio",
            "ameaça", "exposição", "vulnerabilidade", "instabilidade"
        ]

        opportunity_keywords = [
            "oportunidade", "potencial", "crescimento", "expansão",
            "melhoria", "avanço", "desenvolvimento", "inovação"
        ]

        text_lower = text.lower()

        risk_count = sum(1 for word in risk_keywords if word in text_lower)
        opportunity_count = sum(1 for word in opportunity_keywords if word in text_lower)

        # Extract risk contexts (sentences containing risk keywords)
        sentences = text.split(".")
        risk_contexts = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in risk_keywords):
                risk_contexts.append(sentence.strip())

        return {
            "risk_mentions": risk_count,
            "opportunity_mentions": opportunity_count,
            "risk_opportunity_ratio": risk_count / max(1, opportunity_count),
            "risk_contexts": risk_contexts[:3]  # Top 3 risk mentions
        }

    def process_segment(self, segment: Dict) -> Dict:
        """
        Process a transcription segment with all analyses

        Args:
            segment: Segment dictionary with text and metadata

        Returns:
            Processed segment with analysis results
        """
        text = segment.get("text", "")

        # Perform analyses
        sentiment = self.analyze_sentiment(text)
        embedding = self.generate_embedding(text)
        keywords = self.extract_keywords(text)
        entities = self.extract_entities(text)
        topics = self.identify_topics(text)

        # Add analysis results to segment
        processed = {
            **segment,
            "sentiment": sentiment,
            "embedding": embedding.tolist(),  # Convert to list for JSON serialization
            "keywords": keywords,
            "entities": entities,
            "topics": topics
        }

        return processed

    def generate_call_insights(self, segments: List[Dict]) -> Dict:
        """
        Generate overall insights from all segments

        Args:
            segments: List of processed segments

        Returns:
            Dictionary with call-level insights
        """
        # Aggregate sentiment
        sentiments = [s["sentiment"]["polarity"] for s in segments if "sentiment" in s]
        overall_sentiment = np.mean(sentiments) if sentiments else 0

        # Aggregate topics
        all_topics = []
        for segment in segments:
            all_topics.extend(segment.get("topics", []))
        topic_counts = Counter(all_topics)
        key_topics = [topic for topic, _ in topic_counts.most_common(5)]

        # Aggregate keywords
        all_keywords = []
        for segment in segments:
            all_keywords.extend(segment.get("keywords", []))
        keyword_counts = Counter(all_keywords)
        top_keywords = [kw for kw, _ in keyword_counts.most_common(10)]

        # Risk analysis
        all_text = " ".join([s.get("text", "") for s in segments])
        risk_analysis = self.analyze_risk_mentions(all_text)

        # Identify highlights (most positive and negative segments)
        segments_with_sentiment = [s for s in segments if "sentiment" in s]
        segments_sorted = sorted(segments_with_sentiment, key=lambda x: x["sentiment"]["polarity"])

        highlights = {
            "most_positive": segments_sorted[-3:] if len(segments_sorted) >= 3 else segments_sorted,
            "most_negative": segments_sorted[:3] if len(segments_sorted) >= 3 else segments_sorted
        }

        # Generate summary
        summary = {
            "total_segments": len(segments),
            "overall_sentiment": overall_sentiment,
            "sentiment_label": "positive" if overall_sentiment > 0.1 else "negative" if overall_sentiment < -0.1 else "neutral",
            "key_topics": key_topics,
            "top_keywords": top_keywords,
            "risk_mentions": risk_analysis["risk_mentions"],
            "opportunity_mentions": risk_analysis["opportunity_mentions"],
            "highlights": {
                "positive": [
                    {
                        "text": h.get("text", "")[:200] + "...",
                        "sentiment": h["sentiment"]["polarity"],
                        "segment_number": h.get("segment_number", 0)
                    }
                    for h in highlights["most_positive"]
                ],
                "negative": [
                    {
                        "text": h.get("text", "")[:200] + "...",
                        "sentiment": h["sentiment"]["polarity"],
                        "segment_number": h.get("segment_number", 0)
                    }
                    for h in highlights["most_negative"]
                ]
            },
            "analyzed_at": datetime.now().isoformat()
        }

        return summary


if __name__ == "__main__":
    # Example usage
    service = AnalysisService()

    # Test with sample text
    sample_text = """
    No segundo trimestre de 2025, a Petrobras registrou um crescimento de 15% na receita líquida,
    impulsionado pelo aumento da produção e melhores preços do petróleo. O EBITDA alcançou R$ 45 bilhões,
    superando as expectativas do mercado. Apesar dos desafios relacionados à volatilidade cambial,
    a empresa mantém perspectivas positivas para o restante do ano.
    """

    # Analyze sentiment
    sentiment = service.analyze_sentiment(sample_text)
    print(f"Sentiment: {sentiment}")

    # Extract keywords
    keywords = service.extract_keywords(sample_text)
    print(f"Keywords: {keywords}")

    # Extract entities
    entities = service.extract_entities(sample_text)
    print(f"Entities: {entities}")

    # Identify topics
    topics = service.identify_topics(sample_text)
    print(f"Topics: {topics}")