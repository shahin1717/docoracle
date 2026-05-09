import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { loginUser } from "../api/client";
import { AlertCircle, Eye, EyeOff } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Validate inputs
      if (!username || !password) {
        throw new Error("Please fill in all fields");
      }

      // Call API
      const data = await loginUser(username, password);

      // Store token and redirect
      login(data.access_token || data.token || data);
      navigate("/app");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0b0b12] via-[#1a1a2e] to-[#0b0b12] flex flex-col items-center justify-center px-4">
      {/* Background glow */}
      <div className="absolute inset-0 bg-gradient-to-t from-violet-600/10 via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-600 to-violet-700 flex items-center justify-center font-bold text-xl text-white">
              D
            </div>
            <div className="text-left">
              <h1 className="font-bold text-2xl text-white">DocOracle</h1>
              <p className="text-xs text-white/40">Local AI Workspace</p>
            </div>
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white/5 border border-white/10 backdrop-blur-sm rounded-2xl p-8 shadow-2xl">
          <h2 className="text-2xl font-bold text-white mb-2">Welcome Back</h2>
          <p className="text-sm text-white/60 mb-6">
            Sign in to your DocOracle account
          </p>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                Email
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition"
                disabled={loading}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium py-3 rounded-xl text-white mt-6"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          {/* Sign Up Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-white/60">
              Don't have an account?{" "}
              <Link
                to="/register"
                className="text-violet-400 hover:text-violet-300 font-medium transition"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-white/30 mt-6">
          By signing in, you agree to our Terms of Service
        </p>
      </div>
    </div>
  );
}
