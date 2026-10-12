import { Suspense } from "react";
import Link from "next/link";
import { Hero } from "@/components/home/Hero";
import { ModelSnapshot } from "@/components/home/ModelSnapshot";
import {
  RankingDisclaimer,
  RankingsPreview,
} from "@/components/home/RankingsPreview";
import { HowItWorks } from "@/components/home/HowItWorks";
import { Skeleton } from "@/components/ui/States";
export const dynamic = "force-dynamic";
export default function Home() {
  return (
    <>
      <Hero />
      <section
        className="snapshot-section container"
        aria-label="Temporal backtest performance"
      >
        <Suspense fallback={<Skeleton rows={2} />}>
          <ModelSnapshot />
        </Suspense>
        <p className="evaluation-note">
          HISTORICAL TEMPORAL EVALUATION{" "}
          <span>
            Earlier-season training, later-season evaluation. Not test scores of
            the final all-data model.
          </span>
        </p>
      </section>
      <section className="watch container" aria-labelledby="watch-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">WHERE THE NUMBERS DISAGREE</span>
            <h2 id="watch-title">
              MODEL WATCH<span className="accent">.</span>
            </h2>
          </div>
          <Link href="/rankings" className="text-link">
            View all rankings ↗
          </Link>
        </div>
        <div className="rankings-grid">
          {(["higher", "lower"] as const).map((direction) => (
            <Suspense
              key={direction}
              fallback={
                <div className="ranking-card">
                  <Skeleton />
                </div>
              }
            >
              <RankingsPreview direction={direction} />
            </Suspense>
          ))}
        </div>
        <RankingDisclaimer />
      </section>
      <HowItWorks />
    </>
  );
}
