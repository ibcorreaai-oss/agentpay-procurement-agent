# Rascunho pronto pra colar no formulário do Devpost

Fonte dos campos: https://allthingsagentichackathon.devpost.com/ (checado
ao vivo em 25/08/2026). Igor só precisa copiar/colar e ajustar o que
quiser.

## Category
**Taskmaster**

## URL to the hosted Project
https://agentpay-procurement-439350431205.us-central1.run.app

(É a API do servidor ADK, não uma UI clicável — no texto da submissão,
deixar claro que a interação é via `curl`/`adk web`, com exemplos no
README. Se quiser algo mais visual pros jurados clicarem, dá pra rodar
`adk web` local antes da gravação/submissão e usar aquela UI — mas não
é obrigatório, o requisito diz "se disponível".)

## Text description

### Features and functionality
Procurement Agent is an autonomous Taskmaster agent: it decides it
needs a piece of market data, requests real price quotes from multiple
x402-payment providers, has its spending decision reviewed by a
separate AI auditor, checks a deterministic budget cap against its
real spending ledger, and — if everything clears — pays for real: it
signs an EIP-712 payment authorization via Circle's MPC custody, the
x402 protocol settles it on-chain, and the agent independently
re-reads the blockchain `Transfer` event before ever marking the
payment confirmed. No human approves the transaction.

### Technologies used
Google Agent Development Kit (multi-agent via `AgentTool`), Gemini 3.5
Flash (Vertex AI), Google Cloud Run (2 deployed services), Firestore
(payment ledger + audit log), Circle Developer-Controlled Wallets
(MPC custody, EIP-712 signing), the official `x402` Python SDK
(EIP-3009 `transferWithAuthorization`, "exact" scheme), web3.py
(independent on-chain verification), Python/FastAPI (self-hosted demo
data provider).

### Other data sources used
scrape402.xyz (real third-party x402 data provider, Base mainnet) for
price comparison, plus a self-hosted x402 data provider
(`demo_provider/`) built for this project — same official protocol,
Base Sepolia testnet — because the only real third-party provider we
found required mainnet USDC to actually complete a purchase.

### Findings and learnings
- Serverless reuse is a real footgun for agent state: an ADK agent
  object built once at deploy time gets reused across every
  unrelated session on the same Cloud Run instance. Anything
  session-specific (correlation IDs, idempotency keys) has to come
  from the framework's own per-invocation context, never a variable
  captured at construction time.
- The x402 "exact" scheme is a signed EIP-3009 authorization
  (EIP-712), and Circle's raw wallet API needs `types.EIP712Domain`
  explicit in the payload — higher-level SDKs derive it silently and
  never surface that it's needed.
- Wallet addresses from Circle come lowercase (valid, but not EIP-55
  checksummed) — web3.py facilitators reject non-checksummed
  addresses outright.
- `hexbytes` 2.0's `.hex()` dropped the implicit `"0x"` prefix that
  the x402 SDK's facilitator interface expects back — a supply-chain
  version mismatch that only failed on a real (not mocked) payment.
- Testing `adk run` locally never proves the *deployed* server works:
  the Cloud Run service was returning 500 on every real request
  because `.env` is a local-only convenience the ADK CLI reads — the
  deployed server needs the same variables set explicitly on the
  Cloud Run service itself.
- Two AI opinions (the agent + the auditor) can both be wrong at the
  same time. The only thing that actually prevented overspending in
  testing was a plain deterministic budget check against the real
  ledger — not another model's judgment.

## URL to the code repository
https://github.com/ibcorreaai-oss/agentpay-procurement-agent
(público — sem necessidade de compartilhar com testing@devpost.com)

## Architecture Diagram
https://github.com/ibcorreaai-oss/agentpay-procurement-agent/blob/master/docs/ARCHITECTURE.md
(diagrama mermaid renderiza direto no GitHub)

## Demo video
`procurement_agent_demo_video.mp4` (Screenshots/) → sobe no YouTube
(unlisted é aceito por norma geral do Devpost; não listado ≠ privado)
→ cola o link aqui.

## Bonus (opcional)
- Blog post pronto em `docs/BLOG_POST_DRAFT.md` — **precisa ser
  PÚBLICO (não unlisted)** pro bônus valer, e precisa da frase
  dizendo que foi escrito pra participar deste hackathon (já está no
  rascunho). Publicar em dev.to ou medium.com.
- Post em rede social com a hashtag **#AllThingsAgenticHackathon**
  (X, LinkedIn, Instagram ou Facebook) também vale bônus.
