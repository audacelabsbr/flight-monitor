#!/usr/bin/env python3
"""
Monitor de Passagens Aéreas — SP → Orlando (+Nova York)
Verifica preços via SerpAPI (Google Flights) e envia alertas por email.
"""

import os
import json
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itertools import product

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

SERPAPI_KEY = os.environ["SERPAPI_KEY"]
EMAIL_FROM  = os.environ["EMAIL_FROM"]          # ex: seuemail@gmail.com
EMAIL_PASS  = os.environ["EMAIL_APP_PASSWORD"]  # senha de app do Gmail
EMAIL_TO    = "fillipesmoura@gmail.com"

# Preços-alvo (R$) para disparar alerta
ALVO_ORLANDO   = 2400   # GRU ↔ MCO ida e volta
ALVO_NOVA_YORK = 2600   # GRU ↔ JFK ida e volta
ALVO_MULTI     = 3200   # SP → NY → Orlando (ou inverso) — multi-city

# Janela de viagem
DEPARTURE_START = "2025-09-22"   # última semana de setembro
DEPARTURE_END   = "2025-11-01"   # início de novembro
MIN_TRIP_DAYS   = 10
MAX_TRIP_DAYS   = 15

# Rotas a monitorar
ROUTES = [
    {"label": "SP → Orlando (ida e volta)",  "origin": "GRU", "dest": "MCO", "target": ALVO_ORLANDO},
    {"label": "SP → Nova York (ida e volta)", "origin": "GRU", "dest": "JFK", "target": ALVO_NOVA_YORK},
    {"label": "SP → Nova York (EWR)",         "origin": "GRU", "dest": "EWR", "target": ALVO_NOVA_YORK},
]

# ─── GERAR PARES DE DATAS ────────────────────────────────────────────────────

def generate_date_pairs():
    """Gera pares (ida, volta) dentro da janela definida, respeitando duração da viagem."""
    pairs = []
    start = datetime.strptime(DEPARTURE_START, "%Y-%m-%d")
    end   = datetime.strptime(DEPARTURE_END,   "%Y-%m-%d")
    current = start
    while current <= end:
        for days in range(MIN_TRIP_DAYS, MAX_TRIP_DAYS + 1, 2):  # pular de 2 em 2 para reduzir chamadas
            volta = current + timedelta(days=days)
            if volta.strftime("%Y-%m-%d") <= DEPARTURE_END:
                pairs.append((current.strftime("%Y-%m-%d"), volta.strftime("%Y-%m-%d")))
        current += timedelta(days=3)  # checar a cada 3 dias na janela
    return pairs

# ─── BUSCA DE PREÇOS ─────────────────────────────────────────────────────────

def search_flight(origin, destination, outbound_date, return_date):
    """Consulta Google Flights via SerpAPI e retorna o menor preço encontrado."""
    params = {
        "engine":           "google_flights",
        "departure_id":     origin,
        "arrival_id":       destination,
        "outbound_date":    outbound_date,
        "return_date":      return_date,
        "currency":         "BRL",
        "hl":               "pt",
        "api_key":          SERPAPI_KEY,
        "type":             "1",  # 1 = round trip
        "adults":           "1",
    }
    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        prices = []
        for section in ["best_flights", "other_flights"]:
            for flight in data.get(section, []):
                price = flight.get("price")
                if price:
                    prices.append({
                        "price":    price,
                        "airline":  flight.get("flights", [{}])[0].get("airline", "N/A"),
                        "duration": flight.get("total_duration", 0),
                        "stops":    len(flight.get("layovers", [])),
                        "outbound": outbound_date,
                        "return":   return_date,
                    })
        
        return sorted(prices, key=lambda x: x["price"])[:3] if prices else []
    
    except Exception as e:
        print(f"  Erro ao buscar {origin}→{destination} ({outbound_date}): {e}")
        return []


def search_multicity(outbound_date, return_date, ny_first=True):
    """
    Busca voo multi-city:
      - ny_first=True:  GRU → JFK → MCO → GRU
      - ny_first=False: GRU → MCO → JFK → GRU
    """
    if ny_first:
        label  = "SP → NY → Orlando → SP"
        leg1   = ("GRU", "JFK")
        leg2   = ("MCO", "GRU")
    else:
        label  = "SP → Orlando → NY → SP"
        leg1   = ("GRU", "MCO")
        leg2   = ("JFK", "GRU")

    # SerpAPI multi-city: passa os segmentos como JSON
    mid_date = (datetime.strptime(outbound_date, "%Y-%m-%d") +
                timedelta(days=7)).strftime("%Y-%m-%d")

    params = {
        "engine":     "google_flights",
        "type":       "3",  # multi-city
        "currency":   "BRL",
        "hl":         "pt",
        "api_key":    SERPAPI_KEY,
        "adults":     "1",
        "multi_city_json": json.dumps([
            {"departure_id": leg1[0], "arrival_id": leg1[1], "date": outbound_date},
            {"departure_id": leg2[0], "arrival_id": leg2[1], "date": mid_date},
        ]),
    }
    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        prices = []
        for section in ["best_flights", "other_flights"]:
            for flight in data.get(section, []):
                price = flight.get("price")
                if price:
                    prices.append({
                        "price":    price,
                        "airline":  flight.get("flights", [{}])[0].get("airline", "N/A"),
                        "label":    label,
                        "outbound": outbound_date,
                        "return":   return_date,
                    })
        return sorted(prices, key=lambda x: x["price"])[:2] if prices else []

    except Exception as e:
        print(f"  Erro multi-city ({label}): {e}")
        return []

# ─── EMAIL ───────────────────────────────────────────────────────────────────

def send_email(deals):
    """Envia email com as ofertas encontradas abaixo do preço-alvo."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"✈️ Alerta de Passagem — {len(deals)} oferta(s) encontrada(s)!"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    rows = ""
    for d in deals:
        stops_txt = "direto" if d.get("stops", 0) == 0 else f"{d['stops']} parada(s)"
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee">{d['label']}</td>
          <td style="padding:10px;border-bottom:1px solid #eee">{d['outbound']} → {d['return']}</td>
          <td style="padding:10px;border-bottom:1px solid #eee">{d['airline']}</td>
          <td style="padding:10px;border-bottom:1px solid #eee">{stops_txt}</td>
          <td style="padding:10px;border-bottom:1px solid #eee;font-weight:bold;color:#1a7f37">
            R$ {d['price']:,.0f}
          </td>
          <td style="padding:10px;border-bottom:1px solid #eee">
            <a href="https://www.google.com/travel/flights" style="color:#0066cc">Ver no Google Flights</a>
          </td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto">
      <h2 style="color:#1a1a2e">✈️ Monitor de Passagens — Ofertas Encontradas</h2>
      <p>Boas notícias! Encontrei <strong>{len(deals)} opção(ões)</strong> abaixo do seu preço-alvo 
         para a viagem de setembro a novembro de 2025.</p>
      
      <table style="width:100%;border-collapse:collapse;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.1)">
        <thead>
          <tr style="background:#1a1a2e;color:#fff">
            <th style="padding:12px;text-align:left">Rota</th>
            <th style="padding:12px;text-align:left">Datas</th>
            <th style="padding:12px;text-align:left">Cia. Aérea</th>
            <th style="padding:12px;text-align:left">Escalas</th>
            <th style="padding:12px;text-align:left">Preço (I+V)</th>
            <th style="padding:12px;text-align:left">Link</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      
      <p style="margin-top:20px;color:#666;font-size:12px">
        ⚡ Preços verificados em {datetime.now().strftime('%d/%m/%Y às %H:%M')}.<br>
        Valores podem mudar rapidamente — verifique antes de comprar.<br>
        Alvos configurados: Orlando R$ {ALVO_ORLANDO:,} | NY R$ {ALVO_NOVA_YORK:,} | Multi-city R$ {ALVO_MULTI:,}
      </p>
    </body></html>"""

    msg.attach(MIMEText(html, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    
    print(f"  📧 Email enviado para {EMAIL_TO} com {len(deals)} oferta(s)")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'='*60}")
    print(f"  MONITOR DE PASSAGENS — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}\n")
    
    all_deals = []
    date_pairs = generate_date_pairs()
    
    print(f"  Verificando {len(date_pairs)} combinações de datas × {len(ROUTES)} rotas...")
    print(f"  (+ 2 variações multi-city por data)\n")
    
    # Rotas simples (ida e volta)
    for route in ROUTES:
        print(f"  🔍 {route['label']}")
        for outbound, ret in date_pairs:
            results = search_flight(route["origin"], route["dest"], outbound, ret)
            for r in results:
                if r["price"] <= route["target"]:
                    r["label"]  = route["label"]
                    r["target"] = route["target"]
                    all_deals.append(r)
                    print(f"     ✅ R$ {r['price']:,} ({outbound} → {ret}) [{r['airline']}]")
    
    # Multi-city (sample: primeiras 3 datas)
    print(f"\n  🔍 Multi-city SP + NY + Orlando")
    for outbound, ret in date_pairs[:3]:
        for ny_first in [True, False]:
            results = search_multicity(outbound, ret, ny_first=ny_first)
            for r in results:
                if r["price"] <= ALVO_MULTI:
                    r["target"] = ALVO_MULTI
                    all_deals.append(r)
                    print(f"     ✅ R$ {r['price']:,} — {r['label']} ({outbound})")
    
    print(f"\n  Total de ofertas abaixo do alvo: {len(all_deals)}")
    
    if all_deals:
        # Ordenar por preço e remover duplicatas
        seen = set()
        unique_deals = []
        for d in sorted(all_deals, key=lambda x: x["price"]):
            key = (d.get("label",""), d.get("outbound",""), d.get("price",0))
            if key not in seen:
                seen.add(key)
                unique_deals.append(d)
        
        send_email(unique_deals)
    else:
        print("  Nenhuma oferta abaixo do alvo hoje. Nenhum email enviado.")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    run()
