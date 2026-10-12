import { ModelLab } from "@/components/model/ModelLab";
import { getCurrentModel, getModels } from "@/lib/api/client";
import "@/components/ui/analytics.css";
export const metadata = {
  title: {
    absolute: "PlayerWorth Model Lab — How the Valuation Model Was Built",
  },
  description:
    "Explore PlayerWorth's model experiments, temporal evaluation, rejected features and limitations.",
};
export default async function Models() {
  const [current, registered] = await Promise.allSettled([
    getCurrentModel(),
    getModels(),
  ]);
  return (
    <ModelLab
      current={current.status === "fulfilled" ? current.value : null}
      registered={registered.status === "fulfilled" ? registered.value : null}
    />
  );
}
