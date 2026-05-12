import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Send, AlertCircle, Loader2, Network, ChevronDown, Download, Check, Trash2, LogOut, Settings, User, X, Save, Mail, Key, Square, StickyNote } from "lucide-react";
import { getModels, setPreferredModel, pullModelStream, deleteModel, streamQuery, getChatSession, getCurrentUser, logoutUser, updateCurrentUser, deleteCurrentUser, deleteAllHistory, updateChatSessionNotes } from "../api/client";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

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

  const [modelData, setModelData] = useState({ models: [], current: "", catalog: [] });
  const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
  const [pullProgress, setPullProgress] = useState(null);
  const abortControllerRef = useRef(null);

  const [user, setUser] = useState(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isNotesOpen, setIsNotesOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [formData, setFormData] = useState({ username: "", email: "", password: "" });
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    loadModels();
    loadUser();
  }, []);

  async function loadUser() {
    try {
      const data = await getCurrentUser();
      setUser(data);
      setFormData({ username: data.username || "", email: data.email || "", password: "" });
    } catch (err) {
      console.error("Failed to load user:", err);
    }
  }

  async function handleLogout() {
    try {
      await logoutUser();
    } catch (err) {
      console.error(err);
    } finally {
      logout();
      navigate("/login");
    }
  }

  const handleSaveSettings = async () => {
    setIsSaving(true);
    setError(null);
    try {
      // Filter out empty password so Pydantic validation doesn't fail
      const updateData = { ...formData };
      if (!updateData.password) {
        delete updateData.password;
      }
      
      const updatedUser = await updateCurrentUser(updateData);
      setUser(updatedUser);
      setIsSettingsOpen(false);
      setFormData(prev => ({ ...prev, password: "" }));
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to update profile.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteProfile = async () => {
    if (!window.confirm("CRITICAL: This will permanently delete your account and ALL your data. This cannot be undone. Are you absolutely sure?")) {
      return;
    }
    
    setIsSaving(true);
    try {
      await deleteCurrentUser();
      logout();
      navigate("/login");
    } catch (err) {
      setError(err.message || "Failed to delete account.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Delete all chats and uploaded documents? This will reset your workspace.")) {
      return;
    }
    
    try {
      await deleteAllHistory();
      // Reload the session to show empty state
      if (sessionId) {
        onSessionChange(null);
      } else {
        setMessages([
          {
            id: "welcome",
            role: "assistant",
            text: "History cleared. Welcome to DocOracle. Upload documents to this chat to begin.",
            sources: [],
            isStreaming: false,
          },
        ]);
      }
      window.location.reload(); // Hard refresh to clear all states properly
    } catch (err) {
      console.error(err);
      setError("Failed to clear history.");
    }
  };

  const handleSaveNotes = async (newNotes) => {
    setNotes(newNotes);
    if (!sessionId) return;
    
    setIsSavingNotes(true);
    try {
      await updateChatSessionNotes(sessionId, newNotes);
    } catch (err) {
      console.error("Failed to save notes:", err);
    } finally {
      setIsSavingNotes(false);
    }
  };

  const handleOpenSource = (index, messageSources) => {
    const sources = messageSources || [];
    if (index >= 0 && index < sources.length) {
      setSelectedSource(sources[index]);
      setIsSourceModalOpen(true);
    }
  };

  async function loadModels() {
    try {
      const data = await getModels();
      setModelData(data);
    } catch (err) {
      console.error("Failed to load models:", err);
    }
  }

  async function handleModelSelect(modelId) {
    setIsModelDropdownOpen(false);
    
    if (modelData.models.includes(modelId)) {
      try {
        await setPreferredModel(modelId);
        setModelData(prev => ({ ...prev, current: modelId }));
      } catch (err) {
        setError("Failed to set model.");
      }
    } else {
      setPullProgress({ model: modelId, percent: 0 });
      try {
        await pullModelStream(modelId, (chunk) => {
          if (chunk.total && chunk.completed) {
            const p = Math.round((chunk.completed / chunk.total) * 100);
            setPullProgress({ model: modelId, percent: p });
          } else if (chunk.status === "success") {
            setPullProgress({ model: modelId, percent: 100 });
          }
        }, (err) => {
          setError("Failed to pull model: " + err.message);
          setPullProgress(null);
        });
        
        await setPreferredModel(modelId);
        await loadModels();
      } catch (err) {
        setError("Failed to pull model.");
      } finally {
        setPullProgress(null);
      }
    }
  }

  async function handleDeleteModel(modelId, e) {
    e.stopPropagation();
    try {
      await deleteModel(modelId);
      await loadModels();
    } catch (err) {
      setError("Failed to delete model: " + err.message);
    }
  }

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
      setNotes(session.notes || "");

      const formattedMessages = session.messages.map((m) => ({
        id: m.id,
        role: m.role,
        text: m.text || "",
        sources: m.sources || [],
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

  // Cleanup/Stop generation when switching sessions or unmounting
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        console.log("Stopping generation due to session change/unmount");
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [sessionId]);

  function handleStopGeneration() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.isStreaming ? { ...msg, isStreaming: false, text: msg.text + " [Interrupted]" } : msg
        )
      );
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

    // Create new abort controller
    const controller = new AbortController();
    abortControllerRef.current = controller;

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
                const newText = msg.text + (chunk.content || "");
                console.log("AI Token:", chunk.content);
                return {
                  ...msg,
                  text: newText,
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
          if (err.name === "AbortError") {
            console.log("Generation aborted by user");
            return;
          }
          console.error("Stream error:", err),
          setError(err.message || "Something went wrong while streaming response.");

          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, isStreaming: false, text: msg.text + "\n\n[Error occurred]" }
                : msg
            )
          );
        },
        controller.signal
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

  const handleExportChat = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(messages, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `chat_export_${sessionId || 'new'}_${new Date().toISOString().slice(0,10)}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  return (
    <main className="flex-1 flex flex-col bg-[#0b0b12]">
      {/* Top Bar */}
      <div className="border-b border-white/10 px-8 py-4 flex items-start justify-between bg-[#0d0d16] min-h-[72px]">
        <div className="flex-1">
          <h2 className="font-semibold text-lg">AI Workspace</h2>
          
        </div>

        <div className="flex items-center gap-3 ml-4">
          <button 
            onClick={() => setIsNotesOpen(true)}
            disabled={!sessionId}
            className={`border border-white/10 rounded-xl px-4 py-2 text-sm transition whitespace-nowrap flex items-center gap-2 ${sessionId ? 'bg-white/5 hover:bg-white/10 text-white/90' : 'opacity-30 cursor-not-allowed text-white/30'}`}
          >
            <StickyNote className="w-4 h-4 text-amber-400/80" />
            Notes
          </button>
          <button 
            onClick={onOpenGraph}
            className="bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-xl px-4 py-2 text-sm transition whitespace-nowrap flex items-center gap-2"
          >
            <Network className="w-4 h-4" />
            Knowledge Map
          </button>
          <button 
            onClick={handleExportChat}
            className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-2 text-sm transition whitespace-nowrap flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export Chat
          </button>
          
          <div className="relative">
            <button 
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="w-10 h-10 rounded-full bg-violet-600 hover:bg-violet-700 flex items-center justify-center font-medium flex-shrink-0 transition hover:scale-105"
            >
              {user?.username?.[0]?.toUpperCase() || "U"}
            </button>

            {isProfileOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-[#1a1a24] border border-white/10 rounded-xl shadow-xl overflow-hidden z-50">
                <div className="p-3 border-b border-white/10">
                  <p className="text-sm font-medium text-white truncate">{user?.username || "User"}</p>
                  <p className="text-xs text-white/50 truncate">{user?.email || "user@example.com"}</p>
                </div>
                <div className="p-1">
                  <button
                    onClick={() => {
                      setIsProfileOpen(false);
                      setIsSettingsOpen(true);
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white rounded-lg flex items-center gap-2 transition"
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <button
                    onClick={handleClearHistory}
                    className="w-full text-left px-3 py-2 text-sm text-white/60 hover:bg-white/5 hover:text-white rounded-lg flex items-center gap-2 transition mt-1"
                  >
                    <Trash2 className="w-4 h-4 opacity-50" />
                    Clear History
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg flex items-center gap-2 transition mt-1"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Notes Modal */}
      {isNotesOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1a24] border border-white/10 rounded-2xl w-full max-w-2xl h-[600px] shadow-2xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-white/10">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <StickyNote className="w-5 h-5 text-amber-400" />
                Session Notes
              </h3>
              <div className="flex items-center gap-4">
                {isSavingNotes && (
                  <span className="text-xs text-white/40 flex items-center gap-1.5 animate-pulse">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Autosaving...
                  </span>
                )}
                <button 
                  onClick={() => setIsNotesOpen(false)}
                  className="text-white/40 hover:text-white transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="flex-1 p-6">
              <textarea
                value={notes}
                onChange={(e) => handleSaveNotes(e.target.value)}
                placeholder="Write down your key findings, thoughts, or reminders for this session..."
                className="w-full h-full bg-transparent text-white/90 placeholder:text-white/20 outline-none resize-none text-base leading-relaxed"
                autoFocus
              />
            </div>
            <div className="p-4 bg-black/20 border-t border-white/10 flex justify-between items-center text-xs text-white/40">
              <span>Your notes are automatically saved to this chat session.</span>
              <button 
                onClick={() => setIsNotesOpen(false)}
                className="text-violet-400 hover:text-violet-300 font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1a24] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-white/10">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <Settings className="w-5 h-5 text-violet-400" />
                Profile Settings
              </h3>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                className="text-white/40 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                  <User className="w-3.5 h-3.5" />
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-violet-500/50 text-white transition"
                  placeholder="Username"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5" />
                  Email Address
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-violet-500/50 text-white transition"
                  placeholder="Email"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                  <Key className="w-3.5 h-3.5" />
                  New Password
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2.5 outline-none focus:border-violet-500/50 text-white transition placeholder:text-white/20"
                  placeholder="Leave blank to keep current"
                />
              </div>
            </div>
            <div className="p-5 border-t border-white/10 flex justify-between items-center bg-black/20">
              <button
                onClick={handleDeleteProfile}
                disabled={isSaving}
                className="text-xs font-medium text-red-500/60 hover:text-red-400 transition underline underline-offset-4"
              >
                Delete Profile
              </button>
              <div className="flex gap-3">
                <button 
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-white/60 hover:text-white hover:bg-white/5 transition"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleSaveSettings}
                  disabled={isSaving}
                  className="px-5 py-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 rounded-xl text-sm font-medium transition flex items-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
              <div className="text-sm leading-relaxed text-white/90 prose prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={{
                    a: ({ href, children }) => {
                      if (href?.startsWith("#source-")) {
                        const index = parseInt(href.replace("#source-", ""));
                        return (
                          <button 
                            onClick={() => handleOpenSource(index - 1, message.sources)}
                            className="inline-flex items-center justify-center px-1.5 py-0.5 bg-sky-500/20 hover:bg-sky-500/40 text-sky-400 rounded text-[10px] font-bold transition-colors align-top mx-0.5"
                            title="View Source"
                          >
                            {children}
                          </button>
                        );
                      }
                      return <a href={href} target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">{children}</a>;
                    }
                  }}
                >
                  {(message.text || "").replace(/\[([\d,\s]+)\]/g, (match, p1) => {
                    const nums = p1.split(",").map(n => n.trim());
                    return nums.map(n => `[${n}](#source-${n})`).join("");
                  })}
                </ReactMarkdown>
                {message.isStreaming && (
                  <span className="inline-flex items-center gap-1 ml-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                  </span>
                )}
              </div>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-widest text-white/40 mb-2">Sources</p>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, i) => (
                      <div
                        key={i}
                        className="text-xs bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border border-sky-500/20 rounded-lg px-3 py-1.5 max-w-xs truncate transition-colors cursor-pointer"
                        title={typeof source === "string" ? source : source.text?.slice(0, 100)}
                        onClick={() => handleOpenSource(i, message.sources)}
                      >
                        <span className="opacity-50 mr-1">[{i + 1}]</span>
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

            <div className="flex items-center gap-3">
              {loading && (
                <button
                  onClick={handleStopGeneration}
                  className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 rounded-xl px-4 py-2.5 text-sm transition flex items-center gap-2"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  Stop
                </button>
              )}

              <div className="relative">
                <button
                  onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                  className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-2.5 text-sm transition flex items-center gap-2"
                >
                  <span className="text-white/80 max-w-[150px] truncate">
                    {pullProgress ? `Downloading... ${pullProgress.percent}%` : (modelData.current || "Loading...")}
                  </span>
                  <ChevronDown className="w-4 h-4 text-white/50" />
                </button>

                {isModelDropdownOpen && (
                  <div className="absolute bottom-full mb-2 right-0 w-80 bg-[#1a1a24] border border-white/10 rounded-xl shadow-xl overflow-hidden z-50">
                    <div className="max-h-80 overflow-y-auto p-2">
                      <div className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2 px-2 pt-1">Available Models</div>
                      {modelData.catalog.map((m) => {
                        const isDownloaded = modelData.models.includes(m.id);
                        const isCurrent = modelData.current === m.id;
                        const isRecommended = modelData.recommended === m.id;
                        return (
                          <button
                            key={m.id}
                            onClick={() => handleModelSelect(m.id)}
                            disabled={pullProgress !== null}
                            className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center justify-between group transition ${isCurrent ? "bg-violet-600/20 text-violet-300" : "hover:bg-white/5 text-white/80"}`}
                          >
                            <div className="flex flex-col overflow-hidden mr-3">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium truncate">{m.id}</span>
                                {isRecommended && (
                                  <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded font-semibold whitespace-nowrap">⭐ Recommended</span>
                                )}
                              </div>
                              <span className="text-xs text-white/40 truncate mt-0.5">{m.desc}</span>
                            </div>
                            <div className="flex-shrink-0 flex items-center">
                              {isCurrent ? (
                                <Check className="w-4 h-4 text-violet-400" />
                              ) : isDownloaded ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/50 font-medium">Ready</span>
                                  <button 
                                    onClick={(e) => handleDeleteModel(m.id, e)}
                                    className="p-1 hover:bg-red-500/20 text-white/20 hover:text-red-400 rounded-md transition opacity-0 group-hover:opacity-100"
                                    title="Delete Model"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <Download className="w-4 h-4 text-white/30 group-hover:text-white/70 transition" />
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleSendMessage}
                disabled={loading || !input.trim() || documents.length === 0 || pullProgress !== null}
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
      </div>
      {/* Source Preview Modal */}
      {isSourceModalOpen && selectedSource && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[60] p-4 lg:p-10">
          <div className="bg-[#1a1a24] border border-white/10 rounded-2xl w-full max-w-6xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-white/10 bg-violet-600/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-violet-600/20 flex items-center justify-center text-violet-400">
                  <Network className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Source Verification</h3>
                  <p className="text-xs text-white/40">Verifying AI claims against original document</p>
                </div>
              </div>
              <button 
                onClick={() => setIsSourceModalOpen(false)}
                className="text-white/40 hover:text-white transition p-2 hover:bg-white/5 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div>
                <label className="text-[10px] font-bold text-sky-400 uppercase tracking-widest mb-2 block">Document Metadata</label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <p className="text-[10px] text-white/30 uppercase mb-1">File Name</p>
                    <p className="text-sm text-white/80 font-medium truncate">{selectedSource.filename || selectedSource.title || "Unknown File"}</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                    <p className="text-[10px] text-white/30 uppercase mb-1">Page Number</p>
                    <p className="text-sm text-white/80 font-medium">{selectedSource.page_num || "N/A"}</p>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold text-sky-400 uppercase tracking-widest mb-2 block">Original Text Snippet</label>
                <div className="bg-white/[0.03] border border-white/10 rounded-xl p-6 relative group">
                  <div className="absolute top-4 left-4 text-sky-500/10 pointer-events-none">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M14.017 21L14.017 18C14.017 16.8954 14.9124 16 16.017 16H19.017C19.5693 16 20.017 15.5523 20.017 15V9C20.017 8.44772 19.5693 8 19.017 8H16.017C14.9124 8 14.017 7.10457 14.017 6V3H20.017C21.1216 3 22.017 3.89543 22.017 5V15C22.017 18.3137 19.3307 21 16.017 21H14.017ZM2.017 21L2.017 18C2.017 16.8954 2.91243 16 4.017 16H7.017C7.56928 16 8.017 15.5523 8.017 15V9C8.017 8.44772 7.56928 8 7.017 8H4.017C2.91243 8 2.017 7.10457 2.017 6V3H8.017C9.12157 3 10.017 3.89543 10.017 5V15C10.017 18.3137 7.3307 21 4.017 21H2.017Z" /></svg>
                  </div>
                  <p className="text-white/90 text-base leading-relaxed italic relative z-10 whitespace-pre-wrap">
                    {selectedSource.text || selectedSource.content || "No text available for this source."}
                  </p>
                </div>
              </div>
            </div>

            <div className="p-5 bg-black/20 border-t border-white/10 flex justify-end">
              <button 
                onClick={() => setIsSourceModalOpen(false)}
                className="px-6 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-medium transition border border-white/10"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

    </main>
  );
}