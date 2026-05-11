import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/client";
import { User, Mail, Calendar, Shield, ChevronLeft, Loader2 } from "lucide-react";

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const data = await getCurrentUser();
        setUser(data);
      } catch (err) {
        setError("Failed to load profile.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="h-screen bg-[#0b0b12] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b0b12] text-white flex flex-col items-center py-12 px-6">
      <div className="w-full max-w-2xl">
        <button 
          onClick={() => navigate("/app")}
          className="flex items-center gap-2 text-white/40 hover:text-white transition mb-8 group"
        >
          <ChevronLeft className="w-5 h-5 transition group-hover:-translate-x-1" />
          Back to Workspace
        </button>

        <div className="bg-[#0d0d16] border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
          <div className="bg-gradient-to-r from-violet-600 to-indigo-600 h-32 relative">
            <div className="absolute -bottom-12 left-8">
              <div className="w-24 h-24 rounded-2xl bg-violet-500 border-4 border-[#0d0d16] flex items-center justify-center text-3xl font-bold shadow-xl">
                {user?.username?.[0]?.toUpperCase() || "U"}
              </div>
            </div>
          </div>

          <div className="pt-16 pb-8 px-8">
            <div className="flex justify-between items-start mb-8">
              <div>
                <h1 className="text-2xl font-bold mb-1">{user?.username}</h1>
                <p className="text-white/40 text-sm">Personal Account</p>
              </div>
              <div className="px-3 py-1 bg-violet-500/10 border border-violet-500/20 rounded-full text-violet-400 text-xs font-semibold uppercase tracking-wider">
                {user?.is_active ? "Active" : "Inactive"}
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <div className="flex items-center gap-3 text-white/40 mb-2">
                  <Mail className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-semibold">Email Address</span>
                </div>
                <p className="text-white/90">{user?.email}</p>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <div className="flex items-center gap-3 text-white/40 mb-2">
                  <Calendar className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-semibold">Joined Date</span>
                </div>
                <p className="text-white/90">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString("en-US", {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  }) : "N/A"}
                </p>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <div className="flex items-center gap-3 text-white/40 mb-2">
                  <Shield className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-semibold">Account Role</span>
                </div>
                <p className="text-white/90">Standard User</p>
              </div>

              <div className="p-4 bg-white/5 border border-white/10 rounded-2xl">
                <div className="flex items-center gap-3 text-white/40 mb-2">
                  <User className="w-4 h-4" />
                  <span className="text-xs uppercase tracking-wider font-semibold">Default Model</span>
                </div>
                <p className="text-white/90">{user?.preferred_model || "System Default"}</p>
              </div>
            </div>

            <div className="mt-8 pt-8 border-t border-white/5">
              <p className="text-xs text-white/20 text-center italic">
                DocOracle Professional v1.0.0
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
