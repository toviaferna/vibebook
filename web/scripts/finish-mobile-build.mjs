import { access, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "../dist-mobile");
const source = path.join(dist, "mobile.html");
const destination = path.join(dist, "index.html");

try {
  await access(destination);
  console.log("dist-mobile/index.html already exists");
} catch {
  await rename(source, destination);
  console.log("renamed dist-mobile/mobile.html -> index.html");
}
