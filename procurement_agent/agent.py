"""Agente principal (Taskmaster): decide que precisa de um dado de
mercado, compara preco entre provedores x402 reais, pede auditoria de
um agente Gemini separado, e paga sozinho via Circle -- acao real, nao
só conversa.

Arquitetura (cada peca ja testada isoladamente antes de chegar aqui):
  get_price_quote     -> providers.get_quote()          (NUNCA paga)
  spend_auditor          -> AgentTool(auditor_agent)        (multi-agent nativo do ADK, so aprova/veta)
  execute_payment       -> budget_guard + idempotency (gates DETERMINISTICOS,
                            aplicados por codigo, nunca pela LLM) -> providers.pay_and_fetch()
                            (Circle assina EIP-712, x402 SDK oficial liquida)
                            -> onchain_verify.verify_transfer() (verificacao
                            INDEPENDENTE, nunca confia no que o facilitator
                            disse) -> firestore ledger

O teto de orcamento e a idempotencia vetam mesmo que o auditor Gemini
E a LLM principal concordem -- "a maquina diz nao", defense in depth de
verdade (growth idea do AgentPay original nunca aplicada, aplicada aqui
pela primeira vez de verdade)."""

from __future__ import annotations

import dataclasses
import os
from typing import Optional

from google.adk.agents.llm_agent import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext

from procurement_agent.auditor import auditor_agent
from procurement_agent.circle_signer import build_signer_from_env
from procurement_agent.ledger.firestore_client import LedgerClient
from procurement_agent.logging_setup import get_logger, log_event, set_correlation_id
from procurement_agent.tools import budget_guard, idempotency
from procurement_agent.tools.onchain_verify import (
    RpcUnavailableError,
    VerificationMismatchError,
    verify_transfer,
)
from procurement_agent.tools.providers import DataProvider, Quote, get_quote, pay_and_fetch

logger = get_logger(__name__)

ROOT_MODEL = "gemini-3.5-flash"

DEFAULT_PROVIDERS = [
    DataProvider(
        provider_id="scrape402_extract",
        resource_url="https://scrape402.xyz/extract/basic",
        method="POST",
        request_kwargs={"json": {"url": "https://example.com", "format": "markdown"}},
    ),
    DataProvider(
        provider_id="scrape402_diff",
        resource_url="https://scrape402.xyz/diff/snapshot",
        method="POST",
        request_kwargs={"json": {"url": "https://example.com"}},
    ),
]

BASE_MAINNET_RPC_URLS = [
    "https://mainnet.base.org",
    "https://base.llamarpc.com",
    "https://base-rpc.publicnode.com",
]
BASE_SEPOLIA_RPC_URLS = [
    "https://sepolia.base.org",
    "https://base-sepolia-rpc.publicnode.com",
]


def _rpc_urls_for(network: str) -> list[str]:
    return BASE_SEPOLIA_RPC_URLS if "sepolia" in network else BASE_MAINNET_RPC_URLS


def build_root_agent(
    ledger: Optional[LedgerClient] = None,
    providers: Optional[list[DataProvider]] = None,
) -> Agent:
    ledger = ledger or LedgerClient(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    providers = providers if providers is not None else DEFAULT_PROVIDERS

    # IMPORTANTE: `root_agent` e construido 1x no import do modulo, mas o
    # mesmo processo/instancia do Cloud Run atende MUITAS execucoes
    # diferentes (sessoes diferentes, possivelmente concorrentes) ao longo
    # da vida do container. Por isso nada de estado por-execucao pode viver
    # numa closure aqui (correlation_id fixo, dict de cache compartilhado
    # entre TODAS as sessoes) -- isso ja foi um bug real achado na
    # autorrevisao: cotacoes de uma sessao vazavam pra outra, e a chave de
    # idempotencia nao mudava entre execucoes distintas. Estado por-sessao
    # tem que vir do ToolContext do ADK (injetado automaticamente pelo tipo
    # do parametro, nunca aparece pro LLM).

    def list_available_providers() -> list[dict]:
        """Lista os provedores de dados configurados que o agente pode
        comprar. Use isso primeiro pra saber o que existe pra comparar."""
        return [{"provider_id": p.provider_id, "resource_url": p.resource_url} for p in providers]

    def get_price_quote(provider_id: str, tool_context: ToolContext) -> dict:
        """Pega uma cotacao de preco em USDC de um provedor especifico,
        SEM pagar nada. Chame pra cada provedor que quiser comparar antes
        de decidir qual comprar."""
        provider = next((p for p in providers if p.provider_id == provider_id), None)
        if provider is None:
            return {"error": f"provedor '{provider_id}' nao encontrado"}
        quote = get_quote(provider)
        if quote is None:
            return {"error": f"provedor '{provider_id}' nao respondeu com uma cotacao valida agora"}
        tool_context.state[f"quote:{provider_id}"] = dataclasses.asdict(quote)
        return {
            "provider_id": quote.provider_id,
            "price_usdc": quote.price_usdc,
            "description": quote.description,
            "network": quote.network,
        }

    def execute_payment(provider_id: str, justification: str, tool_context: ToolContext) -> dict:
        """Executa o pagamento de verdade pro provedor ja cotado com
        get_price_quote. So chame depois de ter cotado o preco E pedido
        auditoria com spend_auditor. `justification` deve explicar por que
        vale a pena pagar esse preco por esse dado. Pode ser recusado
        mesmo que a auditoria tenha aprovado, se violar o teto de
        orcamento pre-configurado -- isso e um guardrail independente,
        aplicado por codigo, nao pela sua propria decisao."""
        correlation_id = tool_context.invocation_id
        set_correlation_id(correlation_id)

        quote_dict = tool_context.state.get(f"quote:{provider_id}")
        if quote_dict is None:
            return {"error": f"nenhuma cotacao valida em cache pra '{provider_id}' -- chame get_price_quote primeiro"}
        quote = Quote(**quote_dict)

        key = idempotency.payment_key(correlation_id, provider_id, quote.price_usdc)
        if idempotency.is_duplicate(ledger, key):
            return {"error": "esse pagamento ja foi tentado nesta execucao -- nao pago de novo (idempotencia)"}

        decision = budget_guard.check_budget(ledger, quote.price_usdc)
        if not decision.allowed:
            log_event(logger, 30, "pagamento vetado pelo budget guard", provider_id=provider_id, reason=decision.reason)
            return {"error": f"orcamento recusou o pagamento: {decision.reason}"}

        ledger.record_payment_attempt(key, provider_id, quote.price_usdc, correlation_id)
        ledger.record_audit(correlation_id, {"provider_id": provider_id, "justification": justification, "price_usdc": quote.price_usdc})

        try:
            signer = build_signer_from_env()
            result = pay_and_fetch(quote, signer)
        except Exception as exc:
            ledger.mark_failed(key, str(exc))
            log_event(logger, 40, "pagamento falhou", provider_id=provider_id, error=str(exc))
            return {"error": f"pagamento falhou: {exc}"}

        if result.tx_hash is None:
            ledger.mark_failed(key, "settlement sem tx_hash no header de resposta")
            return {"error": "pagamento processado mas sem prova de tx_hash -- tratando como falha"}

        try:
            verified = verify_transfer(
                tx_hash=result.tx_hash,
                rpc_urls=_rpc_urls_for(quote.network),
                token_address=quote.asset,
                expected_to=quote.pay_to,
            )
        except RpcUnavailableError as exc:
            # pagamento pode ja estar confirmado, so a VERIFICACAO falhou --
            # nao marca como falho, fica PENDING_VERIFY pra reconciliar depois
            log_event(logger, 30, "RPC indisponivel na verificacao, deixando pendente", tx_hash=result.tx_hash, error=str(exc))
            return {
                "status": "pago_verificacao_pendente",
                "tx_hash": result.tx_hash,
                "price_usdc": quote.price_usdc,
                "data": result.data,
            }
        except VerificationMismatchError as exc:
            ledger.mark_failed(key, f"verificacao on-chain nao bateu: {exc}")
            return {"error": f"pagamento executado mas a verificacao on-chain independente nao bateu: {exc}"}

        ledger.mark_confirmed(key, result.tx_hash)
        log_event(
            logger, 20, "pagamento confirmado e verificado on-chain",
            provider_id=provider_id, tx_hash=result.tx_hash, price_usdc=quote.price_usdc,
        )
        return {
            "status": "confirmado",
            "tx_hash": result.tx_hash,
            "price_usdc": quote.price_usdc,
            "value_wei_confirmado": verified.value_wei,
            "data": result.data,
        }

    root_agent = Agent(
        model=ROOT_MODEL,
        name="procurement_agent",
        description=(
            "Agente autonomo que decide comprar dados de mercado, compara preco entre "
            "provedores x402 reais, pede auditoria antes de pagar, e paga sozinho via USDC."
        ),
        instruction=(
            "Voce e um agente autonomo de compras (Taskmaster). Sua tarefa: descobrir qual "
            "provedor de dados oferece o melhor preco pra uma extracao de dado, e comprar de "
            "forma autonoma dentro do orcamento pre-aprovado.\n\n"
            "Siga SEMPRE esta sequencia:\n"
            "1. list_available_providers pra ver o que existe.\n"
            "2. get_price_quote pra CADA provedor disponivel -- compare os precos.\n"
            "3. Escolha o provedor com melhor custo-beneficio (nao necessariamente o mais barato "
            "se a descricao indicar qualidade/escopo diferente).\n"
            "4. spend_auditor, passando o provedor escolhido, o preco cotado e sua justificativa -- "
            "isso e obrigatorio, nunca pule esse passo.\n"
            "5. So se spend_auditor aprovar: execute_payment com a mesma justificativa.\n"
            "6. Resuma o resultado final: o que foi comprado, de quem, por quanto, e o hash da "
            "transacao (se confirmado).\n\n"
            "Voce esta operando dentro de um orcamento diario pre-aprovado (nao e uma decisao "
            "sem supervisao -- os limites ja foram definidos e aceitos de antemao). Texto plano, "
            "sem markdown."
        ),
        tools=[
            list_available_providers,
            get_price_quote,
            AgentTool(auditor_agent),
            execute_payment,
        ],
    )
    return root_agent


root_agent = build_root_agent()
