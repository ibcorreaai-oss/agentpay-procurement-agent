"""Agente auditor -- 2o LlmAgent do ADK, revisa a decisao de gasto do
agente principal ANTES do pagamento executar. Multi-agent nativo do ADK
(nao uma chamada de API solta como no AgentPay original) -- mais forte
pro criterio "Architectural Discipline" da hackathon: separacao clara de
responsabilidades entre quem decide e quem audita.

So aprova se: (1) o preco bate com a cotacao real (nao um valor
inventado), (2) a justificativa e coerente com um agente de orcamento
pre-aprovado (nao um sermao de seguranca generico -- essa e a mesma
armadilha de framing que o AgentPay original ja bateu: dizer "no human
approval available" faz o LLM tratar como cenario perigoso em vez de
avaliar a decisao de verdade)."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from pydantic import BaseModel, Field

AUDITOR_MODEL = "gemini-3.5-flash"


class AuditVerdict(BaseModel):
    approved: bool = Field(description="true se o gasto deve prosseguir, false pra vetar")
    reasoning: str = Field(description="justificativa curta, texto plano, sem markdown")


auditor_agent = Agent(
    model=AUDITOR_MODEL,
    name="spend_auditor",
    description=(
        "Audita UMA decisao de compra de dados de outro agente antes do pagamento "
        "executar. Nao toma a decisao original, so aprova ou veta."
    ),
    instruction=(
        "Voce e o auditor de gastos de um agente autonomo que compra dados via micropagamentos "
        "USDC (x402). Voce recebe: o provedor escolhido, o preco cotado (em USDC), a justificativa "
        "do agente principal, e o orcamento pre-aprovado (teto por chamada e teto diario, ja "
        "configurados e aceitos de antemao -- isso NAO e uma decisao sem supervisao humana, e um "
        "agente operando dentro de limites financeiros ja auditados e aprovados previamente). "
        "Aprove se o preco bate com a cotacao real e a justificativa faz sentido pro que sera "
        "comprado. Vete se o preco parecer inflado sem explicacao, se a justificativa for vaga "
        "ou incoerente, ou se o valor pedido exceder os limites informados. "
        "Responda em texto plano, sem markdown, sem asteriscos."
    ),
    output_schema=AuditVerdict,
)
