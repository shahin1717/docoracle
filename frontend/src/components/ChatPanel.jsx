import { useState, useRef, useEffect } from "react";
import { streamQuery } from "../api/client";
import { Send, AlertCircle } from "lucide-react";

export default function ChatPanel({ documents = [] }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: "Welcome to DocOracle. Upload documents and ask questions grounded in your own files.",
      sources: [],
      isStreaming: false,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSendMessage() {
    if (!input.trim() || loading) return;

    // Disable RAG if no documents
    if (documents.length === 0) {
      setError("Please upload documents first to ask questions");
      return;
    }

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      text: input,
      sources: [],
      isStreaming: false,
    };

    // Add user message
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    // Create assistant message placeholder
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage = {
      id: assistantId,
      role: "assistant",
      text: "",
      sources: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      await streamQuery(
        input,
        documents.map((d) => d.id),
        (chunk) => {
          // Update assistant message as chunks arrive
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id === assistantId) {
                if (chunk.type === "content") {
                  return {
                    ...msg,
                    text: msg.text + (chunk.content || ""),
                  };
                } else if (chunk.type === "sources") {
                  return {
                    ...msg,
                    sources: chunk.sources || [],
                  };
                }
              }
              return msg;
            })
          );
        },
        (err) => {
          setError(err.message);
          console.error("Stream error:", err);
        }
      );

      // Mark as done streaming
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId ? { ...msg, isStreaming: false } : msg
        )
      );
    } catch (err) {
      setError(err.message);
      console.error("Query error:", err);

      // Remove assistant message on error
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
      handleSendMessage();
    }
  };

  return (
    <main className="flex-1 flex flex-col bg-[#0b0b12]">
      {/* Top Bar */}
      <div className="h-[72px] border-b border-white/10 px-8 flex items-center justify-between bg-[#0d0d16]">
        <div>
          <h2 className="font-semibold text-lg">AI Workspace</h2>
          <p className="text-sm text-white/40">
            {documents.length > 0
              ? `${documents.length} document${documents.length !== 1 ? "s" : ""} loaded`
              : "Upload documents to start chatting"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-2 text-sm transition">
            Export Chat
          </button>

          <div className="w-10 h-10 rounded-full bg-violet-600 flex items-center justify-center font-medium">
            A
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-3xl rounded-2xl px-5 py-4 border ${
                message.role === "user"
                  ? "bg-violet-600 border-violet-500"
                  : "bg-white/[0.04] border-white/10"
              }`}
            >
              <p className="text-sm leading-relaxed text-white/90 whitespace-pre-wrap">
                {message.text}
                {message.isStreaming && (
                  <span className="ml-1 inline-block w-2 h-4 bg-white/40 animate-pulse" />
                )}
              </p>

              {message.sources && message.sources.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {message.sources.map((source, i) => (
                    <div
                      key={i}
                      className="text-xs bg-violet-500/10 text-violet-300 border border-violet-500/20 rounded-lg px-3 py-1"
                    >
                      {typeof source === "string" ? source : source.name || source}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-white/10 p-6 bg-[#0d0d16]">
        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-4">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              documents.length === 0
                ? "Upload documents first..."
                : "Ask something about your documents... (Ctrl+Enter to send)"
            }
            disabled={loading || documents.length === 0}
            className="w-full bg-transparent outline-none resize-none text-sm text-white placeholder:text-white/30 disabled:opacity-50 disabled:cursor-not-allowed min-h-[80px]"
          />

          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs text-white/30">
              <span>RAG Enabled</span>
              <span>•</span>
              <span>Knowledge Graph Active</span>
            </div>

            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim() || documents.length === 0}
              className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition px-5 py-2 rounded-xl text-sm font-medium flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              {loading ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
