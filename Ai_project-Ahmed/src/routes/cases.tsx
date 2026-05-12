import { createFileRoute } from "@tanstack/react-router";
import { CaseHistoryPage } from "@/pages/CaseHistoryPage";

export const Route = createFileRoute("/cases")({
  head: () => ({ meta: [{ title: "Case History — brAIn" }] }),
  component: CaseHistoryPage,
});
