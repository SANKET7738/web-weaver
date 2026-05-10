def render_screenrecording_capture_script() -> str:
    return r'''#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { chromium } = require("playwright");

const VIEWPORT = { name: "desktop", width: 1440, height: 1000 };
const TOP_HOLD_MS = 2500;
const BOTTOM_HOLD_MS = 2000;
const MIN_SCROLL_MS = 7000;
const MAX_SCROLL_MS = 15000;

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return fallback;
  return process.argv[index + 1];
}

function routeForSlug(slug) {
  return slug === "home" ? "/" : `/${slug}.html`;
}

function safeName(value) {
  return String(value || "page").replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "page";
}

function convertWebmToMp4(inputPath, outputPath) {
  const result = spawnSync("ffmpeg", [
    "-y",
    "-i", inputPath,
    "-an",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-r", "25",
    "-fps_mode", "cfr",
    "-movflags", "+faststart",
    outputPath,
  ], { encoding: "utf8" });

  if (result.status !== 0) {
    throw new Error(`ffmpeg exited with code ${result.status}: ${result.stderr || result.stdout}`);
  }
}

async function waitForVisualStability(page) {
  await page.waitForLoadState("domcontentloaded", { timeout: 10000 });
  await page.waitForLoadState("load", { timeout: 10000 }).catch(() => {});
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
  }).catch(() => {});
  await page.waitForTimeout(500);
}

async function scrollThroughPage(page, maxScrollY, durationMs) {
  await page.evaluate(async ({ maxScrollY, durationMs }) => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtmlBehavior = html.style.scrollBehavior;
    const prevBodyBehavior = body ? body.style.scrollBehavior : "";
    html.style.scrollBehavior = "auto";
    if (body) body.style.scrollBehavior = "auto";
    const overrideStyle = document.createElement("style");
    overrideStyle.setAttribute("data-screenrecording-override", "true");
    overrideStyle.textContent = "html, body, * { scroll-behavior: auto !important; }";
    document.head.appendChild(overrideStyle);

    try {
      window.scrollTo({ left: 0, top: 0, behavior: "instant" });
      if (maxScrollY <= 0) return;
      await new Promise(resolve => {
        const startedAt = performance.now();
        function tick(now) {
          const progress = Math.min(1, (now - startedAt) / durationMs);
          const eased = progress < 0.5
            ? 2 * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 2) / 2;
          window.scrollTo({ left: 0, top: Math.round(maxScrollY * eased), behavior: "instant" });
          if (progress < 1) {
            requestAnimationFrame(tick);
          } else {
            resolve();
          }
        }
        requestAnimationFrame(tick);
      });
    } finally {
      overrideStyle.remove();
      html.style.scrollBehavior = prevHtmlBehavior;
      if (body) body.style.scrollBehavior = prevBodyBehavior;
    }
  }, { maxScrollY, durationMs });
}

async function main() {
  const blueprintPath = argValue("--blueprint", "/workspace/input/blueprint.json");
  const baseUrl = argValue("--base-url", "http://127.0.0.1:3000");
  const outDir = argValue("--out-dir", "/workspace/validation/screenrecordings");
  const reportPath = argValue("--report", "/workspace/validation/screenrecording_capture_report.json");
  const tempVideoDir = path.join(outDir, ".tmp");

  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(tempVideoDir, { recursive: true });
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });

  const blueprint = JSON.parse(fs.readFileSync(blueprintPath, "utf8"));
  const pages = blueprint.pages || [];
  const failures = [];
  const pageReports = [];

  const browser = await chromium.launch({ headless: true });
  try {
    for (const pageSpec of pages) {
      const slug = pageSpec.slug;
      const route = routeForSlug(slug);
      const url = baseUrl.replace(/\/$/, "") + route;
      const safeSlug = safeName(slug);
      const outputFile = `${safeSlug}.mp4`;
      const outputPath = path.join(outDir, outputFile);
      const context = await browser.newContext({
        viewport: VIEWPORT,
        recordVideo: {
          dir: tempVideoDir,
          size: { width: VIEWPORT.width, height: VIEWPORT.height },
        },
      });
      const page = await context.newPage();
      const video = page.video();
      const pageReport = {
        slug,
        route,
        viewport: VIEWPORT,
        scroll_height: null,
        max_scroll_y: null,
        scroll_duration_ms: null,
        top_hold_ms: TOP_HOLD_MS,
        bottom_hold_ms: BOTTOM_HOLD_MS,
        format: "mp4",
        path: outputFile,
        failures: [],
      };

      try {
        const response = await page.goto(url, {
          waitUntil: "domcontentloaded",
          timeout: 10000,
        });
        const status = response ? response.status() : null;
        pageReport.response_status = status;
        if (status === null || status < 200 || status >= 300) {
          const message = `${slug} returned non-2xx status during screen recording: ${status}`;
          failures.push(message);
          pageReport.failures.push(message);
        } else {
          await waitForVisualStability(page);
          const scrollHeight = await page.evaluate(() => {
            const body = document.body;
            const html = document.documentElement;
            return Math.max(
              body?.scrollHeight || 0,
              body?.offsetHeight || 0,
              html?.clientHeight || 0,
              html?.scrollHeight || 0,
              html?.offsetHeight || 0
            );
          });
          const maxScrollY = Math.max(0, scrollHeight - VIEWPORT.height);
          const scrollDurationMs = Math.round(Math.min(
            MAX_SCROLL_MS,
            Math.max(MIN_SCROLL_MS, maxScrollY * 2)
          ));
          pageReport.scroll_height = scrollHeight;
          pageReport.max_scroll_y = maxScrollY;
          pageReport.scroll_duration_ms = scrollDurationMs;

          await page.evaluate(() => {
            const html = document.documentElement;
            const body = document.body;
            const prevHtmlBehavior = html.style.scrollBehavior;
            const prevBodyBehavior = body ? body.style.scrollBehavior : "";
            html.style.scrollBehavior = "auto";
            if (body) body.style.scrollBehavior = "auto";
            window.scrollTo({ left: 0, top: 0, behavior: "instant" });
            html.style.scrollBehavior = prevHtmlBehavior;
            if (body) body.style.scrollBehavior = prevBodyBehavior;
          });
          await page.waitForTimeout(TOP_HOLD_MS);
          await scrollThroughPage(page, maxScrollY, scrollDurationMs);
          await page.waitForTimeout(BOTTOM_HOLD_MS);
          await page.waitForTimeout(500);
        }
      } catch (error) {
        const message = `Screen recording failed for ${slug}: ${error.message}`;
        failures.push(message);
        pageReport.failures.push(message);
      } finally {
        await page.close().catch(() => {});
        await context.close().catch(() => {});
      }

      try {
        const tempPath = await video.path();
        if (fs.existsSync(outputPath)) {
          fs.rmSync(outputPath);
        }
        convertWebmToMp4(tempPath, outputPath);
        pageReport.bytes = fs.statSync(outputPath).size;
        if (pageReport.bytes <= 0) {
          const message = `Screen recording for ${slug} is empty`;
          failures.push(message);
          pageReport.failures.push(message);
        }
        fs.rmSync(tempPath, { force: true });
      } catch (error) {
        const message = `Could not persist screen recording for ${slug}: ${error.message}`;
        failures.push(message);
        pageReport.failures.push(message);
      }

      pageReports.push(pageReport);
    }
  } finally {
    await browser.close();
    fs.rmSync(tempVideoDir, { recursive: true, force: true });
  }

  const recordedPages = pageReports.filter(pageReport => pageReport.bytes > 0).length;
  const valid = failures.length === 0 && pages.length > 0 && recordedPages === pages.length;
  const report = {
    valid,
    viewport: VIEWPORT,
    top_hold_ms: TOP_HOLD_MS,
    bottom_hold_ms: BOTTOM_HOLD_MS,
    min_scroll_ms: MIN_SCROLL_MS,
    max_scroll_ms: MAX_SCROLL_MS,
    output_dir: outDir,
    metrics: {
      expected_pages: pages.length,
      recorded_pages: recordedPages,
    },
    failures,
    pages: pageReports,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  process.exit(valid ? 0 : 2);
}

main().catch(error => {
  const reportPath = argValue("--report", "/workspace/validation/screenrecording_capture_report.json");
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, JSON.stringify({
    valid: false,
    viewport: VIEWPORT,
    failures: [`Screen recording capture crashed: ${error.stack || error.message}`],
    pages: [],
  }, null, 2) + "\n");
  process.exit(2);
});
'''.strip() + "\n"
