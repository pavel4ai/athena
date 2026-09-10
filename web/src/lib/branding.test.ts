import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const indexPath = fileURLToPath(new URL("../../index.html", import.meta.url));
const packagePath = fileURLToPath(new URL("../../package.json", import.meta.url));
const localeDirectory = fileURLToPath(new URL("../i18n/", import.meta.url));
const upstreamName = ["Her", "mes"].join("");

const localeFiles = readdirSync(localeDirectory)
  .filter((name) => name.endsWith(".ts"))
  .filter((name) => !["context.ts", "index.ts", "types.ts"].includes(name));

describe("dashboard branding", () => {
  it("keeps the Athena browser title", () => {
    const html = readFileSync(indexPath, "utf8");

    expect(html).toContain("<title>Athena Agent - Dashboard</title>");
    expect(html.toLowerCase()).not.toContain(upstreamName.toLowerCase());
  });

  it("keeps product and publisher identity in every locale", () => {
    expect(localeFiles.length).toBeGreaterThan(0);

    for (const name of localeFiles) {
      const source = readFileSync(`${localeDirectory}/${name}`, "utf8");

      expect(source).toMatch(/\bbrand:\s*["']Athena Agent["']/);
      expect(source).toMatch(/\borg:\s*["']Futurebound Corp\.["']/);
      expect(source.toLowerCase()).not.toContain(upstreamName.toLowerCase());
    }
  });

  it("keeps the Nous UI kit as an external dependency", () => {
    const packageJson = JSON.parse(readFileSync(packagePath, "utf8")) as {
      dependencies?: Record<string, string>;
    };

    expect(packageJson.dependencies?.["@nous-research/ui"]).toBeTruthy();
  });
});
