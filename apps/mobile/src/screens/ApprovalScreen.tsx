/**
 * Mobile Approval Card screen — one-screen approve (M09-06).
 *
 * Push notification → deep link → this screen → biometric → execute.
 * Swipe right to approve, swipe left to skip.
 */

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from "react-native";

export default function ApprovalScreen() {
  const handleApprove = async () => {
    // In production: trigger biometric → submit to API
    Alert.alert(
      "Confirm Trade",
      "Authenticate to approve this rebalance.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Approve",
          onPress: () => {
            // Biometric + API call
          },
        },
      ],
    );
  };

  return (
    <ScrollView style={styles.container}>
      {/* Regime */}
      <View style={styles.regimeBanner}>
        <View style={styles.regimeDot} />
        <Text style={styles.regimeLabel}>Normal Regime</Text>
        <Text style={styles.confidence}>82%</Text>
      </View>

      {/* Header */}
      <Text style={styles.title}>Growth Portfolio</Text>
      <Text style={styles.subtitle}>Weekly Rebalance — 2 trades</Text>

      {/* Trades */}
      <View style={styles.tradeCard}>
        <TradeRow ticker="GLD" direction="BUY" shares={15} value={2847} cost={1.02} />
        <View style={styles.divider} />
        <TradeRow ticker="TLT" direction="SELL" shares={8} value={832} cost={0.68} />
      </View>

      {/* Cost Summary */}
      <View style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Net Cost</Text>
          <Text style={styles.summaryValue}>$1.70</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Impact</Text>
          <Text style={styles.summaryValue}>+0.3% gold exposure</Text>
        </View>
      </View>

      {/* Actions */}
      <TouchableOpacity style={styles.approveButton} onPress={handleApprove}>
        <Text style={styles.approveText}>Approve All</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.skipButton}>
        <Text style={styles.skipText}>Skip</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.debateLink}>
        <Text style={styles.debateLinkText}>Why this rebalance?</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

function TradeRow({ ticker, direction, shares, value, cost }: {
  ticker: string; direction: string; shares: number; value: number; cost: number;
}) {
  const dirColor = direction === "BUY" ? "#22C55E" : "#EF4444";
  return (
    <View style={styles.tradeRow}>
      <View>
        <Text style={styles.ticker}>{ticker}</Text>
        <Text style={[styles.direction, { color: dirColor }]}>
          {direction} {shares} shares
        </Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={styles.tradeValue}>${value.toLocaleString()}</Text>
        <Text style={styles.tradeCost}>Cost: ${cost.toFixed(2)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0B0E", padding: 16 },
  regimeBanner: {
    flexDirection: "row", alignItems: "center", backgroundColor: "#0A2E1A",
    borderRadius: 12, padding: 12, marginBottom: 16, gap: 8,
  },
  regimeDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#22C55E" },
  regimeLabel: { color: "#22C55E", fontWeight: "600" },
  confidence: { color: "#9BA1AD", marginLeft: "auto" },
  title: { color: "#F0F1F3", fontSize: 22, fontWeight: "700" },
  subtitle: { color: "#9BA1AD", fontSize: 14, marginTop: 4, marginBottom: 16 },
  tradeCard: {
    backgroundColor: "#1A1D24", borderRadius: 12, borderWidth: 1,
    borderColor: "#2A2E37", marginBottom: 12, overflow: "hidden",
  },
  tradeRow: {
    flexDirection: "row", justifyContent: "space-between",
    alignItems: "center", padding: 16,
  },
  divider: { height: 1, backgroundColor: "#2A2E37" },
  ticker: { color: "#F0F1F3", fontSize: 16, fontWeight: "600" },
  direction: { fontSize: 14, marginTop: 2 },
  tradeValue: { color: "#F0F1F3", fontSize: 16, fontFamily: "monospace" },
  tradeCost: { color: "#5D6370", fontSize: 12, marginTop: 2 },
  summaryCard: {
    backgroundColor: "#1A1D24", borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: "#2A2E37", marginBottom: 16,
  },
  summaryRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  summaryLabel: { color: "#9BA1AD" },
  summaryValue: { color: "#F0F1F3", fontWeight: "500" },
  approveButton: {
    backgroundColor: "#3B82F6", borderRadius: 12, padding: 16,
    alignItems: "center", marginBottom: 8,
  },
  approveText: { color: "#FFF", fontWeight: "700", fontSize: 16 },
  skipButton: {
    borderWidth: 1, borderColor: "#2A2E37", borderRadius: 12,
    padding: 14, alignItems: "center", marginBottom: 8,
  },
  skipText: { color: "#9BA1AD", fontSize: 16 },
  debateLink: { alignItems: "center", padding: 12 },
  debateLinkText: { color: "#3B82F6", fontSize: 14 },
});
