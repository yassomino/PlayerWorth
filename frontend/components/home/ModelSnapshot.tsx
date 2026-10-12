import Link from "next/link";
import { getCurrentModel } from "@/lib/api/client";
import type { ModelResponse } from "@/lib/api/types";
import { formatMoney, fullMoney } from "@/lib/format";
import { Unavailable } from "../ui/States";
export function ModelSnapshotView({ model }: { model: ModelResponse }) {
  return (
    <div className="snapshot-grid">
      <div className="snapshot-intro">
        <span className="eyebrow">THE MODEL / V{model.model_version}</span>
        <h2>
          PlayerWorth V1<span className="accent">.</span>
        </h2>
        <p>XGBoost + position</p>
        <Link className="text-link" href="/models">
          Explore Model Lab <span>↗</span>
        </Link>
      </div>
      <div className="metric">
        <span className="metric-label">TEMPORAL OOF MAE</span>
        <strong title={model.mae === null ? undefined : fullMoney(model.mae)}>
          {model.mae === null ? "—" : formatMoney(model.mae, 2)}
        </strong>
        <span>Average absolute error</span>
      </div>
      <div className="metric">
        <span className="metric-label">TEMPORAL OOF R²</span>
        <strong>{model.r2?.toFixed(3) ?? "—"}</strong>
        <span>Historical explanatory fit</span>
      </div>
      <div className="metric">
        <span className="metric-label">TRAINING OBSERVATIONS</span>
        <strong>{model.training_row_count.toLocaleString("en-GB")}</strong>
        <span>{model.training_seasons.length} Premier League seasons</span>
      </div>
    </div>
  );
}
export async function ModelSnapshot() {
  const model = await getCurrentModel().catch(() => null);
  return model ? (
    <ModelSnapshotView model={model} />
  ) : (
    <Unavailable>Model snapshot is temporarily unavailable.</Unavailable>
  );
}
