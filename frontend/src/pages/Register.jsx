import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { registerUser, loginUser } from "../api/client";
import { AlertCircle, Eye, EyeOff, CheckCircle } from "lucide-react";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Password validation
  const passwordStrength = {
    hasMinLength: password.length >= 8,
    hasUpperCase: /[A-Z]/.test(password),
    hasLowerCase: /[a-z]/.test(password),
    hasNumbers: /\d/.test(password),
  };

  const isPasswordStrong =
    Object.values(passwordStrength).filter(Boolean).length >= 3;

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setLoading(true);

    try {
      // Validate inputs
      if (!name || !email || !password || !confirmPassword) {
        throw new Error("Please fill in all fields");
      }

      if (name.trim().length < 2) {
        throw new Error("Name must be at least 2 characters");
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        throw new Error("Please enter a valid email");
      }

      if (password.length < 8) {
        throw new Error("Password must be at least 8 characters");
      }

      if (password !== confirmPassword) {
        throw new Error("Passwords do not match");
      }

      if (!isPasswordStrong) {
        throw new Error(
          "Password must contain uppercase, lowercase, and numbers"
        );
      }

      // Register
      await registerUser(name, email, password);
      setSuccess(true);

      // Auto-login after successful registration
      setTimeout(async () => {
      try {
        // Входим по 'name', так как именно оно стало 'username' в базе
        const data = await loginUser(name, password); 
        login(data.access_token || data.token || data);
        navigate("/app");
      } catch (err) {
        navigate("/login");
      }
    }, 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0b0b12] via-[#1a1a2e] to-[#0b0b12] flex flex-col items-center justify-center px-4">
        <div className="relative z-10 text-center max-w-md">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/20 border border-green-500/30 mb-6 animate-bounce">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">
            Account Created!
          </h2>
          <p className="text-white/60 mb-4">
            Welcome to DocOracle. Redirecting you to the workspace...
          </p>

          <div className="inline-block">
            <div className="animate-spin">
              <div className="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full" />
            </div>
          </div>
        </div>
      </div>
    );
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
          <h2 className="text-2xl font-bold text-white mb-2">Create Account</h2>
          <p className="text-sm text-white/60 mb-6">
            Join DocOracle to start using AI-powered document analysis
          </p>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleRegister} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition"
                disabled={loading}
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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

              {/* Password Strength Indicator */}
              {password && (
                <div className="mt-3 space-y-2">
                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        passwordStrength.hasMinLength
                          ? "bg-green-500"
                          : "bg-white/20"
                      }`}
                    />
                    <span className="text-white/60">At least 8 characters</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        passwordStrength.hasUpperCase
                          ? "bg-green-500"
                          : "bg-white/20"
                      }`}
                    />
                    <span className="text-white/60">Uppercase letter</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        passwordStrength.hasLowerCase
                          ? "bg-green-500"
                          : "bg-white/20"
                      }`}
                    />
                    <span className="text-white/60">Lowercase letter</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        passwordStrength.hasNumbers
                          ? "bg-green-500"
                          : "bg-white/20"
                      }`}
                    />
                    <span className="text-white/60">Number</span>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-white/80 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition"
                >
                  {showConfirmPassword ? (
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
              disabled={loading || !isPasswordStrong}
              className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium py-3 rounded-xl text-white mt-6"
            >
              {loading ? "Creating Account..." : "Create Account"}
            </button>
          </form>

          {/* Sign In Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-white/60">
              Already have an account?{" "}
              <Link
                to="/login"
                className="text-violet-400 hover:text-violet-300 font-medium transition"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-white/30 mt-6">
          By creating an account, you agree to our Terms of Service
        </p>
      </div>
    </div>
  );
}
