"use client";
import Link from "next/link";
export default function ErrorPage({
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <section className="container route-shell" role="alert">
      <span className="eyebrow">PLAYERWORTH / TEMPORARILY UNAVAILABLE</span>
      <h1>Let’s try that again.</h1>
      <p>This page could not finish loading. Your player data is unchanged.</p>
      <div className="error-actions">
        <button className="primary-link" onClick={retry}>
          Try again
        </button>
        <Link className="text-link" href="/">
          Back to PlayerWorth ↗
        </Link>
      </div>
    </section>
  );
}
