import { createFileRoute } from "@tanstack/react-router";
import { Axis2ParkinsonAtypicalPage } from "@/pages/Axis2ParkinsonAtypicalPage";

export const Route = createFileRoute("/axes/parkinson-atypical")({
  head: () => ({ meta: [{ title: "Axis 2 · Parkinson & Atypical — brAIn" }] }),
  component: Axis2ParkinsonAtypicalPage,
});
