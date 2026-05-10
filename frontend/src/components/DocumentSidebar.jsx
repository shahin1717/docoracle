import { useState, useEffect, useRef } from "react";
import { getDocuments, uploadDocument, deleteDocument, getChatSessions, deleteChatSession, createChatSession } from "../api/client";
import { FileText, Trash2, Upload, MessageSquare, Plus, Loader2 } from "lucide-react";

export default function DocumentSidebar({ sessionId, onSessionSelect, refreshTrigger, documents = [], onDocumentsChange }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("chats"); // "documents" or "chats"
  const fileInputRef = useRef(null);

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (refreshTrigger > 0) {
      fetchSessions();
    }
  }, [refreshTrigger]);

  async function fetchSessions() {
    setLoadingSessions(true);
    try {
      const data = await getChatSessions();
      setSessions(data);
    } catch (err) {
      console.error("Failed to fetch sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      if (!sessionId) {
        setError("Please create or select a chat first before uploading documents.");
        return;
      }
      await uploadDocument(file, sessionId);
      if (onDocumentsChange) onDocumentsChange();
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setError(err.message);
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDocument(docId) {
    if (!window.confirm("Are you sure you want to delete this document?")) {
      return;
    }

    try {
      await deleteDocument(docId);
      if (onDocumentsChange) onDocumentsChange();
    } catch (err) {
      setError(err.message);
      console.error("Delete failed:", err);
    }
  }

  async function handleDeleteSession(id, e) {
    e.stopPropagation();
    if (!window.confirm("Delete this chat?")) return;
    try {
      await deleteChatSession(id);
      setSessions(sessions.filter(s => s.id !== id));
      if (sessionId === id) onSessionSelect(null);
    } catch (err) {
      console.error("Delete session failed:", err);
    }
  }

  const getFileIcon = (filename) => {
    if (!filename) return <FileText className="w-6 h-6 text-gray-400" />;

    const ext = filename.split(".").pop()?.toLowerCase() || "";

    const iconClass = "w-6 h-6";

    switch (ext) {
      case "pdf":
        return <span className={`${iconClass} text-red-400`}>📄</span>;
      case "docx":
      case "doc":
        return <span className={`${iconClass} text-blue-400`}>📘</span>;
      case "pptx":
      case "ppt":
        return <span className={`${iconClass} text-orange-400`}>📊</span>;
      case "md":
      case "markdown":
        return <span className={`${iconClass} text-gray-400`}>#</span>;
      default:
        return <FileText className={`${iconClass} text-gray-400`} />;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return "Today";
    if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <aside className="w-[320px] border-r border-white/10 bg-[#11111b] flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/10 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center font-bold text-lg">
            D
          </div>
          <div>
            <h1 className="font-semibold text-lg">DocOracle</h1>
            <p className="text-xs text-white/40">Local AI Workspace</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/10">
        <button
          onClick={() => setActiveTab("chats")}
          className={`flex-1 py-3 text-sm font-medium transition ${
            activeTab === "chats"
              ? "text-violet-400 border-b-2 border-violet-500 bg-white/5"
              : "text-white/50 hover:bg-white/[0.02]"
          }`}
        >
          Chats
        </button>
        <button
          onClick={() => setActiveTab("documents")}
          className={`flex-1 py-3 text-sm font-medium transition ${
            activeTab === "documents"
              ? "text-violet-400 border-b-2 border-violet-500 bg-white/5"
              : "text-white/50 hover:bg-white/[0.02]"
          }`}
        >
          Documents
        </button>
      </div>

      {activeTab === "documents" && (
        <>
          {/* Upload Button */}
          <div className="p-5 border-b border-white/10">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 transition rounded-xl py-3 font-medium flex items-center justify-center gap-2"
            >
              <Upload className="w-4 h-4" />
              {uploading ? "Uploading..." : "+ Upload Document"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.docx,.doc,.pptx,.ppt,.md,.txt"
              className="hidden"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="mx-4 mt-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Documents List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-medium text-white/80">Your Documents</h2>
              <span className="text-xs text-white/30">{documents.length} files</span>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin">
                  <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full" />
                </div>
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-12 text-white/30">
                <p className="text-sm">No documents yet</p>
                <p className="text-xs">Upload one to get started</p>
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-white/[0.04] hover:bg-white/[0.07] transition border border-white/10 rounded-2xl p-4 cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="mt-1">{getFileIcon(doc.name)}</div>
                      <div className="flex-1">
                        <h3 className="font-medium text-sm mb-1 break-all line-clamp-2 group-hover:text-violet-300 transition flex items-center gap-2">
                          {doc.name || doc.filename}
                          {(!doc.kg_ready || doc.status !== "ready") && (
                            <Loader2 className="w-3 h-3 animate-spin text-violet-400" title="Processing document..." />
                          )}
                        </h3>
                        <p className="text-xs text-white/40">{doc.pages || "?"} pages</p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="opacity-0 group-hover:opacity-100 transition"
                    >
                      <Trash2 className="w-4 h-4 text-red-400 hover:text-red-300" />
                    </button>
                  </div>

                  <div className="mt-3 text-xs text-white/30">
                    {formatDate(doc.uploaded_at || new Date().toISOString())}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {activeTab === "chats" && (
        <>
          <div className="p-5 border-b border-white/10">
            <button
              onClick={async () => {
                try {
                  const newSession = await createChatSession();
                  onSessionSelect(newSession.id);
                  fetchSessions();
                } catch (err) {
                  console.error(err);
                }
              }}
              className="w-full bg-white/5 hover:bg-white/10 border border-white/10 transition rounded-xl py-3 font-medium flex items-center justify-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {loadingSessions ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full" />
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-12 text-white/30">
                <p className="text-sm">No chats yet</p>
                <p className="text-xs">Start a new conversation</p>
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => onSessionSelect(session.id)}
                  className={`group cursor-pointer rounded-xl p-3 transition flex items-center justify-between gap-2 ${
                    sessionId === session.id
                      ? "bg-violet-600/20 text-violet-300 border border-violet-500/30"
                      : "hover:bg-white/5 text-white/70 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <MessageSquare className="w-4 h-4 flex-shrink-0 opacity-50" />
                    <div className="truncate text-sm font-medium">
                      {session.title || "New Chat"}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 transition p-1 hover:bg-white/10 rounded"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-400" />
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </aside>
  );
}
