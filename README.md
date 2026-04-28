# ✈️ Monitor de Passagens — SP → Orlando + Nova York

Roda automaticamente todo dia via GitHub Actions e envia um email quando encontrar passagens abaixo do preço-alvo.

---

## Rotas monitoradas

| Rota | Preço-alvo |
|------|-----------|
| GRU → MCO (Orlando) ida e volta | R$ 2.400 |
| GRU → JFK / EWR (Nova York) ida e volta | R$ 2.600 |
| Multi-city SP + NY + Orlando | R$ 3.200 |

**Janela de viagem:** 22/set/2025 a 01/nov/2025 • Duração: 10–15 dias

---

## Configuração (passo a passo)

### 1. Criar conta no SerpAPI (gratuita)

1. Acesse https://serpapi.com e crie uma conta
2. O plano gratuito inclui **100 buscas/mês** — suficiente para rodar ~3x por semana
3. Copie sua **API Key** no dashboard

> 💡 Se quiser rodar diariamente sem limitação, o plano pago custa US$ 50/mês. Para começar, o free é ótimo.

### 2. Configurar email (Gmail)

Você precisa de uma **Senha de App** do Gmail (não a senha normal):

1. Acesse https://myaccount.google.com/security
2. Ative a **verificação em duas etapas** (se não tiver)
3. Busque **"Senhas de app"** na mesma página
4. Crie uma senha para "Email" → anote os 16 caracteres gerados

### 3. Criar o repositório no GitHub

```bash
# No terminal (com Claude Code ou localmente):
cd flight-monitor
git init
git add .
git commit -m "Monitor de passagens inicial"
gh repo create flight-monitor --private --push --source=.
```

### 4. Adicionar os Secrets no GitHub

No repositório criado, vá em **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|--------|-------|
| `SERPAPI_KEY` | Sua chave do SerpAPI |
| `EMAIL_FROM` | Seu email Gmail (ex: `seugmail@gmail.com`) |
| `EMAIL_APP_PASSWORD` | A senha de app de 16 caracteres |

### 5. Ativar e testar

1. Vá em **Actions** no repositório
2. Clique em **Monitor de Passagens Aéreas**
3. Clique em **Run workflow** para testar agora
4. Veja os logs — se encontrar ofertas, você receberá email em `fillipesmoura@gmail.com`

A partir daí roda sozinho todo dia às 08h (horário de Brasília) 🎉

---

## Ajustar preços-alvo

Edite as linhas no topo de `monitor.py`:

```python
ALVO_ORLANDO   = 2400   # mude aqui
ALVO_NOVA_YORK = 2600
ALVO_MULTI     = 3200
```

---

## Estrutura dos arquivos

```
flight-monitor/
├── monitor.py                        ← script principal
├── .github/
│   └── workflows/
│       └── monitor.yml               ← agendamento automático
└── README.md
```
