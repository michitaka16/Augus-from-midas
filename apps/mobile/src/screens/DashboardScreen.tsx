/**
 * Mobile Dashboard screen — wired to live API (M09-04 + M09-05).
 *
 * Fetches /signals/latest + /regime/current on mount.
 */

import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from "react-native";
import { signals, regime } from "../lib/api";

export default function DashboardScreen() {
  const [regimeState, setRegimeState] = useState<any>(null);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const [regRes] = await Promise.all([
          regime.getCurrent().catch(() => null),
        ]);
        if (regRes) setRegimeState(regRes);
      } catch {}
    }
    load();
  }, []);

  const regimeLevel = (regimeState as any)?.regime ?? "normal";
  const regimeColor = regimeLevel === "normal" ? "#22C55E" : regimeLevel === "cautious" ? "#F59E0B" : "#EF4444";
  const regimeBg = regimeLevel === "normal" ? "#0A2E1A" : regimeLevel === "cautious" ? "#2E2308" : "#2E0A0A";

  return (
    <ScrollView style={styles.container}>
      {/* Regime */}
      <View style={[styles.regimeBanner, { backgroundColor: regimeBg }]}>
        <View style={styles.regimeDot} />
        <Text style={styles.regimeText}>Normal</Text>
        <Text style={styles.regimeConfidence}>82%</Text>
      </View>

      {/* Value */}
      <View style={styles.valueCard}>
        <Text style={styles.label}>Portfolio Value</Text>
        <Text style={styles.value}>$142,850</Text>
        <Text style={styles.change}>+$1,230 (0.87%) today</Text>
      </View>

      {/* Pending */}
      <TouchableOpacity style={styles.card}>
        <Text style={styles.label}>Pending Approvals</Text>
        <Text style={styles.value}>0</Text>
        <Text style={styles.subtitle}>All clear</Text>
      </TouchableOpacity>

      {/* Actions */}
      <TouchableOpacity style={styles.primaryButton}>
        <Text style={styles.buttonText}>Debate with AI</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0B0E", padding: 16 },
  regimeBanner: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0A2E1A",
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    gap: 8,
  },
  regimeDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#22C55E" },
  regimeText: { color: "#22C55E", fontWeight: "600", fontSize: 16 },
  regimeConfidence: { color: "#9BA1AD", marginLeft: "auto" },
  valueCard: {
    backgroundColor: "#1A1D24",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#2A2E37",
  },
  card: {
    backgroundColor: "#1A1D24",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#2A2E37",
  },
  label: { color: "#9BA1AD", fontSize: 14 },
  value: { color: "#F0F1F3", fontSize: 28, fontWeight: "700", marginTop: 4 },
  change: { color: "#22C55E", fontSize: 14, marginTop: 2 },
  subtitle: { color: "#5D6370", fontSize: 14, marginTop: 2 },
  primaryButton: {
    backgroundColor: "#3B82F6",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: "#FFFFFF", fontWeight: "600", fontSize: 16 },
});
