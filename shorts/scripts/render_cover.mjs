// -*- node ESM -*-
// 9:16 커버 정지컷 렌더. 영상 렌더(render_remotion_fast.mjs)와 같은 번들 캐시를 재사용한다.
// (Cover 컴포지션은 같은 Root 안에 있으므로 src 미변경이면 번들 재생성 없음 → 빠름.)
//
// 사용: node scripts/render_cover.mjs <outPath> [compositionId=Cover]
import { bundle } from "@remotion/bundler";
import { selectComposition, renderStill, ensureBrowser } from "@remotion/renderer";
import path from "node:path";
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");            // shorts/
const entryPoint = path.join(ROOT, "src", "index.ts");

const outPath = process.argv[2];
const compId = process.argv[3] || "Cover";
if (!outPath) {
  console.error("usage: node render_cover.mjs <outPath> [compositionId=Cover]");
  process.exit(2);
}

// ---- 번들 캐시 (render_remotion_fast.mjs 와 동일 위치/규칙) ----
const cacheDir = path.join(ROOT, "node_modules", ".cache", "phonespot-remotion-bundle");
const bundleDir = path.join(cacheDir, "bundle");
const hashFile = path.join(cacheDir, "srchash.txt");

function hashDirs(dirs) {
  const h = crypto.createHash("sha1");
  const walk = (d) => {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue;
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else { try { const s = fs.statSync(p); h.update(p + "|" + s.size + "|" + s.mtimeMs + "\n"); } catch {} }
    }
  };
  for (const d of dirs) walk(d);
  for (const extra of ["package.json", "remotion.config.ts", "remotion.config.js"]) {
    try { const s = fs.statSync(path.join(ROOT, extra)); h.update(extra + s.mtimeMs); } catch {}
  }
  return h.digest("hex");
}

async function getServeUrl() {
  const want = hashDirs([path.join(ROOT, "src"), path.join(ROOT, "public")]);
  try {
    if (
      fs.existsSync(path.join(bundleDir, "index.html")) &&
      fs.existsSync(hashFile) &&
      fs.readFileSync(hashFile, "utf8").trim() === want
    ) {
      console.log("[cover] reusing cached bundle (src unchanged)");
      return bundleDir;
    }
  } catch {}
  console.log("[cover] bundling (no cache or src changed)...");
  fs.mkdirSync(cacheDir, { recursive: true });
  try { fs.rmSync(bundleDir, { recursive: true, force: true }); } catch {}
  const served = await bundle({ entryPoint, outDir: bundleDir });
  fs.writeFileSync(hashFile, want);
  return served;
}

function findLocalChrome() {
  const env = (process.env.REMOTION_BROWSER_EXECUTABLE || "").trim();
  if (env && fs.existsSync(env)) return env;
  try {
    const pw = path.join(ROOT, "..", ".playwright");
    if (fs.existsSync(pw)) {
      for (const d of fs.readdirSync(pw)) {
        if (!d.toLowerCase().startsWith("chromium")) continue;
        for (const rel of [
          ["chrome-win", "chrome.exe"],
          ["chrome-win64", "chrome.exe"],
          ["chrome-headless-shell-win64", "chrome-headless-shell.exe"],
          ["chrome-headless-shell-win", "chrome-headless-shell.exe"],
        ]) {
          const exe = path.join(pw, d, rel[0], rel[1]);
          if (fs.existsSync(exe)) return exe;
        }
      }
    }
  } catch {}
  const cands = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google", "Chrome", "Application", "chrome.exe"),
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  for (const c of cands) { try { if (c && fs.existsSync(c)) return c; } catch {} }
  return null;
}

const t0 = Date.now();
let browserExecutable = null;
try {
  await ensureBrowser();
} catch (e) {
  browserExecutable = findLocalChrome();
  if (!browserExecutable) throw e;
  console.log("[cover] Remotion browser download failed; using local Chrome: " + browserExecutable);
}
const serveUrl = await getServeUrl();
const composition = await selectComposition({ serveUrl, id: compId, inputProps: {}, browserExecutable });
const isJpg = /\.jpe?g$/i.test(outPath);
fs.mkdirSync(path.dirname(outPath), { recursive: true });
await renderStill({
  serveUrl,
  composition,
  browserExecutable,
  output: outPath,
  frame: 0,
  imageFormat: isJpg ? "jpeg" : "png",
  jpegQuality: isJpg ? 92 : undefined,
});
console.log(`[cover] done in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${outPath}`);
