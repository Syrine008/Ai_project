import { createFileRoute } from "@tanstack/react-router";
import { Axis5FunctionalConnectivityPage } from "@/pages/Axis5FunctionalConnectivityPage";

export const Route = createFileRoute("/axes/functional-connectivity")({
  head: () => ({ meta: [{ title: "Axis 5 · Functional Connectivity — brAIn" }] }),
  component: Axis5FunctionalConnectivityPage,
});
