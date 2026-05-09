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

  // Fetch documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const docs = await getDocuments();
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
      <DocumentSidebar />

      {/* Center - Chat */}
      <ChatPanel documents={documents} />

      {/* Right Panel - Knowledge Graph */}
      <GraphViewer documents={documents} />

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
