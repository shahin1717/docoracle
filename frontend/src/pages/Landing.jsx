import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ArrowRight, Zap, BarChart3, Network } from "lucide-react";

export default function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    navigate("/app");
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0b0b12] via-[#1a1a2e] to-[#0b0b12]">
      {/* Background glow */}
      <div className="absolute inset-0 bg-gradient-to-t from-violet-600/10 via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10">
        {/* Navigation */}
        <nav className="border-b border-white/10 backdrop-blur-md sticky top-0">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center font-bold text-sm">
                D
              </div>
              <span className="font-bold text-white">DocOracle</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate("/login")}
                className="px-4 py-2 text-white/80 hover:text-white transition"
              >
                Sign In
              </button>
              <button
                onClick={() => navigate("/register")}
                className="px-6 py-2 bg-violet-600 hover:bg-violet-700 rounded-lg font-medium text-white transition"
              >
                Get Started
              </button>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="max-w-6xl mx-auto px-6 py-32 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
            Chat with Your
            <br />
            <span className="bg-gradient-to-r from-violet-400 via-violet-500 to-violet-600 bg-clip-text text-transparent">
              Documents
            </span>
          </h1>

          <p className="text-lg text-white/60 max-w-2xl mx-auto mb-8">
            DocOracle uses advanced AI to extract knowledge from your documents.
            Upload PDFs, Word docs, and presentations. Get instant answers with
            citations.
          </p>

          <div className="flex gap-4 justify-center mb-16">
            <button
              onClick={() => navigate("/register")}
              className="px-8 py-3 bg-violet-600 hover:bg-violet-700 rounded-lg font-medium text-white flex items-center gap-2 transition"
            >
              Start Free <ArrowRight className="w-4 h-4" />
            </button>
            <button className="px-8 py-3 border border-white/20 hover:border-white/40 rounded-lg font-medium text-white transition">
              Learn More
            </button>
          </div>

          {/* Feature Preview */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-2 backdrop-blur-sm">
            <div className="bg-gradient-to-br from-violet-600/20 to-transparent rounded-xl p-12 flex items-center justify-center min-h-[400px] text-white/30">
              <p className="text-center">DocOracle Interface Preview</p>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="max-w-6xl mx-auto px-6 py-24">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            Powerful Features
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:border-violet-500/30 transition">
              <div className="w-12 h-12 bg-violet-500/20 rounded-lg flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                RAG-Powered
              </h3>
              <p className="text-white/60">
                Retrieval-Augmented Generation ensures answers are grounded in
                your actual documents.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:border-violet-500/30 transition">
              <div className="w-12 h-12 bg-violet-500/20 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                Knowledge Extraction
              </h3>
              <p className="text-white/60">
                Automatically extract entities, relationships, and insights from
                your documents.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:border-violet-500/30 transition">
              <div className="w-12 h-12 bg-violet-500/20 rounded-lg flex items-center justify-center mb-4">
                <Network className="w-6 h-6 text-violet-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                Knowledge Graphs
              </h3>
              <p className="text-white/60">
                Visualize relationships between concepts and entities across your
                documents.
              </p>
            </div>
          </div>
        </section>

        {/* Supported Formats */}
        <section className="max-w-6xl mx-auto px-6 py-16 text-center">
          <h3 className="text-lg font-semibold text-white/80 mb-6">
            Supported File Types
          </h3>
          <div className="flex flex-wrap gap-4 justify-center">
            {["PDF", "Word (.docx)", "PowerPoint", "Markdown"].map((fmt) => (
              <div
                key={fmt}
                className="px-4 py-2 bg-white/5 border border-white/10 rounded-full text-sm text-white/70"
              >
                {fmt}
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="max-w-4xl mx-auto px-6 py-24 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to supercharge your research?
          </h2>
          <p className="text-white/60 mb-8">
            Join thousands of users leveraging AI to extract knowledge from their
            documents.
          </p>
          <button
            onClick={() => navigate("/register")}
            className="px-8 py-4 bg-violet-600 hover:bg-violet-700 rounded-lg font-medium text-white text-lg transition"
          >
            Get Started Free
          </button>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 py-8 text-center text-white/40 text-sm">
          <p>© 2024 DocOracle. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
}
