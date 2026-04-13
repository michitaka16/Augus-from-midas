"""Tier 1 tests for order preview delta computation (M05-05)."""

import pytest

from midas_broker.orders.preview import compute_order_delta, TradePreview


class TestOrderDelta:
    @pytest.mark.unit
    def test_buy_from_zero(self):
        target = {"equity_sector": 0.5}
        positions = []
        primary = {"equity_sector": "SPY"}
        trades = compute_order_delta(target, positions, 100_000, primary)
        assert len(trades) == 1
        assert trades[0].direction == "buy"
        assert trades[0].ticker == "SPY"
        assert trades[0].estimated_value == pytest.approx(50_000, rel=0.1)

    @pytest.mark.unit
    def test_sell_to_reduce(self):
        target = {"equity_sector": 0.2}
        positions = [{"ticker": "SPY", "quantity": 100, "market_value": 45_000}]
        primary = {"equity_sector": "SPY"}
        trades = compute_order_delta(target, positions, 100_000, primary)
        assert len(trades) == 1
        assert trades[0].direction == "sell"

    @pytest.mark.unit
    def test_skip_small_delta(self):
        target = {"equity_sector": 0.5001}
        positions = [{"ticker": "SPY", "quantity": 100, "market_value": 50_000}]
        primary = {"equity_sector": "SPY"}
        trades = compute_order_delta(target, positions, 100_000, primary)
        # Delta is ~$10 which is below $50 threshold
        assert len(trades) == 0

    @pytest.mark.unit
    def test_multiple_sleeves(self):
        target = {"equity_sector": 0.4, "precious_metals": 0.3}
        positions = []
        primary = {"equity_sector": "SPY", "precious_metals": "GLD"}
        trades = compute_order_delta(target, positions, 100_000, primary)
        assert len(trades) == 2
        tickers = {t.ticker for t in trades}
        assert tickers == {"SPY", "GLD"}

    @pytest.mark.unit
    def test_commission_minimum(self):
        target = {"equity_sector": 0.01}
        positions = []
        primary = {"equity_sector": "SPY"}
        trades = compute_order_delta(target, positions, 100_000, primary)
        if trades:
            assert trades[0].estimated_commission >= 0.35


class TestTokenEncryption:
    """Test OAuth token encryption/decryption round-trip (M05-02)."""

    @pytest.mark.unit
    def test_encrypt_decrypt_round_trip(self, monkeypatch):
        # Set a valid 32-byte key (64 hex chars)
        test_key = "a" * 64
        monkeypatch.setenv("IBKR_TOKEN_ENCRYPTION_KEY", test_key)

        from midas_broker.ibkr.oauth import TokenEncryption
        enc = TokenEncryption()

        plaintext = "test-access-token-12345"
        ciphertext = enc.encrypt(plaintext)
        assert isinstance(ciphertext, bytes)
        assert ciphertext != plaintext.encode()

        decrypted = enc.decrypt(ciphertext)
        assert decrypted == plaintext

    @pytest.mark.unit
    def test_different_encryptions_differ(self, monkeypatch):
        test_key = "b" * 64
        monkeypatch.setenv("IBKR_TOKEN_ENCRYPTION_KEY", test_key)

        from midas_broker.ibkr.oauth import TokenEncryption
        enc = TokenEncryption()

        ct1 = enc.encrypt("same-token")
        ct2 = enc.encrypt("same-token")
        # AES-GCM with random nonce should produce different ciphertext
        assert ct1 != ct2
