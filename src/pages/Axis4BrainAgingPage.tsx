import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis4BrainAgingPage() {
  return <AxisPageTemplate axis={getAxisById("axis4-brain-aging")} />;
}
