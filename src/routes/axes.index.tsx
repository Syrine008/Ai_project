import { createFileRoute } from "@tanstack/react-router";
import { AxesOverviewPage } from "@/pages/AxesOverviewPage";

export const Route = createFileRoute("/axes/")({
  head: () => ({ meta: [{ title: "All Axes — brAIn" }] }),
  component: AxesOverviewPage,
});
