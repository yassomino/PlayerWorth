import { cache } from "react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { ApiError, getPlayer } from "@/lib/api/client";
import { PlayerProfile } from "@/components/player/PlayerProfile";
import { RouteShell } from "@/components/ui/RouteShell";
import "@/components/player/profile.css";

const loadPlayer = cache(getPlayer);
type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ season?: string | string[] }>;
};
function validId(raw: string) {
  return (
    /^\d+$/.test(raw) && Number.isSafeInteger(Number(raw)) && Number(raw) > 0
  );
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const data = validId(id)
    ? await loadPlayer(Number(id)).catch(() => null)
    : null;
  return {
    title: data?.player.name ?? "Player profile",
    description: data
      ? `Explore model-estimated value and Premier League performance history for ${data.player.name}.`
      : "Explore PlayerWorth player profiles.",
  };
}
export default async function PlayerPage({ params, searchParams }: Props) {
  const { id } = await params;
  if (!validId(id)) notFound();
  const result = await loadPlayer(Number(id))
    .then((data) => ({ data, error: null }))
    .catch((error: unknown) => ({ data: null, error }));
  if (result.error instanceof ApiError && result.error.status === 404)
    notFound();
  if (!result.data)
    return (
      <RouteShell
        eyebrow="PLAYER PROFILE"
        title="Profile temporarily unavailable"
        description="We couldn’t load this player right now. Try again shortly, or return to search."
      />
    );
  const { season } = await searchParams;
  return (
    <PlayerProfile
      key={id}
      data={result.data}
      initialSeason={typeof season === "string" ? season : undefined}
    />
  );
}
