"use client";

import { useRef, useState } from "react";
import { Send } from "lucide-react";

type Msg = { role: "user" | "assistant"; content: string };

const SUGGESTIONS = [
  "Compare BASS-II and Saffire-III",
  "Which materials should be banned for the rover?",
  "Give me data for a predictive model",
];

export default function ChatPanel({ investigationId }: { investigationId?: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next, investigationId }),
      });
      const data = await res.json();
      setMessages([...next, { role: "assistant", content: data.text ?? data.error ?? "No response." }]);
    } catch {
      setMessages([...next, { role: "assistant", content: "Could not reach the assistant. Check your connection and try again." }]);
    } finally {
      setLoading(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <aside className="flex h-full flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold">Ask about this data</h2>
        <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">SI</span>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "ml-6 rounded-xl bg-slate-900 p-3 text-white"
                : "mr-6 whitespace-pre-wrap rounded-xl bg-slate-100 p-3"
            }
          >
            {m.content}
          </div>
        ))}
        {loading && <div className="mr-6 rounded-xl bg-slate-100 p-3 text-slate-500">Thinking…</div>}
        <div ref={endRef} />
      </div>

      {messages.length === 0 && (
        <div className="space-y-2 px-4 pb-3">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="block w-full rounded-md border border-slate-200 px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-slate-100 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask across all studies and papers…"
          className="min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-orange-500"
        />
        <button
          type="submit"
          disabled={loading}
          aria-label="Send"
          className="rounded-md bg-orange-500 px-3 text-white disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </form>
    </aside>
  );
}
