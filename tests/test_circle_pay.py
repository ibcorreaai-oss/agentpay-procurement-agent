import json
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from procurement_agent.tools.circle_pay import CircleEvmSigner


@dataclass
class FakeDomain:
    name: str
    version: str
    chain_id: int
    verifying_contract: str


@dataclass
class FakeField:
    name: str
    type: str


def test_sign_typed_data_converts_domain_to_camel_case_and_returns_bytes():
    with patch("procurement_agent.tools.circle_pay.dcw") as mock_dcw, \
         patch("procurement_agent.tools.circle_pay.circle_utils") as mock_utils:
        mock_utils.init_developer_controlled_wallets_client.return_value = MagicMock()
        mock_utils.generate_entity_secret_ciphertext.return_value = "fake-ciphertext"

        mock_signing_api_instance = MagicMock()
        mock_signing_api_instance.sign_typed_data.return_value = MagicMock(
            data=MagicMock(signature="0x" + "ab" * 65)
        )
        mock_dcw.SigningApi.return_value = mock_signing_api_instance
        mock_dcw.SignTypedDataRequest = MagicMock(side_effect=lambda **kw: kw)

        signer = CircleEvmSigner(
            api_key="fake-key",
            entity_secret="fake-secret",
            wallet_id="wallet-123",
            wallet_address="0xAgentAddress",
        )

        domain = FakeDomain(name="USD Coin", version="2", chain_id=8453, verifying_contract="0xTokenAddress")
        types = {"TransferWithAuthorization": [FakeField(name="from", type="address")]}
        message = {"from": "0xAgentAddress", "to": "0xPayTo", "value": "2000"}

        sig = signer.sign_typed_data(domain, types, "TransferWithAuthorization", message)

        assert isinstance(sig, bytes)
        assert len(sig) == 65

        sent_kwargs = mock_signing_api_instance.sign_typed_data.call_args.kwargs
        payload = json.loads(sent_kwargs["sign_typed_data_request"]["data"])
        assert payload["domain"]["chainId"] == 8453
        assert payload["domain"]["verifyingContract"] == "0xTokenAddress"
        assert "chain_id" not in payload["domain"]
        assert "verifying_contract" not in payload["domain"]
        assert payload["primaryType"] == "TransferWithAuthorization"

        # EIP712Domain precisa estar presente em types, listando exatamente
        # os campos que existem no domain (Circle exige isso explicitamente,
        # o SDK oficial x402 nao inclui porque delega pro eth_account, que
        # deriva sozinho -- a API crua da Circle nao deriva).
        domain_type_fields = {f["name"] for f in payload["types"]["EIP712Domain"]}
        assert domain_type_fields == {"name", "version", "chainId", "verifyingContract"}


def test_signer_address_property():
    with patch("procurement_agent.tools.circle_pay.dcw"), \
         patch("procurement_agent.tools.circle_pay.circle_utils") as mock_utils:
        mock_utils.init_developer_controlled_wallets_client.return_value = MagicMock()
        signer = CircleEvmSigner(
            api_key="k", entity_secret="s", wallet_id="w", wallet_address="0xABC",
        )
        assert signer.address == "0xABC"
