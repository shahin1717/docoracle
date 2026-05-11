import { useEffect } from "react"; 
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ArrowRight, Zap, BarChart3, Network, ChevronDown } from "lucide-react";

export default function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/app");
    }
  }, [isAuthenticated, navigate]);

  if (isAuthenticated) return null;

  const scrollToFeatures = () => {
    document.getElementById("features").scrollIntoView({
      behavior: "smooth",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0b0b12] via-[#1a1a2e] to-[#0b0b12] overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 bg-gradient-to-t from-violet-600/10 via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10">
        {/* Navigation */}
        <nav className="border-b border-white/10 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-violet-600 flex items-center justify-center font-bold text-sm shadow-lg shadow-violet-500/50">
                D
              </div>
              <span className="font-bold text-xl text-white">DocOracle</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate("/login")}
                className="px-5 py-2 text-white/80 hover:text-white transition font-medium"
              >
                Sign In
              </button>
              <button
                onClick={() => navigate("/register")}
                className="px-6 py-2 bg-violet-600 hover:bg-violet-700 rounded-xl font-medium text-white transition shadow-lg shadow-violet-500/30"
              >
                Get Started
              </button>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white leading-tight mb-6">
            Chat with Your<br />
            <span className="bg-gradient-to-r from-violet-400 via-violet-500 to-fuchsia-500 bg-clip-text text-transparent">
              Documents
            </span>
          </h1>

          <p className="text-xl text-white/70 max-w-2xl mx-auto mb-10">
            Upload PDFs, Word docs, presentations, and Markdown. 
            Get intelligent answers powered by local AI with citations and knowledge graphs.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <button
              onClick={() => navigate("/register")}
              className="px-8 py-4 bg-violet-600 hover:bg-violet-700 rounded-2xl font-semibold text-lg flex items-center justify-center gap-3 transition group"
            >
              Start Free 
              <ArrowRight className="group-hover:translate-x-1 transition" />
            </button>

            <button
              onClick={scrollToFeatures}
              className="px-8 py-4 border border-white/30 hover:border-white/60 rounded-2xl font-medium text-lg flex items-center justify-center gap-2 transition"
            >
              Learn More
            </button>
          </div>

          {/* Preview */}
          <div className="bg-white/5 border border-white/10 rounded-3xl p-3 backdrop-blur-xl shadow-2xl transition-all duration-700 hover:shadow-violet-500/20 hover:border-violet-500/30 group relative overflow-hidden mt-8">
            <div className="absolute inset-0 bg-gradient-to-tr from-violet-600/10 via-transparent to-fuchsia-600/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
            <img 
              src="/preview.png" 
              alt="DocOracle Interface Preview" 
              className="rounded-2xl w-full border border-white/10 group-hover:scale-[1.01] transition-transform duration-700"
            />
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="max-w-6xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              Powerful Features
            </h2>
            <p className="text-white/60 text-lg">
              Built for researchers, students, and professionals
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="group bg-white/5 border border-white/10 hover:border-violet-500/40 rounded-3xl p-8 transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 bg-violet-500/10 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition">
                <Zap className="w-7 h-7 text-violet-400" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-3">RAG-Powered Chat</h3>
              <p className="text-white/70">
                Answers are always grounded in your documents with accurate citations.
              </p>
            </div>

            <div className="group bg-white/5 border border-white/10 hover:border-violet-500/40 rounded-3xl p-8 transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 bg-violet-500/10 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition">
                <BarChart3 className="w-7 h-7 text-violet-400" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-3">Knowledge Extraction</h3>
              <p className="text-white/70">
                Automatically detects entities, concepts, and relationships from your files.
              </p>
            </div>

            <div className="group bg-white/5 border border-white/10 hover:border-violet-500/40 rounded-3xl p-8 transition-all duration-300 hover:-translate-y-1">
              <div className="w-14 h-14 bg-violet-500/10 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition">
                <Network className="w-7 h-7 text-violet-400" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-3">Interactive Knowledge Graph</h3>
              <p className="text-white/70">
                Visualize connections between ideas across all your documents.
              </p>
            </div>
          </div>
        </section>

        {/* Supported Formats */}
        <section className="max-w-6xl mx-auto px-6 py-20 text-center border-t border-white/10">
          <h3 className="text-lg font-semibold text-white/80 mb-8">
            Supported File Formats
          </h3>
          <div className="flex flex-wrap gap-4 justify-center">
            {["PDF", "DOCX", "PPTX", "Markdown (.md)", "TXT"].map((fmt) => (
              <div
                key={fmt}
                className="px-6 py-3 bg-white/5 border border-white/10 rounded-2xl text-white/80 hover:bg-white/10 transition"
              >
                {fmt}
              </div>
            ))}
          </div>
        </section>

        {/* Final CTA */}
        <section className="max-w-4xl mx-auto px-6 py-28 text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to unlock your documents?
          </h2>
          <p className="text-white/60 mb-10 text-lg">
            Run everything locally. No data leaves your machine.
          </p>
          <button
            onClick={() => navigate("/register")}
            className="px-10 py-5 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:brightness-110 rounded-2xl font-semibold text-xl transition shadow-xl shadow-violet-500/30"
          >
            Get Started Free
          </button>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 py-10 text-center text-white/40 text-sm">
          <p>© 2026 DocOracle. Built with ❤️ for local AI.</p>
        </footer>
      </div>
    </div>
  );
}