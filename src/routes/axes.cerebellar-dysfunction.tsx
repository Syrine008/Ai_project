import { createFileRoute } from "@tanstack/react-router";
import { Axis3CerebellarDysfunctionPage } from "@/pages/Axis3CerebellarDysfunctionPage";

export const Route = createFileRoute("/axes/cerebellar-dysfunction")({
  head: () => ({ meta: [{ title: "Axis 3 · Cerebellar Dysfunction — brAIn" }] }),
  component: Axis3CerebellarDysfunctionPage,
});
