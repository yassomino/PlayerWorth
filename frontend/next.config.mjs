import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL(".", import.meta.url));
const config = { turbopack: { root }, outputFileTracingRoot: root };
export default config;
