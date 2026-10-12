import { RouteShell } from "@/components/ui/RouteShell";
export default function PlayerNotFound() {
  return (
    <RouteShell
      eyebrow="PLAYER PROFILE / NOT FOUND"
      title="Player not found"
      backLabel="Back to PlayerWorth"
      description="This player isn’t in the available records. Return to PlayerWorth and search for another player."
    />
  );
}
