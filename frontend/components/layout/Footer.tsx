import Link from "next/link";
export function Footer() {
  return (
    <footer className="site-footer container">
      <div>
        <Link href="/" className="footer-brand">
          PlayerWorth<span>.</span>
        </Link>
        <p className="small muted">The game. Another value.</p>
      </div>
      <div className="footer-links">
        <Link href="/#player-search">Find a player ↗</Link>
        <Link href="/models">Model Lab ↗</Link>
        <Link href="/rankings">Rankings ↗</Link>
      </div>
      <p className="footer-note">
        Estimates are model outputs for educational and analytical use.
      </p>
    </footer>
  );
}
