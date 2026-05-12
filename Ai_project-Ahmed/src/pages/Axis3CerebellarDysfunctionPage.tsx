import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis3CerebellarDysfunctionPage() {
  return <AxisPageTemplate axis={getAxisById("axis3-cerebellar-dysfunction")} />;
}
