import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis2ParkinsonAtypicalPage() {
  return <AxisPageTemplate axis={getAxisById("axis2-parkinson-atypical")} />;
}
