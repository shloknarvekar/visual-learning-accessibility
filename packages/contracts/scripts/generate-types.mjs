// Generates TypeScript types from lesson.schema.json.
//   node scripts/generate-types.mjs          write src/generated/lesson.ts
//   node scripts/generate-types.mjs --check  exit 1 if the committed file is out of date
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { compileFromFile } from "json-schema-to-typescript";

const schemaPath = fileURLToPath(new URL("../lesson.schema.json", import.meta.url));
const outputUrl = new URL("../src/generated/lesson.ts", import.meta.url);

const generated = await compileFromFile(schemaPath, {
  bannerComment:
    "/* Generated from lesson.schema.json by `npm run contracts:generate`. Do not edit by hand. */",
});

const normalise = (text) => text.replace(/\r\n/g, "\n");

if (process.argv.includes("--check")) {
  const committed = await readFile(outputUrl, "utf8").catch(() => "");
  if (normalise(committed) !== normalise(generated)) {
    console.error("src/generated/lesson.ts is out of date. Run: npm run contracts:generate");
    process.exit(1);
  }
  console.log("Generated types are up to date.");
} else {
  await mkdir(new URL(".", outputUrl), { recursive: true });
  await writeFile(outputUrl, generated);
  console.log("Wrote src/generated/lesson.ts");
}
