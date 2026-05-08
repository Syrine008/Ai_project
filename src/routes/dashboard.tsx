import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/pages/DashboardPage";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — brAIn" }] }),
  component: DashboardPage,
});
