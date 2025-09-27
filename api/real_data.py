# Dados reais da Petrobras extraídos de TODAS as planilhas oficiais do site do investidor
# Dataset histórico completo: 22 períodos (2020-2025) extraídos das planilhas Excel originais

import json
import os

# Carrega dados históricos completos do arquivo JSON
def load_complete_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'petrobras_complete_historical.json')

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Dados históricos completos (22 períodos de 2020-2025)
REAL_DATA = load_complete_data()

# Adiciona dados da Vale como antes (mantendo compatibilidade)
REAL_DATA["VALE3"] = {
    "company": {
        "symbol": "VALE3",
        "name": "Vale S.A.",
        "country": "BRA",
        "sector": "Mining",
        "currency": "BRL"
    },
    "periods": [
        {
            "year": 2025,
            "quarter": 2,
            "period_label": "2T25",
            "financial_data": [
                {
                    "metric_name": "ebitda",
                    "metric_label": "EBITDA",
                    "value": 18000.00,
                    "currency": "BRL",
                    "unit": "millions",
                    "metric_category": "profitability"
                }
            ]
        }
    ]
}