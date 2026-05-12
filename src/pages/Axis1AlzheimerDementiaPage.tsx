import { AxisPageTemplate } from "@/components/AxisPageTemplate";
import { getAxisById } from "@/lib/axes";

export function Axis1AlzheimerDementiaPage() {
  return <AxisPageTemplate axis={getAxisById("axis1-alzheimer-dementia")} />;
}
