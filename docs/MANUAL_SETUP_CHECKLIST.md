# Checklist manual — só o que exige login humano

**Status: CONCLUÍDO (25/08).** Circle configurada, credenciais aplicadas
no Cloud Run, pagamento real validado contra o serviço deployado (tx
`0xca2aa6adde336b0276af2274445901df0f235d73f74def8463a9fd6a78e6e0f3`,
Base Sepolia). Este arquivo fica só como histórico do passo manual que
foi necessário — nenhuma ação pendente aqui.

---

Tudo o resto do projeto já está construído, testado e deployado. Isto
aqui foi a ÚNICA parte que não dava pra automatizar: gerar credenciais da
Circle exige login no console web deles (2FA, sem forma de fazer
programaticamente, e por segurança nenhum agente deve digitar sua
senha).

## 1. Gerar API key + entity secret na Circle

1. Entre em https://console.circle.com com a conta já usada no AgentPay original.
2. Vá em **API Keys** → **Create API Key** (ambiente **Testnet** primeiro, pra testar sem risco).
3. Copie a API key gerada.
4. Vá em **Entity Secret** (ou **Configurator**) → gere o entity secret. A Circle mostra
   uma frase/hex de 32 bytes — **copie e guarde em local seguro** (não dá pra ver de novo depois).
5. **Registre** o entity secret (o próprio console guia esse passo — normalmente é
   rodar um script/CLI deles uma vez, ou colar a chave pública e confirmar).

## 2. Criar a wallet do agente

Depois que a API key + entity secret estiverem prontos, isso aqui é automatizável — me avise
que eu crio a wallet set + wallet via SDK (`WalletsApi`), sem precisar de mais nenhum clique
manual.

## 3. Preencher o `.env`

Depois dos passos acima, cole em `procurement_agent/.env` (nunca commitado — já está no `.gitignore`):

```
CIRCLE_API_KEY=<sua api key>
CIRCLE_ENTITY_SECRET=<seu entity secret hex>
CIRCLE_WALLET_ID=<preenchido automaticamente quando eu criar a wallet>
CIRCLE_WALLET_ADDRESS=<preenchido automaticamente quando eu criar a wallet>
```

E as mesmas 4 variáveis como **variáveis de ambiente no Cloud Run** (não só local) —
me avise depois de preencher o `.env` local que eu aplico no serviço deployado também
(`gcloud run services update ... --set-env-vars`).

## 4. Financiar a wallet (testnet primeiro)

USDC de testnet Base Sepolia: https://faucet.circle.com — grátis, sem limite prático.
Depois de validar tudo funcionando em testnet, decidimos juntos se vale migrar pra
mainnet (dinheiro real, ver seção "scrape402" no `README.md` — mainnet já foi
autorizado por você pra até alguns centavos de teste).

## Depois disso

Assim que o `.env` estiver preenchido, me avise — eu:
1. Testo 1 pagamento real de ponta a ponta (testnet).
2. Aplico as mesmas variáveis no Cloud Run.
3. Testo de novo contra o serviço deployado (não só local).
4. Gravo o vídeo de demo com a transação real.
