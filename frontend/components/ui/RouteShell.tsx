import Link from "next/link";
export function RouteShell({
  eyebrow,
  title,
  description,
  backLabel = "Back to player search",
}: {
  eyebrow: string;
  title: string;
  description: string;
  backLabel?: string;
}) {
  return (
    <section className="container route-shell">
      <span className="eyebrow">{eyebrow}</span>
      <h1>
        {title}
        <span className="accent">.</span>
      </h1>
      <p>{description}</p>
      <Link href="/" className="primary-link">
        ← {backLabel}
      </Link>
      <div className="shell-line" aria-hidden="true" />
    </section>
  );
}
