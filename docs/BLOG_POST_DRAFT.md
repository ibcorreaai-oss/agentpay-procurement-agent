<!--
Rascunho pro "Optional Developer Contribution" da submissao (blog/podcast/video
cobrindo como o projeto foi construido, publicado em plataforma publica tipo
dev.to/medium.com, com a frase obrigatoria de que foi escrito pra participar
do hackathon). Vale ate 0.2 ponto bonus na nota final.

Pendente: publicar em dev.to (ou medium.com) -- isso e uma acao pequena que
EU (Claude) NAO devo fazer sozinho sem autorizacao (postar conteudo publico
em nome do Igor e "Explicit permission required"). Deixar pronto aqui, Igor
decide se quer publicar e onde (precisa de conta dev.to/medium dele).
-->

# Building an AI Agent That Shops, Gets Audited, and Pays — On Its Own

*Written for the All Things Agentic Hackathon (Google).*

Most "autonomous agent" demos stop at reasoning. This one doesn't: it
decides it needs a piece of data, compares real prices across multiple
third-party providers using the x402 HTTP payment protocol, has its
spending decision reviewed by a second AI agent, and then actually pays
— real USDC, signed via MPC custody, verified independently on-chain.

## The shape of the problem

Payment is the part everyone skips in agent demos, for a good reason:
it's the part where a hallucination costs real money. So the design
question wasn't "can an agent pay for something" — it's "how do you
build an agent that can be trusted to pay for something, autonomously,
repeatedly, without a human approving every transaction."

## What actually enforces trust here

Two AI models are involved — the primary agent decides, a separate
auditor agent reviews — but the real safety net isn't either of them.
It's a budget guard that runs as plain deterministic code: it reads the
last 24 hours of confirmed spend from the ledger and vetoes the payment
if it would exceed a pre-approved cap, regardless of what either model
concluded. Two AI opinions can still both be wrong; arithmetic against
a real ledger can't.

The same principle shows up in verification: after the payment SDK
reports a transaction hash, the agent doesn't just trust that string.
It independently reads the `Transfer` event straight off the chain and
confirms the amount and recipient match before marking anything as
confirmed.

## What surprised us

- The x402 "exact" payment scheme isn't a simple transfer — it's a
  signed EIP-3009 authorization (EIP-712), and getting that signature
  right against a *raw* wallet custody API (rather than a convenience
  SDK that hides the details) required manually reconstructing a piece
  of the EIP-712 payload — `types.EIP712Domain` — that higher-level
  libraries derive for you and never surface. Missing it would have
  made every real signature fail silently.
- Serverless reuse is a real footgun for agent state: an agent object
  built once at deploy time gets reused across many unrelated sessions
  on the same instance. Anything session-specific has to come from the
  framework's own per-invocation context, never a variable captured
  when the agent was constructed — we found and fixed this exact bug
  in code review before it ever reached a user.

## What's next

More providers, adaptive routing between them, and eventually letting
the agent's own spend history inform its own budget policy — bounded,
always, by the same principle: two AI opinions are a signal, not a
lock. The code that actually moves money stays boring, deterministic,
and independently checked.

---

*Code: [github.com/ibcorreaai-oss/agentpay-procurement-agent](https://github.com/ibcorreaai-oss/agentpay-procurement-agent)*
*Built for the Taskmaster category of Google's All Things Agentic Hackathon.*
