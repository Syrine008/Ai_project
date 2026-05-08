import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis7EpilepsyNetworkPage() {
  return <AxisPageTemplate axis={getAxisById("axis7-epilepsy-network")} />;
}
