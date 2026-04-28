import os, smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASS = os.environ["EMAIL_APP_PASSWORD"]
EMAIL_TO   = "fillipesmoura@gmail.com"

deals = [
    {"label": "SP -> Orlando (ida e volta)", "outbound": "2025-09-25", "return": "2025-10-05",
     "airline": "LATAM", "stops": 0, "price": 2190},
    {"label": "SP -> Orlando (ida e volta)", "outbound": "2025-10-02", "return": "2025-10-14",
     "airline": "Azul", "stops": 1, "price": 2340},
    {"label": "SP -> Nova York JFK (ida e volta)", "outbound": "2025-09-29", "return": "2025-10-10",
     "airline": "American Airlines", "stops": 1, "price": 2480},
    {"label": "SP -> NY -> Orlando -> SP", "outbound": "2025-10-01", "return": "2025-10-15",
     "airline": "Copa Airlines", "stops": 1, "price": 3050},
]

msg = MIMEMultipart("alternative")
msg["Subject"] = f"[TESTE] Alerta de Passagem - {len(deals)} oferta(s) encontrada(s)!"
msg["From"]    = EMAIL_FROM
msg["To"]      = EMAIL_TO

rows = ""
for d in deals:
    stops_txt = "direto" if d.get("stops", 0) == 0 else f"{d['stops']} parada(s)"
    rows += f"""
    <tr>
      <td style="padding:12px 16px;border-bottom:1px solid #eee;color:#222">{d['label']}</td>
      <td style="padding:12px 16px;border-bottom:1px solid #eee;color:#222">{d['outbound']} &rarr; {d['return']}</td>
      <td style="padding:12px 16px;border-bottom:1px solid #eee;color:#222">{d['airline']}</td>
      <td style="padding:12px 16px;border-bottom:1px solid #eee;color:#222">{stops_txt}</td>
      <td style="padding:12px 16px;border-bottom:1px solid #eee;font-weight:bold;color:#1a7f37;font-size:15px">
        R$ {d['price']:,.0f}
      </td>
      <td style="padding:12px 16px;border-bottom:1px solid #eee">
        <a href="https://www.google.com/travel/flights" style="color:#0066cc;text-decoration:none;font-weight:bold">Ver &rarr;</a>
      </td>
    </tr>"""

html = f"""
<html>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px">
  <div style="max-width:700px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">

    <div style="background:#1a1a2e;padding:24px 28px">
      <h2 style="color:#fff;margin:0;font-size:20px">Monitor de Passagens Aereas</h2>
      <p style="color:#aab4d4;margin:6px 0 0;font-size:13px">audacelabsbr/flight-monitor &bull; Alerta automatico</p>
    </div>

    <div style="padding:24px 28px">
      <p style="margin:0 0 16px;color:#333;font-size:15px">
        Encontrei <strong style="color:#1a7f37">{len(deals)} oferta(s)</strong> abaixo do seu preco-alvo
        para a viagem de <strong>setembro a novembro de 2025</strong>.
      </p>

      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#f0f2f8">
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Rota</th>
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Datas</th>
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Cia. Aerea</th>
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Escalas</th>
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Preco I+V</th>
            <th style="padding:10px 16px;text-align:left;color:#555;font-weight:600;border-bottom:2px solid #dde">Link</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>

    <div style="background:#f8f9fb;padding:16px 28px;border-top:1px solid #eee">
      <p style="margin:0;color:#888;font-size:12px">
        Verificado em {datetime.now().strftime('%d/%m/%Y as %H:%M')} (UTC) &bull;
        Alvos: Orlando R$ 2.400 | NY R$ 2.600 | Multi-city R$ 3.200<br>
        <strong style="color:#c00">[ESTE E UM EMAIL DE TESTE - dados ficticios para validacao]</strong>
      </p>
    </div>

  </div>
</body>
</html>"""

msg.attach(MIMEText(html, "html"))
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(EMAIL_FROM, EMAIL_PASS)
    s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

print("Email de teste enviado com sucesso!")
