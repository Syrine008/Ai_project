import { createFileRoute } from "@tanstack/react-router";
import { Axis4BrainAgingPage } from "@/pages/Axis4BrainAgingPage";

export const Route = createFileRoute("/axes/brain-aging")({
  head: () => ({ meta: [{ title: "Axis 4 · Brain Aging — brAIn" }] }),
  component: Axis4BrainAgingPage,
});
