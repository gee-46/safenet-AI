/**
 * SafeNet AI — History Screen
 * ------------------------------
 * Lists recent scam reports from GET /calls/reports and currency scans from GET /currency/reports.
 */
import React, { useCallback, useEffect, useState } from "react";
import { View, FlatList, StyleSheet, RefreshControl } from "react-native";
import { Text, Card, Chip, ActivityIndicator, HelperText, Button, SegmentedButtons } from "react-native-paper";
import api from "../../services/api";

interface ScamReport {
  id: string;
  caller_number: string;
  scam_type: string;
  confidence_score: number;
  status: string;
  city: string | null;
  state: string | null;
  created_at: string;
}

interface CounterfeitReport {
  id: string;
  denomination: number;
  verdict: "genuine" | "counterfeit" | "uncertain";
  confidence_score: number;
  city: string | null;
  state: string | null;
  created_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  confirmed: "#00D4A0",
  pending: "#FFB020",
  false_positive: "#6B7280",
  escalated: "#FF3B47",
};

const VERDICT_COLOR: Record<string, string> = {
  genuine: "#00D4A0",
  counterfeit: "#FF3B47",
  uncertain: "#FFB020",
};

function formatDate(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function maskNumber(number: string): string {
  if (!number) return "";
  if (number.length < 7) return number;
  return number.slice(0, 4) + "••••" + number.slice(-3);
}

export default function HistoryScreen() {
  const [historyType, setHistoryType] = useState<"calls" | "currency">("calls");
  const [scamReports, setScamReports] = useState<ScamReport[]>([]);
  const [currencyReports, setCurrencyReports] = useState<CounterfeitReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    setError(null);
    try {
      if (historyType === "calls") {
        const { data } = await api.get<ScamReport[]>("/calls/reports", {
          params: { page: 1, page_size: 50, days_back: 90 },
        });
        setScamReports(data);
      } else {
        const { data } = await api.get<CounterfeitReport[]>("/currency/reports", {
          params: { page: 1, page_size: 50, days_back: 90 },
        });
        setCurrencyReports(data);
      }
    } catch (e: any) {
      setError(e?.message || `Failed to load ${historyType === "calls" ? "scam reports" : "currency scans"}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [historyType]);

  useEffect(() => {
    setLoading(true);
    fetchReports();
  }, [fetchReports]);

  if (loading && (historyType === "calls" ? scamReports.length === 0 : currencyReports.length === 0)) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#4D9EFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text variant="headlineSmall" style={styles.heading}>
        Incident History
      </Text>
      
      <View style={styles.segmentedContainer}>
        <SegmentedButtons
          value={historyType}
          onValueChange={(val) => setHistoryType(val as "calls" | "currency")}
          buttons={[
            { value: "calls", label: "Scam Calls", icon: "phone" },
            { value: "currency", label: "Note Scans", icon: "banknote" },
          ]}
          theme={{ colors: { secondaryContainer: "#141D35", onSecondaryContainer: "#FFFFFF" } }}
        />
      </View>

      {error && (historyType === "calls" ? scamReports.length === 0 : currencyReports.length === 0) ? (
        <View style={styles.centered}>
          <HelperText type="error">{error}</HelperText>
          <Button mode="contained" onPress={fetchReports}>
            Retry
          </Button>
        </View>
      ) : (
        <FlatList
          data={(historyType === "calls" ? scamReports : currencyReports) as any[]}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                fetchReports();
              }}
              tintColor="#4D9EFF"
            />
          }
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              No items yet. Reports will appear here once scans or analyses are performed.
            </Text>
          }
          renderItem={({ item }) => {
            if (historyType === "calls") {
              const r = item as ScamReport;
              return (
                <Card style={styles.card}>
                  <Card.Content>
                    <View style={styles.row}>
                      <Text style={styles.titleText}>{maskNumber(r.caller_number)}</Text>
                      <Chip
                        style={{ backgroundColor: `${STATUS_COLOR[r.status] ?? "#6B7280"}22` }}
                        textStyle={{ color: STATUS_COLOR[r.status] ?? "#6B7280", fontSize: 11 }}
                      >
                        {r.status.replace(/_/g, " ")}
                      </Chip>
                    </View>
                    <Text style={styles.subTitleText}>{r.scam_type.replace(/_/g, " ")}</Text>
                    <View style={styles.metaRow}>
                      <Text style={styles.metaText}>
                        {r.city ? `${r.city}, ` : ""}
                        {r.state ?? "Unknown location"}
                      </Text>
                      <Text style={styles.metaText}>{formatDate(r.created_at)}</Text>
                    </View>
                    <Text style={styles.confidence}>{Math.round(r.confidence_score * 100)}% confidence</Text>
                  </Card.Content>
                </Card>
              );
            } else {
              const c = item as CounterfeitReport;
              return (
                <Card style={styles.card}>
                  <Card.Content>
                    <View style={styles.row}>
                      <Text style={styles.titleText}>₹{c.denomination} Note</Text>
                      <Chip
                        style={{ backgroundColor: `${VERDICT_COLOR[c.verdict] ?? "#6B7280"}22` }}
                        textStyle={{ color: VERDICT_COLOR[c.verdict] ?? "#6B7280", fontSize: 11 }}
                      >
                        {c.verdict.toUpperCase()}
                      </Chip>
                    </View>
                    <Text style={[styles.subTitleText, { color: VERDICT_COLOR[c.verdict] }]}>
                      Verdict: {c.verdict}
                    </Text>
                    <View style={styles.metaRow}>
                      <Text style={styles.metaText}>
                        {c.city ? `${c.city}, ` : ""}
                        {c.state ?? "Unknown location"}
                      </Text>
                      <Text style={styles.metaText}>{formatDate(c.created_at)}</Text>
                    </View>
                    <Text style={styles.confidence}>{Math.round(c.confidence_score * 100)}% confidence</Text>
                  </Card.Content>
                </Card>
              );
            }
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0E1A" },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#0A0E1A" },
  heading: { color: "#FFFFFF", fontWeight: "700", padding: 16, paddingBottom: 8 },
  segmentedContainer: { paddingHorizontal: 16, marginBottom: 12 },
  listContent: { paddingHorizontal: 16, paddingBottom: 24 },
  card: { marginBottom: 10, backgroundColor: "#141D35" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  titleText: { color: "#FFFFFF", fontWeight: "600", fontSize: 15 },
  subTitleText: { color: "#FF3B47", textTransform: "capitalize", marginBottom: 6, fontWeight: "600" },
  metaRow: { flexDirection: "row", justifyContent: "space-between" },
  metaText: { color: "#94A3B8", fontSize: 12 },
  confidence: { color: "#4D9EFF", fontSize: 12, marginTop: 6, fontWeight: "600" },
  emptyText: { color: "#6B7280", textAlign: "center", marginTop: 40, paddingHorizontal: 24 },
});
