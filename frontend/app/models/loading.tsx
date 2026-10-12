import { Skeleton } from "@/components/ui/States";
export default function Loading() {
  return (
    <div className="container route-shell">
      <span className="eyebrow">MODEL LAB</span>
      <h1>Behind the estimate.</h1>
      <Skeleton rows={5} />
    </div>
  );
}
