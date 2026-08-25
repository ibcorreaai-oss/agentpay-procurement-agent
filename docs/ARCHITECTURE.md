# Arquitetura

```mermaid
sequenceDiagram
    participant U as Solicitação (task)
    participant R as procurement_agent (Gemini 3.5, ADK)
    participant P as Provedores x402 (scrape402, etc)
    participant A as spend_auditor (Gemini 3.5, sub-agente ADK)
    participant BG as budget_guard + idempotency (código, determinístico)
    participant C as Circle (custódia MPC, assina EIP-712)
    participant X as x402 SDK oficial (liquida on-chain)
    participant V as onchain_verify (independente)
    participant F as Firestore (ledger + auditoria)

    U->>R: "compare provedores e compre o melhor"
    R->>P: GET/POST (sem pagamento)
    P-->>R: HTTP 402 + cotação (preço, payTo, asset, network)
    R->>A: audita esta decisão (preço, justificativa)
    A-->>R: aprovado / vetado + motivo
    R->>BG: pode gastar X USDC agora?
    BG->>F: soma gasto confirmado nas últimas 24h
    F-->>BG: total
    BG-->>R: permitido / vetado (teto por chamada + teto diário)
    R->>C: assina EIP-712 (transferWithAuthorization)
    C-->>R: assinatura (nunca a chave privada)
    R->>X: reenvia requisição com prova de pagamento
    X->>P: liquida on-chain, libera o dado
    P-->>X: dado + header de settlement (tx_hash)
    X-->>R: dado + tx_hash
    R->>V: confirma de verdade lendo o evento Transfer on-chain
    V-->>R: confirmado / não bate / RPC indisponível
    R->>F: grava resultado final no ledger
    R-->>U: resumo (provedor, preço, tx_hash, dado)
```

## Por que cada peça existe

- **`spend_auditor` como sub-agente ADK, não uma chamada solta**: separa
  quem decide (agente principal) de quem audita (auditor), com contrato
  de saída estruturado (`AuditVerdict`). Testável e substituível
  independente do resto.

- **`budget_guard` roda DEPOIS da auditoria e pode vetar mesmo com
  aprovação**: os dois modelos de LLM podem concordar e ainda assim
  estar errados (alucinação, prompt injection do provedor, etc). O teto
  é matemática determinística sobre o ledger real, não outra opinião de
  LLM.

- **Assinatura via Circle (MPC), não chave privada no processo**: o
  agente nunca tem acesso a uma chave capaz de mover fundos além do que
  a Circle autoriza via API. Mesmo padrão de custódia não-custodiada
  usado no projeto anterior (AgentPay), agora aplicado ao protocolo
  x402 "exact" real (EIP-3009) em vez de um transfer direto caseiro.

- **`onchain_verify` é independente do `x402` SDK**: o SDK oficial
  liquida o pagamento e devolve um header de settlement — mas nós lemos
  o evento `Transfer` direto da rede, com nosso próprio parsing, antes
  de marcar qualquer coisa como confirmada. Se o facilitator mentir ou
  falhar parcialmente, isso não vira verdade automaticamente pro nosso
  ledger.

- **Firestore em vez de SQLite local**: o Cloud Run é stateless — cada
  instância nova começa com filesystem vazio. O ledger precisa
  sobreviver entre execuções e escalar horizontalmente.

## Categorias de erro tratadas explicitamente

| Situação | Tratamento |
|---|---|
| RPC caiu durante a verificação, mas o pagamento já foi liquidado | `RpcUnavailableError` — fica `PENDING_VERIFY`, nunca reenvia pagamento |
| Recibo on-chain não bate com o esperado | `VerificationMismatchError` — marca como falho, não reconcilia sozinho |
| Mesmo pagamento (provedor+valor+escopo) tentado 2x | `idempotency.is_duplicate` bloqueia antes de qualquer chamada de pagamento |
| Orçamento diário ou por chamada estourado | `budget_guard` veta antes de qualquer chamada de pagamento |
| Credenciais da Circle ausentes | Erro claro e acionável (`MissingCircleCredentialsError`), não uma exceção genérica |
