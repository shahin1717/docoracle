import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { registerUser } from "../api/client";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const validate = () => {
    const e = {};
    if (!form.name) e.name = "Name is required";
    if (!form.email) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = "Invalid email address";
    if (!form.password) e.password = "Password is required";
    else if (form.password.length < 8) e.password = "Password must be at least 8 characters";
    if (!form.confirmPassword) e.confirmPassword = "Please confirm your password";
    else if (form.password !== form.confirmPassword) e.confirmPassword = "Passwords do not match";
    return e;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const v = validate();
    if (Object.keys(v).length > 0) {
      setErrors(v);
      return;
    }
    setLoading(true);
    setErrors({});
    try {
      await registerUser(form.name, form.email, form.password);
      navigate("/login");
    } catch (err) {
      setErrors({ api: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] px-4">
      <div className="w-full max-w-md bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur">
        <h1 className="text-3xl font-bold text-white mb-2 text-center">
          Create Account
        </h1>
        <p className="text-center text-white/40 text-sm mb-6">
          Join DocOracle today
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-xs text-white/60">Full Name</label>
            <input
              className="w-full mt-1 p-3 rounded-lg bg-white/5 border border-white/10 text-white outline-none focus:border-violet-500"
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="John Doe"
            />
            {errors.name && (
              <p className="text-red-400 text-xs mt-1">{errors.name}</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="text-xs text-white/60">Email</label>
            <input
              className="w-full mt-1 p-3 rounded-lg bg-white/5 border border-white/10 text-white outline-none focus:border-violet-500"
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@gmail.com"
            />
            {errors.email && (
              <p className="text-red-400 text-xs mt-1">{errors.email}</p>
            )}
          </div>

          {/* Password */}
          <div>
            <label className="text-xs text-white/60">Password</label>
            <input
              className="w-full mt-1 p-3 rounded-lg bg-white/5 border border-white/10 text-white outline-none focus:border-violet-500"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="••••••••"
            />
            {errors.password && (
              <p className="text-red-400 text-xs mt-1">{errors.password}</p>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label className="text-xs text-white/60">Confirm Password</label>
            <input
              className="w-full mt-1 p-3 rounded-lg bg-white/5 border border-white/10 text-white outline-none focus:border-violet-500"
              type="password"
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              placeholder="••••••••"
            />
            {errors.confirmPassword && (
              <p className="text-red-400 text-xs mt-1">{errors.confirmPassword}</p>
            )}
          </div>

          {/* API error */}
          {errors.api && (
            <p className="text-red-400 text-xs">{errors.api}</p>
          )}

          {/* Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-violet-600 hover:bg-violet-700 text-white py-3 rounded-lg font-medium transition"
          >
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="text-center text-xs text-white/40 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-violet-400 hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}