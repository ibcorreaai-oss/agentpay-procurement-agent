"""Signer EIP-712 usando a custodia MPC da Circle (Developer-Controlled
Wallets) -- implementa o protocolo `ClientEvmSigner` do SDK oficial
`x402` (mesmo usado pelo scrape402 e outros provedores reais), mas a
assinatura nunca usa uma chave privada crua no nosso processo.

Mesmo principio de design do AgentPay original (custodia MPC, gas
patrocinado, nenhuma chave privada no app) -- so que agora contra o
protocolo x402 "exact" de verdade (EIP-3009 transferWithAuthorization
assinado via EIP-712), nao mais um transfer direto caseiro.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from circle.web3 import developer_controlled_wallets as dcw
from circle.web3 import utils as circle_utils

from procurement_agent.logging_setup import get_logger, log_event

logger = get_logger(__name__)

# EIP-712 exige que "types" descreva TAMBEM os campos do proprio "domain"
# via uma entrada "EIP712Domain" -- o SDK oficial x402 NAO inclui isso (ele
# usa `eth_account.sign_typed_data(domain_data=..., message_types=...)`,
# que deriva isso sozinho por baixo dos panos). A API crua da Circle
# (`eth_signTypedData_v4` padrao) espera o JSON completo, entao temos que
# montar essa entrada manualmente -- confirmado contra o exemplo oficial
# da documentacao da Circle antes de escrever este codigo. So inclui os
# campos que realmente aparecerem no domain (mesmo padrao do exemplo
# oficial, que so lista os campos presentes).
_EIP712_DOMAIN_FIELD_TYPES = {
    "name": "string",
    "version": "string",
    "chainId": "uint256",
    "verifyingContract": "address",
    "salt": "bytes32",
}


class CircleEvmSigner:
    """Satisfaz `x402.mechanisms.evm.signer.ClientEvmSigner`:
    precisa so de `.address` (str) e `.sign_typed_data(domain, types,
    primary_type, message) -> bytes` (assinatura de 65 bytes)."""

    def __init__(
        self,
        api_key: str,
        entity_secret: str,
        wallet_id: str,
        wallet_address: str,
    ):
        self._api_key = api_key
        self._entity_secret = entity_secret
        self._wallet_id = wallet_id
        self._address = wallet_address
        api_client = circle_utils.init_developer_controlled_wallets_client(
            api_key=api_key, entity_secret=entity_secret
        )
        self._signing_api = dcw.SigningApi(api_client)

    @property
    def address(self) -> str:
        return self._address

    def sign_typed_data(
        self,
        domain: Any,
        types: dict[str, list[Any]],
        primary_type: str,
        message: dict[str, Any],
    ) -> bytes:
        types_json = {
            type_name: [asdict(f) if not isinstance(f, dict) else f for f in fields]
            for type_name, fields in types.items()
        }
        domain_json = asdict(domain) if not isinstance(domain, dict) else domain
        # EIP-712 usa camelCase no domain; TypedDataDomain do x402 usa snake_case
        if "chain_id" in domain_json:
            domain_json["chainId"] = domain_json.pop("chain_id")
        if "verifying_contract" in domain_json:
            domain_json["verifyingContract"] = domain_json.pop("verifying_contract")

        types_json["EIP712Domain"] = [
            {"name": field_name, "type": _EIP712_DOMAIN_FIELD_TYPES[field_name]}
            for field_name in domain_json
            if field_name in _EIP712_DOMAIN_FIELD_TYPES
        ]

        typed_data_payload = json.dumps(
            {
                "types": types_json,
                "domain": domain_json,
                "primaryType": primary_type,
                "message": message,
            }
        )

        # Ciphertext do entity secret e de USO UNICO (gerado do zero a cada
        # chamada) -- nunca reaproveitar entre requisicoes, e o proprio
        # design de seguranca da Circle.
        ciphertext = circle_utils.generate_entity_secret_ciphertext(
            self._api_key, self._entity_secret
        )

        request = dcw.SignTypedDataRequest(
            wallet_id=self._wallet_id,
            data=typed_data_payload,
            entity_secret_ciphertext=ciphertext,
        )
        response = self._signing_api.sign_typed_data(sign_typed_data_request=request)
        signature_hex = response.data.signature

        log_event(
            logger,
            20,
            "EIP-712 assinado via Circle MPC",
            primary_type=primary_type,
            wallet_address=self._address,
        )

        return bytes.fromhex(signature_hex.removeprefix("0x"))
