import { readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "../dist");
const jsBudget = 550 * 1024;
const cssBudget = 60 * 1024;

function assetPath(url) {
  const clean = url.split("?")[0].replace(/^\/+/, "");
  return path.join(dist, clean);
}

function gzipSize(file) {
  return gzipSync(readFileSync(file)).byteLength;
}

function tags(html, name) {
  return html.match(new RegExp(`<${name}\\b[^>]*>`, "gi")) ?? [];
}

function attr(tag, name) {
  const match = tag.match(new RegExp(`${name}="([^"]+)"`, "i"));
  return match?.[1] ?? null;
}

const html = readFileSync(path.join(dist, "index.html"), "utf8");
const jsFiles = new Set();
const cssFiles = new Set();

for (const tag of tags(html, "script")) {
  const src = attr(tag, "src");
  if (src?.endsWith(".js")) {
    jsFiles.add(src);
  }
}

for (const tag of tags(html, "link")) {
  const href = attr(tag, "href");
  const rel = attr(tag, "rel");
  if (!href) continue;
  if (rel === "modulepreload" && href.endsWith(".js")) {
    jsFiles.add(href);
  }
  if (rel === "stylesheet" && href.endsWith(".css")) {
    cssFiles.add(href);
  }
}

if (jsFiles.size === 0) {
  console.error("No initial JavaScript found in dist/index.html. Run the build first.");
  process.exit(1);
}

function report(label, files, budget) {
  let total = 0;
  for (const url of files) {
    const file = assetPath(url);
    const size = gzipSize(file);
    const raw = statSync(file).size;
    total += size;
    console.log(
      `${label} ${path.basename(file)}: ${(size / 1024).toFixed(1)} KiB gzip (${(raw / 1024).toFixed(1)} KiB raw)`,
    );
  }
  console.log(
    `${label} total: ${(total / 1024).toFixed(1)} KiB gzip / ${(budget / 1024).toFixed(0)} KiB budget`,
  );
  return total;
}

const jsTotal = report("JS", jsFiles, jsBudget);
const cssTotal = report("CSS", cssFiles, cssBudget);

let failed = false;
if (jsTotal > jsBudget) {
  console.error(
    `Initial JavaScript exceeds budget by ${((jsTotal - jsBudget) / 1024).toFixed(1)} KiB.`,
  );
  failed = true;
}
if (cssTotal > cssBudget) {
  console.error(`Initial CSS exceeds budget by ${((cssTotal - cssBudget) / 1024).toFixed(1)} KiB.`);
  failed = true;
}

if (failed) {
  process.exit(1);
}
