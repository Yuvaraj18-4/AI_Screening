import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("Frontend build output contains index.html and compiled bundles", () => {
  const distDir = path.resolve("dist");
  assert.ok(fs.existsSync(distDir), "dist directory must exist");
  assert.ok(fs.existsSync(path.join(distDir, "index.html")), "dist/index.html must exist");

  const assetsDir = path.join(distDir, "assets");
  assert.ok(fs.existsSync(assetsDir), "dist/assets directory must exist");
  const files = fs.readdirSync(assetsDir);
  assert.ok(files.some((f) => f.endsWith(".js")), "dist/assets must contain JS bundle");
  assert.ok(files.some((f) => f.endsWith(".css")), "dist/assets must contain CSS bundle");
});
