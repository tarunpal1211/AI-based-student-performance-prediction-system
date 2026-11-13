import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { apiClient } from "../api/client";
import {
  BrainCircuit, Lock, Mail, User, GraduationCap,
  BarChart3, Brain, ShieldCheck, Eye, EyeOff,
  UserCheck, Trash2, Sparkles,
} from "lucide-react";

interface SavedAccount {
  email: string;
  password?: string;
  fullName: string;
  role: string;
  savedAt: number;
}

const SAVED_ACCOUNTS_KEY = "gradematrix_saved_accounts";

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [registerRole, setRegisterRole] = useState<"teacher" | "admin">("teacher");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedAccounts, setSavedAccounts] = useState<SavedAccount[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Load saved accounts on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(SAVED_ACCOUNTS_KEY);
      if (stored) {
        const parsed: SavedAccount[] = JSON.parse(stored);
        setSavedAccounts(parsed);
      }
    } catch {
      // ignore parse error
    }
  }, []);

  // Filter saved accounts matching typed email for autocomplete popup
  const filteredAccounts = savedAccounts.filter((a) => {
    if (!email.trim()) return true;
    const term = email.trim().toLowerCase();
    return (
      a.email.toLowerCase().includes(term) ||
      (a.fullName && a.fullName.toLowerCase().includes(term))
    );
  });

  const saveAccount = (acc: SavedAccount) => {
    const updated = [
      acc,
      ...savedAccounts.filter((a) => a.email.toLowerCase() !== acc.email.toLowerCase()),
    ].slice(0, 5); // Keep up to 5 recent accounts
    setSavedAccounts(updated);
    try {
      localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(updated));
    } catch {
      // ignore storage error
    }
  };

  const removeSavedAccount = (e: React.MouseEvent, emailToRemove: string) => {
    e.stopPropagation();
    const updated = savedAccounts.filter((a) => a.email !== emailToRemove);
    setSavedAccounts(updated);
    try {
      localStorage.setItem(SAVED_ACCOUNTS_KEY, JSON.stringify(updated));
    } catch {
      // ignore
    }
    toast.success("Account removed from quick sign-in.");
    if (email === emailToRemove) {
      setEmail("");
      setPassword("");
    }
  };

  const selectAccount = (acc: SavedAccount, directLogin = false) => {
    setEmail(acc.email);
    setPassword(acc.password || "");
    setTab("login");
    if (directLogin && acc.password) {
      quickLogin(acc.email, acc.password);
    } else {
      toast.success(`Credentials filled for ${acc.fullName || acc.email}! ✨`);
    }
  };

  const quickLogin = async (userEmail: string, userPass: string) => {
    setLoading(true);
    try {
      const profile = await login(userEmail, userPass);
      saveAccount({
        email: userEmail,
        password: userPass,
        fullName: profile.full_name || userEmail.split("@")[0],
        role: profile.role,
        savedAt: Date.now(),
      });
      toast.success(`Welcome back, ${profile.full_name}! 🎉`);
      navigate("/dashboard");
    } catch {
      toast.error("Sign in failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const profile = await login(email, password);
      // Save successful login credentials with actual verified role from profile
      saveAccount({
        email,
        password,
        fullName: profile.full_name || email.split("@")[0],
        role: profile.role,
        savedAt: Date.now(),
      });
      toast.success(`Welcome back, ${profile.full_name}! 🎉`);
      navigate("/dashboard");
    } catch {
      toast.error("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post("/api/auth/register", {
        email,
        password,
        full_name: fullName,
        role: registerRole,
      });

      // Save credentials locally with chosen role so user can immediately quick-login
      saveAccount({
        email,
        password,
        fullName: fullName || email,
        role: registerRole,
        savedAt: Date.now(),
      });

      toast.success(`Account created as ${registerRole === "admin" ? "Administrator" : "Teacher"}! Credentials saved for quick login. 🎉`);
      // Keep email & password populated and switch to login tab
      setTab("login");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Registration failed.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (role: "admin" | "teacher") => {
    setEmail(role === "admin" ? "admin@school.edu" : "teacher@school.edu");
    setPassword(role === "admin" ? "Admin@123" : "Teacher@123");
    setTab("login");
    toast.success(`${role === "admin" ? "Admin" : "Teacher"} credentials populated!`);
  };

  return (
    <div className="login-bg">
      {/* Left branding panel */}
      <div className="login-left">
        <div className="login-brand">
          <div className="login-brand-icon">
            <BrainCircuit size={36} color="#fff" />
          </div>
          <h1>GradeMatrix</h1>
          <p>AI-Powered Student Performance Intelligence</p>
        </div>

        <div className="login-features">
          <div className="login-feat">
            <Brain size={20} />
            <div>
              <strong>ML Predictions</strong>
              <span>Early &amp; mid-term academic forecasting</span>
            </div>
          </div>
          <div className="login-feat">
            <BarChart3 size={20} />
            <div>
              <strong>Analytics Dashboard</strong>
              <span>Class-wide risk distribution &amp; trends</span>
            </div>
          </div>
          <div className="login-feat">
            <GraduationCap size={20} />
            <div>
              <strong>Personalised Recommendations</strong>
              <span>Targeted improvement strategies per student</span>
            </div>
          </div>
          <div className="login-feat">
            <ShieldCheck size={20} />
            <div>
              <strong>Role-Based Access</strong>
              <span>Secure JWT auth for teachers &amp; admins</span>
            </div>
          </div>
        </div>

        {/* Demo credential cards */}
        <div className="demo-creds">
          <p className="demo-label">Demo accounts:</p>
          <div className="demo-cards">
            <button className="demo-card" onClick={() => fillDemo("admin")} type="button">
              <ShieldCheck size={16} />
              <div>
                <strong>Admin</strong>
                <span>admin@school.edu</span>
              </div>
            </button>
            <button className="demo-card" onClick={() => fillDemo("teacher")} type="button">
              <GraduationCap size={16} />
              <div>
                <strong>Teacher</strong>
                <span>teacher@school.edu</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="login-right">
        <div className="login-form-box">
          <div className="form-logo-mobile">
            <BrainCircuit size={28} color="#4f46e5" />
            <span>GradeMatrix</span>
          </div>

          {/* Tabs */}
          <div className="auth-tabs">
            <button
              className={`auth-tab${tab === "login" ? " active" : ""}`}
              onClick={() => setTab("login")}
              type="button"
            >
              Sign In
            </button>
            <button
              className={`auth-tab${tab === "register" ? " active" : ""}`}
              onClick={() => setTab("register")}
              type="button"
            >
              Register
            </button>
          </div>

          {tab === "login" ? (
            <form onSubmit={handleLogin} className="auth-form">
              <h2>Welcome back</h2>
              <p className="auth-sub">Sign in to your account to continue</p>

              <div className="field-group" style={{ position: "relative" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label>
                    <Mail size={14} /> Email / Username
                  </label>
                  {savedAccounts.length > 0 && (
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {savedAccounts.length} saved account{savedAccounts.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 220)}
                  placeholder="e.g. tarun@123 or admin@school.edu"
                  autoComplete="username"
                  required
                  autoFocus
                />

                {/* Autocomplete Popup / Saved Password Suggestions */}
                {showSuggestions && filteredAccounts.length > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "100%",
                      left: 0,
                      right: 0,
                      marginTop: 4,
                      background: "rgba(255, 255, 255, 0.98)",
                      backdropFilter: "blur(12px)",
                      border: "1px solid rgba(79, 70, 229, 0.25)",
                      borderRadius: 10,
                      boxShadow: "0 14px 35px -5px rgba(15, 23, 42, 0.22)",
                      zIndex: 100,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        padding: "6px 12px",
                        fontSize: 10.5,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.5px",
                        color: "#6366f1",
                        background: "rgba(99, 102, 241, 0.08)",
                        borderBottom: "1px solid rgba(226, 232, 240, 0.8)",
                        display: "flex",
                        alignItems: "center",
                        gap: 5,
                      }}
                    >
                      <Sparkles size={11} /> Saved Accounts &amp; Passwords
                    </div>
                    <div style={{ maxHeight: 210, overflowY: "auto" }}>
                      {filteredAccounts.map((acc) => (
                        <div
                          key={acc.email}
                          onMouseDown={() => {
                            selectAccount(acc);
                            setShowSuggestions(false);
                          }}
                          style={{
                            padding: "9px 12px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            borderBottom: "1px solid rgba(241, 245, 249, 0.9)",
                            transition: "background 0.15s ease",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = "#f1f5f9")}
                          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <div
                              style={{
                                width: 28,
                                height: 28,
                                borderRadius: "50%",
                                background: acc.role === "admin" ? "#eef2ff" : "#ecfdf5",
                                color: acc.role === "admin" ? "#4f46e5" : "#059669",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexShrink: 0,
                              }}
                            >
                              {acc.role === "admin" ? <ShieldCheck size={14} /> : <UserCheck size={14} />}
                            </div>
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 600, color: "#1e293b", lineHeight: 1.2 }}>
                                {acc.fullName || acc.email}
                              </div>
                              <div style={{ fontSize: 11, color: "#64748b" }}>{acc.email}</div>
                            </div>
                          </div>

                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 600,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background: acc.role === "admin" ? "#e0e7ff" : "#d1fae5",
                                color: acc.role === "admin" ? "#3730a3" : "#065f46",
                              }}
                            >
                              {acc.role === "admin" ? "Admin" : "Teacher"}
                            </span>
                            <button
                              type="button"
                              title="Delete saved credentials"
                              onMouseDown={(e) => {
                                e.stopPropagation();
                                removeSavedAccount(e, acc.email);
                              }}
                              style={{
                                background: "none",
                                border: "none",
                                cursor: "pointer",
                                color: "#94a3b8",
                                padding: 2,
                                display: "flex",
                                alignItems: "center",
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
                              onMouseLeave={(e) => (e.currentTarget.style.color = "#94a3b8")}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="field-group">
                <label>
                  <Lock size={14} /> Password
                </label>
                <div className="pw-wrap">
                  <input
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    className="pw-toggle"
                    onClick={() => setShowPw((v) => !v)}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <span className="btn-spinner" /> : "Sign In"}
              </button>

              <p className="auth-hint">
                💡 Credentials are saved automatically so you can 1-click sign in next time!
              </p>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="auth-form">
              <h2>Create account</h2>
              <p className="auth-sub">Register to save credentials &amp; login directly</p>

              <div className="field-group">
                <label>
                  <User size={14} /> Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Tarun Sharma"
                  required
                  autoFocus
                />
              </div>

              <div className="field-group">
                <label>
                  <ShieldCheck size={14} /> Account Role
                </label>
                <div className="role-selector-group">
                  <button
                    type="button"
                    className={`role-select-pill ${registerRole === "teacher" ? "active" : ""}`}
                    onClick={() => setRegisterRole("teacher")}
                  >
                    <GraduationCap size={15} /> Teacher
                  </button>
                  <button
                    type="button"
                    className={`role-select-pill ${registerRole === "admin" ? "active" : ""}`}
                    onClick={() => setRegisterRole("admin")}
                  >
                    <ShieldCheck size={15} /> Administrator
                  </button>
                </div>
              </div>

              <div className="field-group">
                <label>
                  <Mail size={14} /> Email / Username
                </label>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. tarun@123 or tarun@school.edu"
                  required
                />
              </div>

              <div className="field-group">
                <label>
                  <Lock size={14} /> Password
                </label>
                <div className="pw-wrap">
                  <input
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min 6 characters"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    className="pw-toggle"
                    onClick={() => setShowPw((v) => !v)}
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
                {loading ? <span className="btn-spinner" /> : "Create Account & Save Credentials"}
              </button>

              <p className="auth-hint">
                ✨ Account will be saved for instant 1-click login!
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
