import { useState, useRef, useEffect } from "react";
import { streamQuery, getChatSession } from "../api/client";
import { Send, AlertCircle, Loader2, Network } from "lucide-react";

export default function ChatPanel({ documents = [], sessionId, onSessionChange, pendingQuery, clearPendingQuery, onOpenGraph }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: "Welcome to DocOracle. Upload documents and select them to start chatting.",
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

  // Handle pending query from graph
  useEffect(() => {
    if (pendingQuery && !loading) {
      handleSendMessage(pendingQuery);
      clearPendingQuery();
    }
  }, [pendingQuery, loading]);

  // Load session when sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadSession();
    } else {
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          text: "Welcome to DocOracle. Upload documents to this chat to begin.",
          sources: [],
          isStreaming: false,
        },
      ]);
    }
  }, [sessionId]);

  async function loadSession() {
    try {
      setLoading(true);
      setError(null);
      const session = await getChatSession(sessionId);

      const formattedMessages = session.messages.map((m) => ({
        id: m.id,
        role: m.role,
        text: m.content,
        sources: [], // we don't persist sources in DB yet
        isStreaming: false,
      }));
      if (formattedMessages.length > 0) {
        setMessages(formattedMessages);
      } else {
        setMessages([
          {
            id: "welcome",
            role: "assistant",
            text: "Welcome to DocOracle. Upload documents to this chat to begin.",
            sources: [],
            isStreaming: false,
          },
        ]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load chat history.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage(overrideText = null) {
    const textToSend = typeof overrideText === "string" ? overrideText : input;
    if (!textToSend.trim() || loading) return;
    if (documents.length === 0) {
      setError("Please upload at least one document to chat with.");
      return;
    }

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      text: textToSend.trim(),
      sources: [],
      isStreaming: false,
    };

    const assistantId = (Date.now() + 1).toString();
    const assistantMessage = {
      id: assistantId,
      role: "assistant",
      text: "",
      sources: [],
      isStreaming: true,
    };

    // Remove welcome message if it's the first message
    setMessages((prev) => {
      const filtered = prev.filter((m) => m.id !== "welcome");
      return [...filtered, userMessage, assistantMessage];
    });

    const currentInput = textToSend.trim();
    if (typeof overrideText !== "string") {
      setInput("");
    }
    setLoading(true);
    setError(null);

    try {
      await streamQuery(
        currentInput,
        sessionId,
        (chunk) => {
          if (chunk.type === "session") {
            if (!sessionId && onSessionChange) {
              onSessionChange(chunk.content);
            }
            return;
          }

          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantId) return msg;

              if (chunk.type === "token") {
                return {
                  ...msg,
                  text: msg.text + (chunk.content || ""),
                };
              } else if (chunk.type === "sources") {
                return {
                  ...msg,
                  sources: Array.isArray(chunk.content) ? chunk.content : [],
                };
              } else if (chunk.type === "error") {
                setError(chunk.content);
                return { ...msg, isStreaming: false };
              } else if (chunk.type === "done") {
                return { ...msg, isStreaming: false };
              }

              return msg;
            })
          );
        },
        (err) => {
          console.error("Stream error:", err);
          setError(err.message || "Something went wrong while streaming response.");

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, isStreaming: false, text: msg.text + "\n\n[Error occurred]" }
                : msg
            )
          );
        }
      );
    } catch (err) {
      console.error("Query error:", err);
      setError(err.message || "Failed to get response from AI.");

      setMessages((prev) => prev.filter((msg) => msg.id !== assistantId));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <main className="flex-1 flex flex-col bg-[#0b0b12]">
      {/* Top Bar */}
      <div className="border-b border-white/10 px-8 py-4 flex items-start justify-between bg-[#0d0d16] min-h-[72px]">
        <div className="flex-1">
          <h2 className="font-semibold text-lg">AI Workspace</h2>
          
          <div className="mt-2">
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-white/40 py-1.5">Workspace Documents:</span>
              {documents.length === 0 ? (
                <span className="text-xs text-white/20 py-1.5">None</span>
              ) : (
                documents.map((doc) => (
                  <span
                    key={doc.id}
                    className="text-xs px-2.5 py-1.5 rounded-lg bg-white/[0.03] text-white/50 border border-white/5 truncate max-w-[200px]"
                  >
                    {doc.name}
                  </span>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-4">
          <button 
            onClick={onOpenGraph}
            className="bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-xl px-4 py-2 text-sm transition whitespace-nowrap flex items-center gap-2"
          >
            <Network className="w-4 h-4" />
            Knowledge Map
          </button>
          <button className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-2 text-sm transition whitespace-nowrap">
            Export Chat
          </button>
          <div className="w-10 h-10 rounded-full bg-violet-600 flex items-center justify-center font-medium flex-shrink-0">
            A
          </div>
        </div>
      </div>

      {/* Messages Area */}
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
                  <span className="inline-flex items-center gap-1 ml-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                  </span>
                )}
              </p>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-widest text-white/40 mb-2">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, i) => (
                      <div
                        key={i}
                        className="text-xs bg-violet-500/10 text-violet-300 border border-violet-500/20 rounded-lg px-3 py-1.5 max-w-xs truncate"
                        title={typeof source === "string" ? source : source.text?.slice(0, 100)}
                      >
                        {typeof source === "string"
                          ? source
                          : source.title || source.source_path || `Source ${i + 1}`}
                      </div>
                    ))}
                  </div>
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
                : "Ask a question about your documents... (Press Enter to send)"
            }
            disabled={loading || documents.length === 0}
            className="w-full bg-transparent outline-none resize-none text-sm text-white placeholder:text-white/30 disabled:opacity-50 min-h-[80px] max-h-[200px]"
            rows={3}
          />

          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs text-white/30">
              <span>RAG + Knowledge Graph</span>
            </div>

            <button
              onClick={handleSendMessage}
              disabled={loading || !input.trim() || documents.length === 0}
              className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Thinking...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}