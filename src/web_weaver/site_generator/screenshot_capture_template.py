def render_screenshot_capture_script() -> str:
    return r'''#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const VIEWPORT = { name: "desktop", width: 1440, height: 1000 };
const SLICE_STEP = 1000;
const SLICE_OVERLAP = VIEWPORT.height - SLICE_STEP;

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

function slicePositions(scrollHeight) {
  const maxScrollY = Math.max(0, scrollHeight - VIEWPORT.height);
  const positions = [];
  for (let y = 0; y <= maxScrollY; y += SLICE_STEP) {
    positions.push(y);
  }
  if (!positions.length || positions[positions.length - 1] !== maxScrollY) {
    positions.push(maxScrollY);
  }
  return [...new Set(positions)];
}

async function waitForVisualStability(page) {
  await page.waitForLoadState("domcontentloaded", { timeout: 10000 });
  await page.waitForLoadState("load", { timeout: 10000 }).catch(() => {});
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
  }).catch(() => {});
  await page.waitForTimeout(300);
}

async function neutralizeViewportPinnedElements(page) {
  return await page.evaluate(() => {
    const pinnedElements = [];
    document.documentElement.style.setProperty("scroll-behavior", "auto", "important");
    document.body.style.setProperty("scroll-behavior", "auto", "important");

    for (const element of Array.from(document.body.querySelectorAll("*"))) {
      const style = window.getComputedStyle(element);
      if (style.position !== "fixed" && style.position !== "sticky") continue;

      const rect = element.getBoundingClientRect();
      const record = {
        tag: element.tagName.toLowerCase(),
        id: element.id || null,
        className: typeof element.className === "string" ? element.className : "",
        position: style.position,
      };

      element.setAttribute("data-web-weaver-capture-position", style.position);
      if (style.position === "fixed") {
        element.style.setProperty("position", "absolute", "important");
        element.style.setProperty("top", `${rect.top + window.scrollY}px`, "important");
        element.style.setProperty("left", `${rect.left + window.scrollX}px`, "important");
        element.style.setProperty("right", "auto", "important");
        element.style.setProperty("bottom", "auto", "important");
        element.style.setProperty("width", `${rect.width}px`, "important");
        element.style.setProperty("height", `${rect.height}px`, "important");
      } else {
        element.style.setProperty("position", "static", "important");
        element.style.setProperty("top", "auto", "important");
        element.style.setProperty("right", "auto", "important");
        element.style.setProperty("bottom", "auto", "important");
        element.style.setProperty("left", "auto", "important");
      }
      pinnedElements.push(record);
    }
    return pinnedElements;
  });
}

async function main() {
  const blueprintPath = argValue("--blueprint", "/workspace/input/blueprint.json");
  const baseUrl = argValue("--base-url", "http://127.0.0.1:3000");
  const outDir = argValue("--out-dir", "/workspace/validation/screenshots");
  const reportPath = argValue("--report", "/workspace/validation/screenshot_capture_report.json");

  fs.mkdirSync(outDir, { recursive: true });
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
      const slugDirName = safeName(slug);
      const pageDir = path.join(outDir, slugDirName);
      fs.mkdirSync(pageDir, { recursive: true });

      const page = await browser.newPage({ viewport: VIEWPORT });
      const pageReport = {
        slug,
        route,
        viewport: VIEWPORT,
        slice_step: SLICE_STEP,
        slice_overlap: SLICE_OVERLAP,
        scroll_height: null,
        slices: [],
        full_page: null,
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
          const message = `${slug} returned non-2xx status during screenshot capture: ${status}`;
          failures.push(message);
          pageReport.failures.push(message);
          pageReports.push(pageReport);
          await page.close();
          continue;
        }

        await waitForVisualStability(page);
        pageReport.neutralized_pinned_elements = await neutralizeViewportPinnedElements(page);
        await page.waitForTimeout(100);
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
        pageReport.scroll_height = scrollHeight;

        const positions = slicePositions(scrollHeight);
        for (const [index, scrollY] of positions.entries()) {
          await page.evaluate(y => window.scrollTo(0, y), scrollY);
          await page.waitForTimeout(150);
          const fileName = `${slugDirName}_${String(index + 1).padStart(3, "0")}.png`;
          const absolutePath = path.join(pageDir, fileName);
          await page.screenshot({
            path: absolutePath,
            fullPage: false,
            animations: "disabled",
          });
          pageReport.slices.push({
            index: index + 1,
            scroll_y: scrollY,
            path: path.relative(outDir, absolutePath).split(path.sep).join("/"),
          });
        }

        try {
          await page.evaluate(() => window.scrollTo(0, 0));
          await page.waitForTimeout(150);
          const fullFileName = `${slugDirName}_full.png`;
          const fullAbsolutePath = path.join(pageDir, fullFileName);
          await page.screenshot({
            path: fullAbsolutePath,
            fullPage: true,
            animations: "disabled",
          });
          pageReport.full_page = {
            path: path.relative(outDir, fullAbsolutePath).split(path.sep).join("/"),
            bytes: fs.statSync(fullAbsolutePath).size,
          };
        } catch (error) {
          const message = `Full-page screenshot failed for ${slug}: ${error.message}`;
          failures.push(message);
          pageReport.failures.push(message);
        }
      } catch (error) {
        const message = `Screenshot capture failed for ${slug}: ${error.message}`;
        failures.push(message);
        pageReport.failures.push(message);
      } finally {
        await page.close();
      }

      pageReports.push(pageReport);
    }
  } finally {
    await browser.close();
  }

  const totalSlices = pageReports.reduce((sum, pageReport) => sum + pageReport.slices.length, 0);
  const totalFullPages = pageReports.reduce((sum, pageReport) => sum + (pageReport.full_page ? 1 : 0), 0);
  const valid = failures.length === 0
    && pages.length > 0
    && pageReports.every(pageReport => pageReport.slices.length > 0 && pageReport.full_page);
  const report = {
    valid,
    viewport: VIEWPORT,
    slice_step: SLICE_STEP,
    slice_overlap: SLICE_OVERLAP,
    output_dir: outDir,
    metrics: {
      expected_pages: pages.length,
      captured_pages: pageReports.filter(pageReport => pageReport.slices.length > 0).length,
      total_slices: totalSlices,
      total_full_pages: totalFullPages,
    },
    failures,
    pages: pageReports,
  };

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  process.exit(valid ? 0 : 2);
}

main().catch(error => {
  const reportPath = argValue("--report", "/workspace/validation/screenshot_capture_report.json");
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, JSON.stringify({
    valid: false,
    viewport: VIEWPORT,
    slice_step: SLICE_STEP,
    slice_overlap: SLICE_OVERLAP,
    failures: [`Screenshot capture crashed: ${error.stack || error.message}`],
    pages: [],
  }, null, 2) + "\n");
  process.exit(2);
});
'''.strip() + "\n"
