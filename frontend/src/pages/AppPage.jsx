import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import DocumentSidebar from "../components/DocumentSidebar";
import ChatPanel from "../components/ChatPanel";
import GraphViewer from "../components/GraphViewer";
import { getDocuments, logoutUser } from "../api/client";
import { LogOut } from "lucide-react";

export default function AppPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [refreshChats, setRefreshChats] = useState(0);
  const [pendingQuery, setPendingQuery] = useState(null);

  // Fetch documents when session changes
  useEffect(() => {
    loadDocuments();
  }, [sessionId]);

  // Poll for document status if any are pending
  useEffect(() => {
    const hasPendingDocs = documents.some((d) => !d.kg_ready || d.status !== "ready");
    if (hasPendingDocs && sessionId) {
      const interval = setInterval(() => {
        loadDocuments();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [documents, sessionId]);

  async function loadDocuments() {
    if (!sessionId) {
      setDocuments([]);
      return;
    }
    try {
      const docs = await getDocuments(sessionId);
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  }

  async function handleLogout() {
    try {
      await logoutUser();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      logout();
      navigate("/login");
    }
  }

  return (
    <div className="h-screen bg-[#0b0b12] text-white flex overflow-hidden">
      {/* Left Sidebar - Documents */}
      <DocumentSidebar 
        sessionId={sessionId}
        onSessionSelect={setSessionId}
        refreshTrigger={refreshChats}
        documents={documents}
        onDocumentsChange={loadDocuments}
      />

      {/* Center - Chat */}
      <ChatPanel 
        documents={documents} 
        sessionId={sessionId}
        onSessionChange={(id) => {
          setSessionId(id);
          setRefreshChats(prev => prev + 1);
        }}
        pendingQuery={pendingQuery}
        clearPendingQuery={() => setPendingQuery(null)}
      />

      {/* Right Panel - Knowledge Graph */}
      <GraphViewer 
        documents={documents} 
        onNodeClick={(entity) => setPendingQuery(`explain more '${entity}'`)}
      />

      {/* Logout Button (floating) */}
      <button
        onClick={handleLogout}
        className="fixed bottom-6 right-6 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 rounded-full p-3 transition text-red-300"
        title="Logout"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </div>
  );
}
