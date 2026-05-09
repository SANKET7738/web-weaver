def render_playwright_checker_script() -> str:
    return r'''#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "mobile", width: 390, height: 844 },
];
const MIN_TEXT_LENGTH = 500;
const MIN_SCROLL_HEIGHT_RATIO = 1.0;

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return fallback;
  return process.argv[index + 1];
}

function routeForSlug(slug) {
  return slug === "home" ? "/" : `/${slug}.html`;
}

function localHrefToRoute(href) {
  if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
    return null;
  }
  try {
    const parsed = new URL(href, "http://127.0.0.1:3000");
    if (parsed.origin !== "http://127.0.0.1:3000") return null;
    if (parsed.pathname === "/index.html") return "/";
    return parsed.pathname;
  } catch {
    return null;
  }
}

async function main() {
  const blueprintPath = argValue("--blueprint", "/workspace/input/blueprint.json");
  const baseUrl = argValue("--base-url", "http://127.0.0.1:3000");
  const outPath = argValue("--out", "/workspace/validation/playwright_report.json");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });

  const blueprint = JSON.parse(fs.readFileSync(blueprintPath, "utf8"));
  const pages = blueprint.pages || [];
  const failures = [];
  const pageReports = [];
  const allFailedRequests = [];
  const allConsoleErrors = [];
  const allPageErrors = [];
  let routesOk = 0;
  let sectionVisibilityOk = 0;
  let expectedSections = 0;
  let localLinksChecked = 0;
  let brokenLocalLinks = 0;
  let overflowFailures = 0;

  const browser = await chromium.launch({ headless: true });
  try {
    for (const pageSpec of pages) {
      const slug = pageSpec.slug;
      const route = routeForSlug(slug);
      const url = baseUrl.replace(/\/$/, "") + route;
      const pageReport = { slug, route, viewports: [] };

      for (const viewport of VIEWPORTS) {
        const page = await browser.newPage({ viewport });
        const failedRequests = [];
        const consoleErrors = [];
        const pageErrors = [];

        page.on("requestfailed", request => {
          const requestUrl = request.url();
          if (requestUrl.startsWith(baseUrl)) {
            failedRequests.push({
              url: requestUrl,
              failure: request.failure()?.errorText || "request failed",
            });
          }
        });
        page.on("response", response => {
          const responseUrl = response.url();
          if (responseUrl.startsWith(baseUrl) && response.status() >= 400) {
            failedRequests.push({
              url: responseUrl,
              status: response.status(),
            });
          }
        });
        page.on("console", message => {
          if (message.type() === "error") {
            consoleErrors.push(message.text());
          }
        });
        page.on("pageerror", error => {
          pageErrors.push(error.message);
        });

        let responseStatus = null;
        let routeOk = false;
        let metrics = {};
        try {
          const response = await page.goto(url, {
            waitUntil: "domcontentloaded",
            timeout: 10000,
          });
          responseStatus = response ? response.status() : null;
          routeOk = responseStatus !== null && responseStatus >= 200 && responseStatus < 300;
          await page.waitForLoadState("load", { timeout: 10000 }).catch(() => {});
          metrics = await page.evaluate(() => {
            const body = document.body;
            const html = document.documentElement;
            const sectionBoxes = Array.from(document.querySelectorAll("section[id]")).map(section => {
              const rect = section.getBoundingClientRect();
              return {
                id: section.id,
                width: rect.width,
                height: rect.height,
                visible: rect.width > 1 && rect.height > 20,
              };
            });
            return {
              title: document.title || "",
              bodyTextLength: (body?.innerText || "").trim().length,
              scrollHeight: Math.max(body?.scrollHeight || 0, html?.scrollHeight || 0),
              scrollWidth: Math.max(body?.scrollWidth || 0, html?.scrollWidth || 0),
              viewportWidth: window.innerWidth,
              viewportHeight: window.innerHeight,
              sectionBoxes,
              localHrefs: Array.from(document.querySelectorAll("a[href]")).map(anchor => anchor.getAttribute("href")),
            };
          });
        } catch (error) {
          failures.push(`Playwright failed to load ${slug} at ${viewport.name}: ${error.message}`);
        }

        if (viewport.name === "desktop" && routeOk) routesOk += 1;

        const textOk = (metrics.bodyTextLength || 0) >= MIN_TEXT_LENGTH;
        const heightOk = (metrics.scrollHeight || 0) >= (metrics.viewportHeight || viewport.height) * MIN_SCROLL_HEIGHT_RATIO;
        const overflowOk = (metrics.scrollWidth || 0) <= (metrics.viewportWidth || viewport.width) + 8;
        if (!overflowOk) overflowFailures += 1;

        if (!textOk) failures.push(`${slug} ${viewport.name} body text is too short`);
        if (!heightOk) failures.push(`${slug} ${viewport.name} scroll height is too short`);
        if (!overflowOk) failures.push(`${slug} ${viewport.name} has horizontal overflow`);

        if (viewport.name === "desktop") {
          for (const section of pageSpec.sections || []) {
            expectedSections += 1;
            const found = (metrics.sectionBoxes || []).find(box => box.id === section.id);
            if (found && found.visible) {
              sectionVisibilityOk += 1;
            } else {
              failures.push(`Section ${section.id} is missing or not visibly laid out`);
            }
          }

          const expectedRoutes = new Set(pages.map(candidate => routeForSlug(candidate.slug)));
          const seenLocalHrefs = new Set();
          for (const href of metrics.localHrefs || []) {
            const hrefRoute = localHrefToRoute(href);
            if (!hrefRoute || hrefRoute === "/") continue;
            if (seenLocalHrefs.has(hrefRoute)) continue;
            seenLocalHrefs.add(hrefRoute);
            if (!expectedRoutes.has(hrefRoute)) {
              localLinksChecked += 1;
              brokenLocalLinks += 1;
              failures.push(`Unexpected or broken local href on ${slug}: ${href}`);
            } else {
              localLinksChecked += 1;
            }
          }
        }

        if (failedRequests.length) {
          failures.push(`${slug} ${viewport.name} has failed local requests`);
          allFailedRequests.push(...failedRequests.map(item => ({ slug, viewport: viewport.name, ...item })));
        }
        if (consoleErrors.length) {
          failures.push(`${slug} ${viewport.name} has console errors`);
          allConsoleErrors.push(...consoleErrors.map(text => ({ slug, viewport: viewport.name, text })));
        }
        if (pageErrors.length) {
          failures.push(`${slug} ${viewport.name} has uncaught page errors`);
          allPageErrors.push(...pageErrors.map(text => ({ slug, viewport: viewport.name, text })));
        }

        pageReport.viewports.push({
          viewport,
          responseStatus,
          routeOk,
          textOk,
          heightOk,
          overflowOk,
          metrics,
          failedRequests,
          consoleErrors,
          pageErrors,
        });
        await page.close();
      }
      pageReports.push(pageReport);
    }
  } finally {
    await browser.close();
  }

  const checks = {
    routes: routesOk === pages.length,
    section_visibility: expectedSections === 0 || sectionVisibilityOk === expectedSections,
    local_links: brokenLocalLinks === 0,
    failed_local_requests: allFailedRequests.length === 0,
    console_errors: allConsoleErrors.length === 0,
    page_errors: allPageErrors.length === 0,
    responsive_overflow: overflowFailures === 0,
  };

  const valid = Object.values(checks).every(Boolean);
  const report = {
    valid,
    checks,
    metrics: {
      expected_pages: pages.length,
      responsive_routes: routesOk,
      expected_sections: expectedSections,
      visible_sections: sectionVisibilityOk,
      local_links_checked: localLinksChecked,
      broken_local_links: brokenLocalLinks,
      failed_local_requests: allFailedRequests.length,
      console_errors: allConsoleErrors.length,
      page_errors: allPageErrors.length,
      overflow_failures: overflowFailures,
    },
    failures,
    failed_requests: allFailedRequests,
    console_errors: allConsoleErrors,
    page_errors: allPageErrors,
    pages: pageReports,
  };

  fs.writeFileSync(outPath, JSON.stringify(report, null, 2) + "\n");
  process.exit(valid ? 0 : 2);
}

main().catch(error => {
  const outPath = argValue("--out", "/workspace/validation/playwright_report.json");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify({
    valid: false,
    checks: {},
    metrics: {},
    failures: [`Playwright sanity checker crashed: ${error.stack || error.message}`],
  }, null, 2) + "\n");
  process.exit(2);
});
'''.strip() + "\n"
