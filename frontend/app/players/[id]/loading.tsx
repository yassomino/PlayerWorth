import { Skeleton } from "@/components/ui/States";
export default function LoadingPlayer() {
  return (
    <div
      className="container"
      style={{ paddingBlock: 48 }}
      aria-label="Loading player profile"
    >
      <Skeleton rows={2} />
      <Skeleton rows={2} />
      <Skeleton rows={4} />
      <Skeleton rows={3} />
    </div>
  );
}
