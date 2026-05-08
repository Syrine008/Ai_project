import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis6NeuromotorVideoPage() {
  return <AxisPageTemplate axis={getAxisById("axis6-neuromotor-video")} />;
}
