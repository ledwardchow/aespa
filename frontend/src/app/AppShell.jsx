import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar.jsx";
export function AppShell({ section, preferences, children }) {
  const [collapsed, setCollapsed] = useState(() => window.innerWidth <= 700);
  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth <= 700) setCollapsed(true);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <div className={"shell" + (collapsed ? " sidebar-collapsed" : "")}>
      <Sidebar
        section={section}
        preferences={preferences}
        collapsed={collapsed}
        onToggle={() => setCollapsed((value) => !value)}
      />
      <main className="main">{children}</main>
    </div>
  );
}
