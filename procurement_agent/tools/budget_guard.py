"""Teto de orcamento aplicado por CODIGO, nao so texto de prompt.

O AgentPay original documentava "pre-aprovado $0.05/call, $5.00/dia"
apenas como texto dentro do prompt do Claude -- nada no codigo
rejeitava programaticamente se essa regra fosse violada (growth idea
"Adaptive budget ceiling enforcement" do Evolution Review de 23/08,
nunca aplicada). Aqui isso vira um gate real: mesmo que o LLM (decisor)
E o auditor (Gemini) aprovem um gasto, esse guard veta antes de
qualquer chamada de pagamento se o teto seria estourado -- defense in
depth de verdade, "a maquina diz nao" independente do que os 2 modelos
concluiram.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# USDC tem 6 casas decimais on-chain; qualquer diferenca menor que isso e
# ruido de ponto flutuante, nao um estouro de teto real (ex: 5.00 - 4.95
# em float da 0.049999999999999982, nao 0.05 exato).
_EPSILON_USDC = 1e-6


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    spent_today_usdc: float
    remaining_today_usdc: float


def check_budget(
    ledger_client,
    amount_usdc: float,
    per_call_cap_usdc: float = 0.05,
    daily_cap_usdc: float = 5.00,
    now: dt.datetime | None = None,
) -> BudgetDecision:
    if amount_usdc > per_call_cap_usdc + _EPSILON_USDC:
        return BudgetDecision(
            allowed=False,
            reason=f"valor {amount_usdc:.4f} USDC excede o teto por chamada de {per_call_cap_usdc:.4f} USDC",
            spent_today_usdc=0.0,
            remaining_today_usdc=0.0,
        )

    now = now or dt.datetime.now(dt.timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    spent_today = ledger_client.sum_confirmed_spend_since(start_of_day)
    remaining = daily_cap_usdc - spent_today

    if amount_usdc > remaining + _EPSILON_USDC:
        return BudgetDecision(
            allowed=False,
            reason=(
                f"gasto de hoje ja e {spent_today:.4f} USDC de um teto diario de "
                f"{daily_cap_usdc:.4f} USDC -- restam {remaining:.4f} USDC, "
                f"insuficiente pra esta compra de {amount_usdc:.4f} USDC"
            ),
            spent_today_usdc=spent_today,
            remaining_today_usdc=remaining,
        )

    return BudgetDecision(
        allowed=True,
        reason="dentro do teto por chamada e do teto diario",
        spent_today_usdc=spent_today,
        remaining_today_usdc=remaining,
    )
