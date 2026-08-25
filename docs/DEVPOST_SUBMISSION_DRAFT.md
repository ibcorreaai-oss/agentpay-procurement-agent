# Rascunho pronto pra colar no formulário do Devpost

Fonte dos campos: https://allthingsagentichackathon.devpost.com/ (checado
ao vivo em 25/08/2026). Igor só precisa copiar/colar e ajustar o que
quiser.

## Project Story — "About the project" (campo markdown de texto livre)

```markdown
## Inspiration

Most "autonomous agent" demos stop at reasoning: the agent writes a plan, maybe calls an API, and a human still approves anything that costs money. Payment is the part everyone skips, for a good reason — it's the part where a hallucination costs real money. We wanted to build a Taskmaster agent that doesn't stop at deciding: it shops for a real price, gets that decision reviewed by a second AI, checks a real budget, and pays — with real USDC, with no human in the loop for the transaction itself.

## What it does

Procurement Agent decides it needs a piece of market data, then:

1. **Quotes** the price from multiple real x402-payment providers (never pays at this step).
2. **Sends the decision to a separate auditor agent** (a second Gemini instance) for review before anything moves.
3. **Checks a deterministic budget guard** — plain code, not an LLM — against the real spending ledger. It can veto the payment even if both AI agents approved it.
4. **Signs and pays**: an EIP-712 payment authorization (EIP-3009 `transferWithAuthorization`) via Circle's MPC custody — no private key ever touches the process — settled through the official x402 protocol.
5. **Verifies independently on-chain**: it never trusts the payment SDK's settlement header alone. It re-reads the `Transfer` event directly from the blockchain before marking anything confirmed.
6. **Records everything** in Firestore: the ledger and the audit trail.

## How we built it

Google's Agent Development Kit (ADK) with Gemini 3.5 Flash: a primary agent for decision-making and a separate `spend_auditor` sub-agent wired in as a native `AgentTool` — not a loose API call. Two deterministic guardrails (`budget_guard`, `idempotency`) sit between the AI's decision and the actual payment call, reading real state from Firestore instead of trusting either model's opinion. Payment goes through the official `x402` Python SDK against Circle's Developer-Controlled Wallets API. Both services — the agent and a self-hosted data provider — run on Cloud Run.

The only real third-party x402 provider we found (scrape402.xyz) only accepts Base **mainnet**, and completing a real purchase there would mean spending real USDC just to validate the flow. So we built a second provider ourselves (`demo_provider/`), speaking the exact same official x402 protocol against Base **Sepolia testnet** — same security, same code path, zero real cost — and used it to prove the full payment loop end to end.

## Challenges we ran into

- **Serverless state is a real footgun for agents.** An ADK agent object is built once when the Cloud Run container starts and reused across every unrelated session afterward. A correlation ID or idempotency key captured in a closure at construction time leaks between completely different requests. Fixed by pulling everything session-specific from the ADK's own per-invocation `ToolContext`.
- **The x402 "exact" scheme is a signed EIP-3009 authorization (EIP-712)**, and Circle's raw wallet API needs `types.EIP712Domain` present explicitly in the payload — something higher-level SDKs derive silently and never surface. Missing it would have made every real signature fail.
- **Wallet addresses from Circle come lowercase** (valid, but not EIP-55 checksummed) — the facilitator's web3.py client rejected them outright with "only accepts checksum addresses."
- **A dependency version mismatch broke real payments silently**: `hexbytes` 2.0's `.hex()` stopped returning the `"0x"` prefix that the x402 SDK's facilitator interface expects back. Only surfaced when we tried a real (not mocked) transaction.
- **Testing `adk run` locally never proved the deployed server worked.** The Cloud Run service returned 500 on every real request because `.env` is a local-only convenience the ADK CLI reads — the deployed server needed the same variables set explicitly on the service itself. We only caught this by calling the live `.run.app` URL directly, not just checking that the process started.
- **A network-string comparison bug** (`"sepolia" in network`) always evaluated false against the real CAIP-2 format (`eip155:84532`), silently routing every testnet verification to the wrong (mainnet) RPC endpoints.

## Accomplishments that we're proud of

A real, independently-verified transaction — signed via Circle's MPC custody, settled through the official x402 protocol, confirmed by reading the raw blockchain receipt ourselves — executed by calling the actual deployed Cloud Run service, not a local script. 28 automated tests covering the budget guard, idempotency, EIP-712 signing, on-chain verification, and RPC network selection.

## What we learned

Two AI opinions — the agent and its auditor — can both be wrong at the same time. The only thing that actually prevented overspending in testing was a plain deterministic check against a real ledger, not another model's judgment. Defense in depth for an agent that spends money means code that can say no even when every LLM in the loop says yes.

## What's next

More real providers, adaptive routing between them, and letting the agent's own spend history inform its own budget policy — always bounded by the same principle: AI opinions are a signal, never the final word on whether money moves.
```

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
**https://youtu.be/XsQc7Wyndxc** (publicado 25/08/2026, 2:08, "Não listado")

## Bonus
- [x] **Blog post PUBLICADO** (25/08):
  https://dev.to/ibcorrea/building-an-ai-agent-that-shops-gets-audited-and-pays-on-its-own-5hgg
  — público, com a frase de disclosure, link já adicionado ao campo
  de bônus da submissão no Devpost.
- [ ] Post em rede social com a hashtag **#AllThingsAgenticHackathon**
  (X, LinkedIn, Instagram ou Facebook) — ainda não feito, opcional.
