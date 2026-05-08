import { createFileRoute } from "@tanstack/react-router";
import { Axis6NeuromotorVideoPage } from "@/pages/Axis6NeuromotorVideoPage";

export const Route = createFileRoute("/axes/neuromotor-video")({
  head: () => ({ meta: [{ title: "Axis 6 · Neuromotor Video — brAIn" }] }),
  component: Axis6NeuromotorVideoPage,
});
