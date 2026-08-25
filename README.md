# Procurement Agent — Taskmaster (All Things Agentic Hackathon)

Um agente autônomo que decide sozinho que precisa de um dado, cota preço
entre múltiplos provedores reais de dados via [x402](https://x402.org)
(pagamento HTTP nativo em USDC), tem a decisão auditada por um segundo
agente antes de gastar, e paga de verdade — sem humano no loop, dentro
de um orçamento pré-aprovado e aplicado por código.

Categoria: **Taskmaster** — "Build a Complete Workflow, Not Just a
Chatbot". Não é um agente que só responde perguntas: ele toma uma ação
financeira real e verificável.

## O que ele faz, de ponta a ponta

1. **Lista provedores** de dados configurados.
2. **Cota preço** de cada um via handshake x402 real (HTTP 402 + schema
   `PaymentRequirements`) — nunca paga nessa etapa.
3. **Pede auditoria** a um segundo agente (Gemini, sub-agente nativo do
   ADK) antes de decidir gastar.
4. **Paga sozinho**: assina EIP-712 (EIP-3009 `transferWithAuthorization`)
   via custódia MPC da Circle (nenhuma chave privada no processo),
   liquidação feita pelo protocolo x402 oficial.
5. **Verifica on-chain de forma independente** — nunca confia só na
   palavra do facilitator de que o pagamento foi liquidado; relê o
   evento `Transfer` direto da rede.
6. **Grava tudo no Firestore** (ledger de pagamentos + log de auditoria)
   e reporta o resultado.

## Stack obrigatório da hackathon

| Requisito | Como é atendido |
|---|---|
| Gemini 3.5+ | `gemini-3.5-flash` via Vertex AI, usado pelo agente principal E pelo agente auditor |
| Framework de agente do Google | [Google ADK](https://google.github.io/adk-docs/) — multi-agent nativo (`AgentTool`), não uma chamada de API solta |
| Infra Google Cloud | Cloud Run (deploy do agente) + Firestore (ledger) |

## Arquitetura

Ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) pro diagrama completo.

Peça central: o **teto de orçamento é aplicado por código**, não só
sugerido no prompt. Mesmo que o agente principal E o auditor Gemini
aprovem um gasto, o `budget_guard` pode vetar antes de qualquer
chamada de pagamento — defense in depth de verdade.

## Origem / disclosure (regra "New Projects Only" da hackathon)

Este repositório é um projeto novo, construído inteiramente durante o
período de submissão (03–31/08/2026). Ele reaproveita **padrões de
design e aprendizados** (não código) de um projeto pessoal anterior,
[AgentPay](https://github.com/ibcorreaai-oss/agentpay) — construído em
julho/2026 para outro hackathon, sem nenhuma relação com o Google —
especificamente:

- Verificação on-chain independente do evento `Transfer` (nunca confiar
  no cliente/facilitator).
- Custódia MPC via Circle em vez de chave privada crua no app.
- A ideia de teto de orçamento aplicado por código, idempotência e
  logging estruturado veio de um backlog de melhorias ("growth ideas")
  geradas pelo sistema de auto-revisão semanal do AgentPay original,
  identificadas em 23/08/2026 mas nunca implementadas até este projeto.

Todo o código deste repositório — o agente ADK, o agente auditor, a
comparação multi-provedor, a assinatura EIP-712 via Circle, o ledger no
Firestore e o deploy no Cloud Run — foi escrito do zero durante o
período de submissão.

## Rodando localmente

```bash
python -m venv .venv && source .venv/Scripts/activate  # ou .venv/bin/activate no Linux/Mac
pip install google-adk google-genai
pip install -r procurement_agent/requirements.txt

cp procurement_agent/.env.example procurement_agent/.env
# preencha GOOGLE_CLOUD_PROJECT com seu projeto GCP (Vertex AI habilitado)
# credenciais da Circle: ver docs/MANUAL_SETUP_CHECKLIST.md

gcloud auth application-default login
adk run procurement_agent
```

## Deploy no Cloud Run

```bash
adk deploy cloud_run --project=<seu-projeto> --region=us-central1 \
  --service_name=agentpay-procurement procurement_agent
```

## Testes

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

18 testes, cobrindo verificação on-chain (mockada), teto de orçamento
(incluindo um bug real de precisão de float achado e corrigido durante
o desenvolvimento), idempotência, e assinatura EIP-712.
