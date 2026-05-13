import { createFileRoute } from "@tanstack/react-router";
import { Axis1AlzheimerDementiaPage } from "@/pages/Axis1AlzheimerDementiaPage";

export const Route = createFileRoute("/axes/alzheimer-dementia")({
  head: () => ({ meta: [{ title: "Axis 1 · Alzheimer & Dementias — brAIn" }] }),
  component: Axis1AlzheimerDementiaPage,
});
