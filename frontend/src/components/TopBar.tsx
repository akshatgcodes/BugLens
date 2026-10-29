import { Link, NavLink } from "react-router-dom";
import { Logo, useLogout } from "./RequireOwner";

export default function TopBar() {
  const logout = useLogout();
  return (
    <header className="topbar">
      <Link to="/" className="logo">
        <Logo /> <span className="logo-text">BugLens</span>
      </Link>
      <nav className="nav">
        <NavLink to="/" end>
          Review
        </NavLink>
        <NavLink to="/history">History</NavLink>
        <NavLink to="/rules">Rules</NavLink>
      </nav>
      <button className="link-btn" onClick={logout}>
        Log out
      </button>
    </header>
  );
}
