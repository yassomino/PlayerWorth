import { Skeleton } from "@/components/ui/States";
export default function Loading() {
  return (
    <div className="container route-shell">
      <span className="eyebrow">MODEL RANKINGS</span>
      <h1>Comparing the estimates.</h1>
      <Skeleton rows={6} />
    </div>
  );
}
