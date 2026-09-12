// Validates every examples/*.json file against lesson.schema.json.
import { readdir, readFile } from "node:fs/promises";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const packageRoot = new URL("../", import.meta.url);
const examplesDir = new URL("examples/", packageRoot);

const readJson = async (url) => JSON.parse(await readFile(url, "utf8"));

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(await readJson(new URL("lesson.schema.json", packageRoot)));

const files = (await readdir(examplesDir)).filter((name) => name.endsWith(".json"));
if (files.length === 0) {
  console.error("No example files found in examples/.");
  process.exit(1);
}

let failed = false;
for (const file of files) {
  if (validate(await readJson(new URL(file, examplesDir)))) {
    console.log(`valid   ${file}`);
  } else {
    failed = true;
    console.error(`INVALID ${file}`);
    console.error(`  ${ajv.errorsText(validate.errors, { separator: "\n  " })}`);
  }
}

process.exit(failed ? 1 : 0);
