import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  BrainCircuit,
  History,
  AlertTriangle,
  BarChart2,
  Sliders,
  TrendingUp,
  LogOut,
  User,
  ShieldCheck,
} from "lucide-react";
import toast from "react-hot-toast";

const navItems = [
  { to: "/dashboard", icon: <LayoutDashboard size={18} />, label: "Dashboard" },
  { to: "/predict", icon: <BrainCircuit size={18} />, label: "Predict" },
  { to: "/simulator", icon: <Sliders size={18} />, label: "What-If Simulator" },
  { to: "/progress", icon: <TrendingUp size={18} />, label: "Student Progress" },
  { to: "/history", icon: <History size={18} />, label: "History" },
  { to: "/at-risk", icon: <AlertTriangle size={18} />, label: "At-Risk Students" },
  { to: "/analytics", icon: <BarChart2 size={18} />, label: "Analytics" },
];

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    toast.success("Logged out.");
    navigate("/login");
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo-icon">
          <BrainCircuit size={20} />
        </div>
        <div className="sidebar-brand-text">
          <span>GradeMatrix</span>
          <span className="sidebar-brand-badge">AI</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar-circle">
            {user?.role === "admin" ? <ShieldCheck size={18} /> : <User size={18} />}
          </div>
          <div className="user-details">
            <div className="user-name" title={user?.full_name || "User"}>{user?.full_name || "User"}</div>
            <div className={`user-role-tag ${user?.role || "teacher"}`}>
              {user?.role === "admin" ? "Administrator" : "Teacher"}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="sidebar-logout-btn"
          title="Sign Out"
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
