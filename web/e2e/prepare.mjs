import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const library = path.join(root, ".tmp", "e2e");

fs.rmSync(library, { recursive: true, force: true });
fs.mkdirSync(library, { recursive: true });
