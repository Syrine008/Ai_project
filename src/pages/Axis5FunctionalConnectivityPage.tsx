import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis5FunctionalConnectivityPage() {
  return <AxisPageTemplate axis={getAxisById("axis5-functional-connectivity")} />;
}
