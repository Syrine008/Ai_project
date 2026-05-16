import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig, mergeConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

const tanstackStartDefaults = {
  importProtection: {
    behavior: "error",
    client: {
      files: ["**/server/**"],
      specifiers: ["server-only"],
    },
  },
};

export default defineConfig({
  resolve: {
    alias: {
      "@": `${process.cwd()}/src`,
    },
    dedupe: [
      "react",
      "react-dom",
      "react/jsx-runtime",
      "react/jsx-dev-runtime",
      "@tanstack/react-query",
      "@tanstack/query-core",
    ],
  },
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    tailwindcss(),
    tsConfigPaths({ projects: ["./tsconfig.json"] }),
    tanstackStart(
      mergeConfig(tanstackStartDefaults, {
        server: { entry: "server" },
      }),
    ),
    nitro(),
    viteReact(),
  ],
});
