"""_rpc_urls_for tinha um bug real achado testando pagamento de verdade:
comparava `"sepolia" in network`, mas o formato CAIP-2 (`eip155:84532`)
nunca contem essa palavra -- toda verificacao de testnet ia pro RPC de
mainnet errado."""

from procurement_agent.agent import BASE_MAINNET_RPC_URLS, BASE_SEPOLIA_RPC_URLS, _rpc_urls_for


def test_base_sepolia_network_uses_sepolia_rpcs():
    assert _rpc_urls_for("eip155:84532") == BASE_SEPOLIA_RPC_URLS


def test_base_mainnet_network_uses_mainnet_rpcs():
    assert _rpc_urls_for("eip155:8453") == BASE_MAINNET_RPC_URLS


def test_unknown_network_defaults_to_mainnet_rpcs():
    assert _rpc_urls_for("eip155:1") == BASE_MAINNET_RPC_URLS
