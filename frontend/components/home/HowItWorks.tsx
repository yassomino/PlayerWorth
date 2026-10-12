import Link from "next/link";
export function HowItWorks() {
  return (
    <section className="method container" aria-labelledby="method-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">THE THINKING BEHIND THE NUMBERS</span>
          <h2 id="method-title">Performance. Perspective. PlayerWorth.</h2>
        </div>
        <Link className="text-link" href="/models">
          Our methodology ↗
        </Link>
      </div>
      <div className="steps">
        {[
          [
            "01",
            "The performance",
            "Historical Premier League seasons. Real minutes, goals and assists.",
          ],
          [
            "02",
            "The model",
            "Age, minutes, goals, assists and position. Five inputs, learned relationships.",
          ],
          [
            "03",
            "The perspective",
            "An estimated market value in euros. Another way to read the game.",
          ],
        ].map(([number, title, text]) => (
          <div className="step" key={number}>
            <span className="step-number">{number}</span>
            <div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="evolution">
        <span className="eyebrow">BUILT THROUGH COMPARISON</span>
        <p>
          Linear Regression <span>→</span> Ridge <span>→</span> Random Forest{" "}
          <span>→</span> XGBoost <span>→</span>{" "}
          <strong>XGBoost + position</strong>
        </p>
        <Link href="/models" aria-label="Explore model development">
          ↗
        </Link>
      </div>
    </section>
  );
}
