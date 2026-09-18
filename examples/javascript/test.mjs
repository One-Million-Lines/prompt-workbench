// Cross-language conformance test for the JavaScript reference renderer.
// Run: node test.mjs   (exit code 0 = all fixtures pass)

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { canonicalJson } from "./canonical.mjs";
import { renderString } from "./renderer.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(join(here, "fixtures.json"), "utf-8"));

let failures = 0;

for (const c of fixtures.canonical) {
  const got = canonicalJson(c.value);
  if (got !== c.expected) {
    failures++;
    console.error(`CANONICAL FAIL: got ${got} expected ${c.expected}`);
  }
}

for (const r of fixtures.render) {
  const declared = new Set(r.declared);
  const got = renderString(r.template, r.values, declared);
  if (got !== r.expected) {
    failures++;
    console.error(`RENDER FAIL [${r.name}]: got ${JSON.stringify(got)} expected ${JSON.stringify(r.expected)}`);
  }
}

if (failures === 0) {
  console.log(`OK: ${fixtures.canonical.length} canonical + ${fixtures.render.length} render fixtures passed.`);
  process.exit(0);
} else {
  console.error(`${failures} fixture(s) failed.`);
  process.exit(1);
}
