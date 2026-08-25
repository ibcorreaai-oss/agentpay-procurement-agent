# Roteiro do vídeo de demo (máx. 4 min, exigido pela submissão)

Mesmo pipeline já validado no AgentPay/Socratiq: Playwright captura a
app real rodando → ElevenLabs narra (voz clonada do Igor) → ffmpeg monta.
Diferença aqui: a "app" é o terminal rodando `adk run` + o dashboard do
Cloud Run/Firestore no navegador (não uma UI web própria).

**Desbloqueado 25/08**: Circle configurada, pagamento real de ponta a
ponta confirmado on-chain (Base Sepolia, tx
`0x31c9704854b79910b89314e21a24569b7ac1645c962789010d0b9c1f53263e2f`).
Falta só aplicar as credenciais Circle no serviço `agentpay-procurement`
deployado (hoje só rodou local) antes de gravar o segmento 3/4 contra o
serviço de verdade — ver README. Pendência de credencial: só o Igor
pode autorizar essa etapa (bloqueio de segurança do classificador).

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

## Checklist de gravação (quando a Circle estiver pronta)
- [ ] Rodar o fluxo real 1x pra garantir que sai tudo limpo antes de gravar
- [ ] Playwright/screenshot do terminal + BaseScan + Cloud Run + Firestore
- [ ] ElevenLabs: reaproveitar a voz clonada do Igor (`AwOG8GsiTbwBq3sHLpmX`, mesma do AgentPay)
- [ ] ffmpeg monta em 1280x800, ~3min30s
- [ ] Revisar de verdade (extrair frame de cada segmento + `silencedetect` no áudio) antes de publicar
- [ ] Upload no YouTube — **manual, só o Igor pode** (sem tool de upload de vídeo)
