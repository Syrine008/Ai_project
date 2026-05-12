import { createFileRoute } from "@tanstack/react-router";
import { Axis7EpilepsyNetworkPage } from "@/pages/Axis7EpilepsyNetworkPage";

export const Route = createFileRoute("/axes/epilepsy-network")({
  head: () => ({ meta: [{ title: "Axis 7 · Epilepsy Network — brAIn" }] }),
  component: Axis7EpilepsyNetworkPage,
});
