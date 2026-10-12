"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, useState } from "react";
export function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const toggle = useRef<HTMLButtonElement>(null);
  return (
    <header
      className="site-header"
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          setOpen(false);
          toggle.current?.focus();
        }
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <div className="container nav-inner">
        <Link
          href="/"
          className="wordmark"
          onClick={() => setOpen(false)}
          aria-label="PlayerWorth home"
        >
          <span className="brand-mark" aria-hidden="true">
            PW
          </span>
          PLAYER<span>WORTH</span>
          <span className="brand-dot">.</span>
        </Link>
        <button
          className="menu-toggle"
          ref={toggle}
          aria-expanded={open}
          aria-controls="main-navigation"
          onClick={() => setOpen(!open)}
        >
          {open ? "Close" : "Menu"}{" "}
          <span aria-hidden="true">{open ? "×" : "☰"}</span>
        </button>
        <nav
          id="main-navigation"
          aria-label="Main navigation"
          className={open ? "main-nav open" : "main-nav"}
        >
          {[
            ["Home", "/"],
            ["Players", "/#player-search"],
            ["Rankings", "/rankings"],
            ["Model Lab", "/models"],
          ].map(([label, href]) => (
            <Link
              key={href}
              href={href}
              aria-current={
                (
                  href === "/#player-search"
                    ? pathname.startsWith("/players/")
                    : pathname === href
                )
                  ? "page"
                  : undefined
              }
              onClick={() => setOpen(false)}
            >
              {label}
            </Link>
          ))}
        </nav>
        <span className="nav-context">
          PREMIER LEAGUE <span className="status-dot" />
        </span>
      </div>
    </header>
  );
}
