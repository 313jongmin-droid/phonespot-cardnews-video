// -*- node ESM -*-
// 빠른 Remotion 렌더 경로.
//  #1 동시성: 환경변수 PHONESPOT_RENDER_CONCURRENCY (숫자 | "50%" | "auto"=Remotion 자동)
//  #3 번들 재사용: src 가 바뀌지 않으면 webpack 번들을 다시 만들지 않는다(렌더마다 번들링 제거).
//  #2 싼 중간 인코딩: raw 는 어차피 Step 6 finalize 에서 최종 인코딩되므로 crf/preset 을 싸게.
//     (Step 6 가 화질 게이트라 최종 결과 규격/화질은 그대로.)
//
// 실패하면 0이 아닌 코드로 종료 → run_codex_casual.bat 가 기존 `npx remotion render` CLI 로 폴백.
//
// 사용: node scripts/render_remotion_fast.mjs <compositionId> <outPath>
import { bundle } from "@remotion/bundler";
import { selectComposition, renderMedia, ensureBrowser } from "@remotion/renderer";
import path from "node:path";
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");            // shorts/
const entryPoint = path.join(ROOT, "src", "index.ts");

const compId = process.argv[2] || "CasualShort";
const outPath = process.argv[3];
if (!outPath) {
  console.error("usage: node render_remotion_fast.mjs <compositionId> <outPath>");
  process.exit(2);
}

// ---- #1 concurrency ----
const concEnv = (process.env.PHONESPOT_RENDER_CONCURRENCY || "50%").trim();
let concurrency;
if (/^\d+$/.test(concEnv)) concurrency = parseInt(concEnv, 10);
else if (concEnv.toLowerCase() === "auto" || concEnv === "") concurrency = null;
else concurrency = concEnv; // e.g. "50%"

// ---- #2 cheap intermediate ----
const crf = parseInt(process.env.PHONESPOT_RAW_CRF || "23", 10);
const x264Preset = process.env.PHONESPOT_RAW_PRESET || "veryfast";

// ---- #3 bundle cache (reuse unless src changed) ----
const cacheDir = path.join(ROOT, "node_modules", ".cache", "phonespot-remotion-bundle");
const bundleDir = path.join(cacheDir, "bundle");
const hashFile = path.join(cacheDir, "srchash.txt");

function hashDirs(dirs) {
  // src/ 코드 + public/ 에셋(일러스트 포함)을 모두 해시한다.
  // public 을 빼면, 새로 가져온 일러스트가 캐시된 번들에 안 들어가 렌더에 옛 이미지가 나온다.
  const h = crypto.createHash("sha1");
  const walk = (d) => {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue;
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else {
        try { const s = fs.statSync(p); h.update(p + "|" + s.size + "|" + s.mtimeMs + "\n"); } catch {}
      }
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
      console.log("[render] reusing cached bundle (src unchanged)");
      return bundleDir;
    }
  } catch {}
  console.log("[render] bundling (no cache or src changed)...");
  fs.mkdirSync(cacheDir, { recursive: true });
  try { fs.rmSync(bundleDir, { recursive: true, force: true }); } catch {}
  let lastLogged = -1;
  const served = await bundle({
    entryPoint,
    outDir: bundleDir,
    onProgress: (p) => {
      const v = Math.round(p);
      if (v >= lastLogged + 20) { lastLogged = v; console.log("[bundle] " + v + "%"); }
    },
  });
  fs.writeFileSync(hashFile, want);
  return served;
}

const t0 = Date.now();
// Remotion 전용 브라우저 보장. 다운로드가 방화벽 등으로 막히면 시스템 Chrome 으로 폴백.
function findLocalChrome() {
  const env = (process.env.REMOTION_BROWSER_EXECUTABLE || "").trim();
  if (env && fs.existsSync(env)) return env;
  // 1순위: 셋업이 설치한 Playwright chromium (이 repo 의 .playwright, 모든 생산기 PC 에 존재)
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
  // 2순위: 시스템 Chrome / Edge
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
let browserExecutable = null;
try {
  await ensureBrowser();
} catch (e) {
  browserExecutable = findLocalChrome();
  if (!browserExecutable) throw e;
  console.log("[render] Remotion browser download failed; using local Chrome: " + browserExecutable);
}
const serveUrl = await getServeUrl();
const composition = await selectComposition({ serveUrl, id: compId, inputProps: {}, browserExecutable });
console.log(
  `[render] ${compId} ${composition.width}x${composition.height} frames=${composition.durationInFrames} ` +
  `concurrency=${concurrency} crf=${crf} preset=${x264Preset}`
);
let lastPc = -1;
const renderOpts = {
  serveUrl,
  composition,
  browserExecutable,
  codec: "h264",
  outputLocation: outPath,
  crf,
  x264Preset,
  concurrency,
  pixelFormat: "yuv420p",
  onProgress: ({ progress }) => {
    const pc = Math.round(progress * 100);
    if (pc >= lastPc + 10) { lastPc = pc; console.log("[render] " + pc + "%"); }
  },
};
// GPU 가속(옵트인): blur/box-shadow/gradient 가 많은 컴포지션은 GPU 로 프레임당 비용이 크게 준다.
// 기본 미설정 = 기존(CPU/swiftshader) 동작 그대로. 테스트: set PHONESPOT_GL=angle
const gl = (process.env.PHONESPOT_GL || "").trim();
if (gl) {
  renderOpts.chromiumOptions = { gl };
  const chromeMode = (process.env.PHONESPOT_CHROME_MODE || "chrome-for-testing").trim();
  if (chromeMode) renderOpts.chromeMode = chromeMode; // 헤드리스에서 GPU 디스플레이 사용
  console.log(`[render] GPU mode: gl=${gl} chromeMode=${renderOpts.chromeMode || "-"}`);
}
await renderMedia(renderOpts);
console.log(`[render] done in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${outPath}`);
