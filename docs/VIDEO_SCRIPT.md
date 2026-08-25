# Roteiro do vídeo de demo (máx. 4 min, exigido pela submissão)

Mesmo pipeline já validado no AgentPay/Socratiq: Playwright captura a
app real rodando → ElevenLabs narra (voz clonada do Igor) → ffmpeg monta.
Diferença aqui: a "app" é o terminal rodando `adk run` + o dashboard do
Cloud Run/Firestore no navegador (não uma UI web própria).

**GRAVADO 25/08**: `procurement_agent_demo_video.mp4` (42s, 1280x800,
salvo em `OneDrive/Área de Trabalho/Screenshots/`). Pipeline real
adaptado nesse dia por dois bloqueios de infra (não de conteúdo):

- **Chrome extension (claude-in-chrome) não conectada** após o reboot
  do PC → usei Playwright MCP (browser próprio, não depende da
  extensão) pra capturar o GitHub real. Console do Cloud Run/Firestore
  (exige login Google) foi substituído por saída real de
  `gcloud run services list` / `gcloud firestore databases list` —
  mesma prova, sem depender de sessão logada no navegador.
- **BaseScan bloqueou com challenge anti-bot (403)** → em vez de
  contornar, mostrei a leitura raw da RPC (`eth_getTransactionReceipt`,
  status 0x1, tx real) — na verdade mais forte como prova, e é
  literalmente o que `onchain_verify.py` faz.
- **ElevenLabs com fatura em atraso (401 payment_required)** → vídeo
  saiu **sem narração**, só com legendas em tela em inglês (cumpre a
  exigência "em inglês ou com legenda em inglês" mesmo assim). Pra
  adicionar a voz clonada do Igor depois: resolver a fatura na
  ElevenLabs, e eu regenero os 5 áudios + remonto (pipeline modular,
  script fica pronto pra reuso).

Todo o conteúdo do vídeo é dado real: tx real
(`0xca2aa6adde336b0276af2274445901df0f235d73f74def8463a9fd6a78e6e0f3`),
provedores/preços reais, saída real do `gcloud`/`curl` contra o
serviço deployado.

## Exigências da submissão (Devpost) que o vídeo TEM que cumprir
- Overview do problema + proposta de valor + demo em ação
- **Precisa mostrar o backend rodando no Google Cloud** (Console, Cloud
  Run dashboard, logs do Vertex AI, ou a URL `.run.app`)
- Até 4 minutos (só os primeiros 4min são avaliados se passar)
- Em inglês ou com legenda em inglês
- Publicado no YouTube ou Vimeo, não listado

## Segmentos (alvo: ~3min30s total, com folga do limite de 4min)

### Segmento 1 — Problema + proposta de valor (0:00–0:35)
**Tela:** README do repo no GitHub (github.com/ibcorreaai-oss/agentpay-procurement-agent)
**Narração (EN):** "AI agents are great at reasoning, but terrible at
taking real action with real money. This is Procurement Agent: it
decides it needs a piece of data, shops for the best price across
multiple real x402-payment providers, gets its decision audited by a
second AI, and pays — autonomously, with real USDC — inside a
budget enforced by code, not just a prompt."

### Segmento 2 — Arquitetura (0:35–1:05)
**Tela:** `docs/ARCHITECTURE.md` no GitHub, diagrama mermaid renderizado
**Narração:** "Built on Google's Agent Development Kit with Gemini 3.5:
a primary agent for decision-making, a separate auditor sub-agent for
review, and deterministic guardrails — a budget cap and idempotency
check — that can veto a payment even if both AI agents approve it."

### Segmento 3 — Demo ao vivo, terminal (1:05–2:15)
**Tela:** terminal rodando `adk run procurement_agent` (ou, se preferir
mostrar o serviço deployado, chamar o endpoint do Cloud Run via curl/
Postman em vez do terminal local — decidir na hora, o que ficar mais
legível em vídeo)
**Ação real a capturar:**
1. Agente lista os provedores (scrape402_extract, scrape402_diff)
2. Cota os dois em tempo real (mostrar os preços reais aparecendo)
3. Chama o auditor (sub-agente Gemini) — mostrar o veredito
4. Executa o pagamento — mostrar o `tx_hash` real aparecendo
**Narração:** vai narrando cada passo conforme aparece na tela,
terminando com "...and there it is — a real USDC transaction, signed
via Circle's MPC custody, verified independently on-chain."

### Segmento 4 — Prova on-chain + Google Cloud (2:15–2:55)
**Tela:** split ou sequência:
- BaseScan mostrando a transação real (link do `tx_hash` do segmento 3)
- Cloud Run console mostrando o serviço `agentpay-procurement` ativo
  (região us-central1, revisão mais recente)
- Firestore console mostrando o documento do pagamento no banco
  `agentpay-procurement`, coleção `payments`, status CONFIRMED
**Narração:** "The payment is verified independently on-chain — we
never trust the facilitator's word alone. And the whole agent runs
live on Google Cloud Run, with Firestore as the ledger."

### Segmento 5 — Fechamento (2:55–3:20)
**Tela:** README de novo, seção "O que ele faz"
**Narração:** "Procurement Agent: autonomous decision, independent
audit, real payment, independent verification. Built for the Taskmaster
category of the All Things Agentic Hackathon. Code's public, link
below."

## Checklist de gravação
- [x] Rodar o fluxo real 1x pra garantir que sai tudo limpo antes de gravar (feito 25/08, tx real capturada)
- [x] Capturas reais (GitHub via Playwright, terminal com o trace real, RPC on-chain, `gcloud`) — trocado BaseScan/Cloud
      Run console por alternativas sem login/anti-bot, ver nota acima
- [ ] ElevenLabs: reaproveitar a voz clonada do Igor (`AwOG8GsiTbwBq3sHLpmX`) — **bloqueado, fatura em atraso**
- [x] ffmpeg monta em 1280x800 — saiu 42s (sem narração ainda, ritmo mais curto que os 3min30 planejados)
- [x] Revisado (frame extraído de cada segmento antes de salvar); sem áudio ainda, `silencedetect` não se aplica
- [ ] Assistir o vídeo final e aprovar (ou pedir ajuste) antes do upload
- [ ] Upload no YouTube — **manual, só o Igor pode** (sem tool de upload de vídeo)
- [ ] Upload no YouTube — **manual, só o Igor pode** (sem tool de upload de vídeo)
