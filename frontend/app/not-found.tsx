import { RouteShell } from "@/components/ui/RouteShell";
export default function NotFound() {
  return (
    <RouteShell
      eyebrow="OFF THE PITCH / 404"
      title="Page not found"
      description="This page is not in the PlayerWorth lineup. Search a player or explore the Model Lab from the navigation."
      backLabel="Back to PlayerWorth"
    />
  );
}
