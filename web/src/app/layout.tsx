"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/cognition", label: "Cognition" },
  { href: "/spaces", label: "Context Spaces" },
  { href: "/data", label: "All Data" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <body>
        <div className="layout">
          <aside className="sidebar">
            <h1>Founder OS</h1>
            <div className="sub">Context Dashboard</div>
            <nav className="nav">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={
                    pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
                      ? "active"
                      : ""
                  }
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
