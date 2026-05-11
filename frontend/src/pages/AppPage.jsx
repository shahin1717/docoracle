import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import DocumentSidebar from "../components/DocumentSidebar";
import ChatPanel from "../components/ChatPanel";
import GraphViewer from "../components/GraphViewer";
import { getDocuments, logoutUser, triggerKgBuild } from "../api/client";
import { LogOut } from "lucide-react";

export default function AppPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [refreshChats, setRefreshChats] = useState(0);
  const [pendingQuery, setPendingQuery] = useState(null);
  const [showGraphModal, setShowGraphModal] = useState(false);

  // Fetch documents when session changes
  useEffect(() => {
    loadDocuments();
  }, [sessionId]);

  // Poll for document status if any are pending
  useEffect(() => {
    const hasPendingDocs = documents.some((d) => d.status !== "ready" || d.kg_status === "processing");
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
        onOpenGraph={async () => {
          // If NO documents in this session have a KG yet, trigger all of them
          const anyKgInProgress = documents.some(d => d.kg_ready || d.kg_status === "processing");
          
          if (!anyKgInProgress) {
            const unbuiltDocs = documents.filter(d => d.status === "ready" && !d.kg_ready && d.kg_status === "none");
            if (unbuiltDocs.length > 0) {
              await Promise.all(unbuiltDocs.map(d => 
                triggerKgBuild(d.id).catch(err => console.error("Auto-trigger KG failed:", err))
              ));
              await loadDocuments(); // Instant refresh so UI shows "Building..."
            }
          }
          setShowGraphModal(true);
        }}
      />

      {/* Graph Modal */}
      {showGraphModal && (
        <GraphViewer 
          documents={documents} 
          onNodeClick={(entity) => {
            setPendingQuery(`explain more '${entity}'`);
            setShowGraphModal(false);
          }}
          onClose={() => setShowGraphModal(false)}
        />
      )}

    </div>
  );
}
