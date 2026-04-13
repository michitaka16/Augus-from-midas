/**
 * Debate Chat page — the USP (M08-10).
 *
 * Interactive conversation with the AI. Every claim cites a signal,
 * backtest, or cost model output. Citations are clickable cards.
 * The AI defends its positions with data and resists sycophancy.
 */

"use client";

import { useState, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { type: string; id: string; display_value: string }[];
  timestamp: string;
}

export default function DebatePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Load conversation history on mount
  useEffect(() => {
    async function loadHistory() {
      try {
        const { debate } = await import("@/lib/api");
        const token = localStorage.getItem("midas_token") ?? "";
        const res = (await debate.getHistory(token)) as { messages?: Message[] };
        if (res.messages && res.messages.length > 0) {
          setMessages(res.messages);
        } else {
          // Show welcome message if no history
          setMessages([{
            id: "welcome",
            role: "assistant",
            content:
              "I'm your portfolio debate agent. Ask me about any allocation decision, " +
              "regime signal, or backtest result. Every claim I make will cite specific data. " +
              "Challenge me — I'll defend my positions unless you show me better evidence.",
            timestamp: new Date().toISOString(),
          }]);
        }
      } catch {
        setMessages([{
          id: "welcome",
          role: "assistant",
          content:
            "I'm your portfolio debate agent. Ask me about any allocation decision, " +
            "regime signal, or backtest result. Challenge me with data.",
          timestamp: new Date().toISOString(),
        }]);
      }
    }
    loadHistory();
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { debate } = await import("@/lib/api");
      const token = localStorage.getItem("midas_token") ?? "";
      const result = await debate.sendMessage(token, userMsg.content);
      const resp = (result as { response: { content: string; citations?: { type: string; id: string; display_value: string }[]; suggested_followups?: string[] } }).response;

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: resp.content ?? "No response from debate agent.",
        citations: resp.citations ?? [],
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (e) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Could not reach the debate agent. ${e instanceof Error ? e.message : "Check if the API is running."}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      <h1 className="text-2xl font-bold mb-4">Debate</h1>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-accent-primary text-white"
                  : "bg-bg-surface border border-border"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {msg.citations.map((cite, i) => (
                    <button
                      key={i}
                      className="text-xs px-2 py-1 rounded bg-accent-muted text-accent-primary hover:bg-accent-primary/20 transition-colors"
                    >
                      [{cite.type}: {cite.id}]
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-bg-surface border border-border rounded-xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-text-muted rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Followups */}
      <div className="flex gap-2 mb-3">
        {["Why commodities?", "Show backtest", "What if I skip?"].map(
          (suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInput(suggestion)}
              className="text-sm px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:bg-bg-surface transition-colors"
            >
              {suggestion}
            </button>
          ),
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Challenge the AI's reasoning..."
          className="flex-1 px-4 py-3 rounded-xl bg-bg-surface border border-border focus:border-accent-primary focus:outline-none text-text-primary placeholder-text-muted"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="px-6 py-3 rounded-xl bg-accent-primary hover:bg-accent-hover text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
