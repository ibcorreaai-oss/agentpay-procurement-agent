"""Constroi o CircleEvmSigner a partir de variaveis de ambiente.

Modulo separado (nao dentro de circle_pay.py) porque essa e a UNICA
peca do projeto que depende de credenciais que so o Igor pode gerar --
API key + entity secret exigem login manual no console.circle.com (ver
docs/MANUAL_SETUP_CHECKLIST.md). Isolar isso aqui deixa claro, so de
olhar os imports, que so este arquivo fica bloqueado ate o setup manual
-- todo o resto do agente (cotacao, auditoria, ledger, verificacao
on-chain) funciona e e testavel sem essas credenciais."""

from __future__ import annotations

import os

from procurement_agent.tools.circle_pay import CircleEvmSigner

_REQUIRED_ENV_VARS = [
    "CIRCLE_API_KEY",
    "CIRCLE_ENTITY_SECRET",
    "CIRCLE_WALLET_ID",
    "CIRCLE_WALLET_ADDRESS",
]


class MissingCircleCredentialsError(RuntimeError):
    pass


def build_signer_from_env() -> CircleEvmSigner:
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise MissingCircleCredentialsError(
            "Credenciais da Circle ausentes: " + ", ".join(missing) + ". "
            "Siga docs/MANUAL_SETUP_CHECKLIST.md (passo manual, exige login em "
            "console.circle.com) e preencha o .env antes de executar pagamentos reais."
        )
    return CircleEvmSigner(
        api_key=os.environ["CIRCLE_API_KEY"],
        entity_secret=os.environ["CIRCLE_ENTITY_SECRET"],
        wallet_id=os.environ["CIRCLE_WALLET_ID"],
        wallet_address=os.environ["CIRCLE_WALLET_ADDRESS"],
    )
