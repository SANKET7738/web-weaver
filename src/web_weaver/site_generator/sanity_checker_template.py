def render_sanity_checker_script() -> str:
    return r'''#!/usr/bin/env python3
import argparse
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


CONTENT_COVERAGE_THRESHOLD = 0.75
SECTION_COVERAGE_THRESHOLD = 0.80
ASSET_COVERAGE_THRESHOLD = 0.50
MIN_PALETTE_COLORS_USED = 3
MIN_FONT_MATCHES = 1


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)

    @property
    def text(self):
        return " ".join(self.text_parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprint", default="/workspace/input/blueprint.json")
    parser.add_argument("--design-plan", default="/workspace/input/design_plan.json")
    parser.add_argument("--site-dir", default="/workspace/output/reference_site")
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument(
        "--framework",
        default="html_css",
        choices=["html_css", "react_css", "react_tailwind", "solid_tailwind"],
    )
    parser.add_argument("--out", default="/workspace/validation/sanity_report.json")
    args = parser.parse_args()

    blueprint_path = Path(args.blueprint)
    design_plan_path = Path(args.design_plan)
    site_dir = Path(args.site_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    failures = []
    metrics = {}

    blueprint = load_json(blueprint_path, failures, "blueprint")
    design_plan = load_json(design_plan_path, failures, "design_plan")

    if blueprint is None or design_plan is None:
        write_report(out_path, False, {}, metrics, failures)
        return 1

    pages = blueprint.get("pages", [])
    expected_page_files = expected_files_for_pages(pages)
    generated_files = list_generated_files(site_dir)
    combined_code = "\n".join(read_text(path) for path in generated_files)
    combined_html_text = extract_all_html_text(site_dir)

    checks = {}
    checks["file_structure"] = check_file_structure(site_dir, combined_code, failures)
    checks["page_files"] = check_page_files(site_dir, expected_page_files, failures)
    checks["routes"] = check_routes(args.base_url, pages, failures, metrics)
    if args.framework == "html_css":
        checks["content_coverage"] = check_content_coverage(
            blueprint,
            combined_html_text,
            failures,
            metrics,
        )
        checks["section_coverage"] = check_section_coverage(
            blueprint,
            combined_code,
            failures,
            metrics,
        )
    else:
        # React / Solid builds produce a static HTML shell where all content
        # and section ids only appear in the rendered DOM after JS hydration.
        # The Playwright sanity check (a real headless browser) covers this
        # at the DOM level, so we skip the static-source-text checks here
        # rather than fail on a meaningless 0% match.
        checks["content_coverage"] = True
        checks["section_coverage"] = True
        metrics["content_coverage_skipped"] = f"framework={args.framework}"
        metrics["section_coverage_skipped"] = f"framework={args.framework}"
    checks["palette_usage"] = check_palette_usage(
        design_plan,
        combined_code,
        failures,
        metrics,
    )
    checks["font_usage"] = check_font_usage(
        design_plan,
        combined_code,
        failures,
        metrics,
    )
    checks["asset_coverage"] = check_asset_coverage(
        blueprint,
        site_dir,
        combined_code,
        failures,
        metrics,
    )
    checks["policy"] = check_policy(combined_code, failures, metrics, args.framework)

    hard_checks = [
        checks["file_structure"],
        checks["page_files"],
        checks["routes"],
        checks["content_coverage"],
        checks["palette_usage"],
        checks["font_usage"],
        checks["policy"],
    ]
    valid = all(hard_checks)

    write_report(out_path, valid, checks, metrics, failures)
    return 0 if valid else 2


def load_json(path, failures, label):
    if not path.exists():
        failures.append(f"Missing {label} file: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        failures.append(f"Invalid {label} JSON: {error}")
        return None


def expected_files_for_pages(pages):
    expected = {}
    for page in pages:
        slug = page.get("slug", "")
        if not slug:
            continue
        expected[slug] = "index.html" if slug == "home" else f"{slug}.html"
    return expected


def list_generated_files(site_dir):
    if not site_dir.exists():
        return []
    suffixes = {".html", ".css", ".js", ".svg"}
    return [
        path
        for path in site_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    ]


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def extract_all_html_text(site_dir):
    parts = []
    if not site_dir.exists():
        return ""
    for html_path in site_dir.rglob("*.html"):
        parser = TextExtractor()
        parser.feed(read_text(html_path))
        parts.append(parser.text)
    return " ".join(parts)


def check_file_structure(site_dir, combined_code, failures):
    ok = True
    if not site_dir.exists():
        failures.append(f"Missing reference site directory: {site_dir}")
        return False
    if not (site_dir / "index.html").exists():
        failures.append("Missing required home page: index.html")
        ok = False

    has_css_file = any(site_dir.rglob("*.css"))
    has_inline_style = bool(re.search(r"<style\b", combined_code, re.IGNORECASE))
    if not has_css_file and not has_inline_style:
        failures.append("Missing CSS file or inline style block")
        ok = False
    return ok


def check_page_files(site_dir, expected_page_files, failures):
    ok = True
    for slug, file_name in expected_page_files.items():
        if not (site_dir / file_name).exists():
            failures.append(f"Missing page file for slug {slug}: {file_name}")
            ok = False
    return ok


def check_routes(base_url, pages, failures, metrics):
    responsive = 0
    expected = 0
    for page in pages:
        slug = page.get("slug")
        if not slug:
            continue
        expected += 1
        route = "/" if slug == "home" else f"/{slug}.html"
        url = base_url.rstrip("/") + route
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read()
                if 200 <= response.status < 300 and len(body) > 500:
                    responsive += 1
                else:
                    failures.append(
                        f"Route {route} returned status {response.status} or short body"
                    )
        except (urllib.error.URLError, TimeoutError) as error:
            failures.append(f"Route {route} did not respond: {error}")

    metrics["expected_pages"] = expected
    metrics["responsive_routes"] = responsive
    return expected > 0 and responsive == expected


def check_content_coverage(blueprint, html_text, failures, metrics):
    expected_texts = collect_expected_texts(blueprint)
    normalized_html = normalize_text(html_text)
    matched = [
        text
        for text in expected_texts
        if normalize_text(text) and normalize_text(text) in normalized_html
    ]
    total = len(expected_texts)
    coverage = len(matched) / total if total else 1.0
    metrics["expected_texts"] = total
    metrics["matched_texts"] = len(matched)
    metrics["content_coverage"] = round(coverage, 4)

    identity_name = blueprint.get("identity", {}).get("name")
    if identity_name and normalize_text(identity_name) not in normalized_html:
        failures.append(f"Missing identity name in generated site: {identity_name}")

    home_headline = first_home_headline(blueprint)
    if home_headline and normalize_text(home_headline) not in normalized_html:
        failures.append(f"Missing home headline in generated site: {home_headline}")

    if coverage < CONTENT_COVERAGE_THRESHOLD:
        failures.append(
            f"Content coverage {coverage:.2f} below threshold {CONTENT_COVERAGE_THRESHOLD:.2f}"
        )
        return False
    return True


def collect_expected_texts(blueprint):
    texts = []
    identity = blueprint.get("identity", {})
    append_text(texts, identity.get("name"))
    append_text(texts, identity.get("tagline"))

    for page in blueprint.get("pages", []):
        append_text(texts, page.get("title"))
        for section in page.get("sections", []):
            append_text(texts, section.get("headline"))
            for cta in section.get("ctas", []):
                append_text(texts, cta.get("label"))
            for item in section.get("items", []):
                append_text(texts, item.get("title"))

    seen = set()
    unique = []
    for text in texts:
        normalized = normalize_text(text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(text)
    return unique


def append_text(texts, text):
    if isinstance(text, str) and text.strip():
        texts.append(text.strip())


def first_home_headline(blueprint):
    for page in blueprint.get("pages", []):
        if page.get("slug") != "home":
            continue
        for section in page.get("sections", []):
            headline = section.get("headline")
            if headline:
                return headline
    return None


def normalize_text(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = text.lower()
    text = text.replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def check_section_coverage(blueprint, combined_code, failures, metrics):
    section_ids = []
    for page in blueprint.get("pages", []):
        for section in page.get("sections", []):
            section_id = section.get("id")
            if section_id:
                section_ids.append(section_id)

    matched = 0
    for section_id in section_ids:
        if re.search(rf"\bid\s*=\s*['\"]{re.escape(section_id)}['\"]", combined_code):
            matched += 1

    total = len(section_ids)
    coverage = matched / total if total else 1.0
    metrics["expected_sections"] = total
    metrics["matched_section_ids"] = matched
    metrics["section_coverage"] = round(coverage, 4)

    if coverage < SECTION_COVERAGE_THRESHOLD:
        failures.append(
            f"Section id coverage {coverage:.2f} below threshold {SECTION_COVERAGE_THRESHOLD:.2f}"
        )
        return False
    return True


def check_palette_usage(design_plan, combined_code, failures, metrics):
    palette = [
        color.get("hex", "").lower()
        for color in design_plan.get("color_palette", [])
        if isinstance(color.get("hex"), str)
    ]
    lower_code = combined_code.lower()
    used = sorted({color for color in palette if color in lower_code})
    metrics["palette_colors_used"] = len(used)
    metrics["palette_colors_expected"] = len(palette)
    metrics["palette_colors_matched"] = used
    if len(used) < min(MIN_PALETTE_COLORS_USED, len(palette)):
        failures.append(
            f"Only {len(used)} design palette colors used; expected at least {MIN_PALETTE_COLORS_USED}"
        )
        return False
    return True


def check_font_usage(design_plan, combined_code, failures, metrics):
    typography = design_plan.get("typography", {})
    fonts = [
        typography.get("heading_font"),
        typography.get("body_font"),
        typography.get("accent_font"),
    ]
    lower_code = combined_code.lower()
    matched = [
        font
        for font in fonts
        if isinstance(font, str) and font.strip() and font.lower() in lower_code
    ]
    metrics["font_matches"] = len(matched)
    metrics["fonts_matched"] = matched
    if len(matched) < MIN_FONT_MATCHES:
        failures.append("No design-plan font names found in generated code")
        return False
    return True


def check_asset_coverage(blueprint, site_dir, combined_code, failures, metrics):
    asset_sections = []
    for page in blueprint.get("pages", []):
        page_file = "index.html" if page.get("slug") == "home" else f"{page.get('slug')}.html"
        page_code = read_text(site_dir / page_file)
        for section in page.get("sections", []):
            if section.get("asset_ideas"):
                asset_sections.append((section.get("id"), page_code))

    covered = 0
    for section_id, page_code in asset_sections:
        section_code = extract_section_code(page_code, section_id) or page_code
        if has_visual_signal(section_code):
            covered += 1

    total = len(asset_sections)
    coverage = covered / total if total else 1.0
    metrics["asset_sections"] = total
    metrics["covered_asset_sections"] = covered
    metrics["asset_coverage"] = round(coverage, 4)

    if total and coverage < ASSET_COVERAGE_THRESHOLD:
        failures.append(
            f"Asset coverage {coverage:.2f} below threshold {ASSET_COVERAGE_THRESHOLD:.2f}"
        )
        return False
    return True


def extract_section_code(page_code, section_id):
    if not section_id:
        return ""
    pattern = (
        r"<section\b[^>]*\bid\s*=\s*['\"]"
        + re.escape(section_id)
        + r"['\"][\s\S]*?</section>"
    )
    match = re.search(pattern, page_code, re.IGNORECASE)
    return match.group(0) if match else ""


def has_visual_signal(code):
    lower = code.lower()
    if any(tag in lower for tag in ["<svg", "<canvas", "<img"]):
        return True
    visual_terms = [
        "visual",
        "illustration",
        "asset",
        "mockup",
        "chart",
        "pattern",
        "icon",
        "map",
        "dashboard",
        "graphic",
    ]
    return any(term in lower for term in visual_terms)


def check_policy(combined_code, failures, metrics, framework="html_css"):
    lower = combined_code.lower()
    violations = []

    if framework == "html_css":
        framework_url_markers = [
            "bootstrap",
            "tailwind",
            "jquery",
            "react",
            "vue",
            "svelte",
        ]
    elif framework == "react_css":
        framework_url_markers = ["tailwind", "vue", "svelte", "jquery", "bootstrap"]
    elif framework == "react_tailwind":
        framework_url_markers = ["vue", "svelte", "jquery", "bootstrap"]
    elif framework == "solid_tailwind":
        framework_url_markers = ["react", "vue", "svelte", "jquery", "bootstrap"]
    else:
        framework_url_markers = []

    external_urls = re.findall(r"https?://[^'\"\s)]+", combined_code)
    for url in external_urls:
        lower_url = url.lower()
        if "fonts.googleapis.com" in lower_url or "fonts.gstatic.com" in lower_url:
            continue
        if re.search(r"\.(png|jpe?g|gif|webp|avif|mp4|webm|mov|svg)(\?|$)", lower_url):
            violations.append(f"Forbidden external media URL: {url}")
        if any(
            marker in lower_url
            for marker in ["unsplash", "pexels", "pixabay", "cdn.jsdelivr", "unpkg", "cdnjs"]
            + framework_url_markers
        ):
            violations.append(f"Forbidden external dependency URL: {url}")

    if framework == "html_css":
        framework_patterns = {
            "react script": r"<script\b[^>]+src\s*=\s*['\"][^'\"]*react[^'\"]*['\"]",
            "vue script": r"<script\b[^>]+src\s*=\s*['\"][^'\"]*vue[^'\"]*['\"]",
            "svelte script": r"<script\b[^>]+src\s*=\s*['\"][^'\"]*svelte[^'\"]*['\"]",
            "jquery script": r"<script\b[^>]+src\s*=\s*['\"][^'\"]*jquery[^'\"]*['\"]",
            "bootstrap stylesheet": r"<link\b[^>]+href\s*=\s*['\"][^'\"]*bootstrap[^'\"]*['\"]",
            "tailwind cdn": r"cdn\.tailwindcss\.com",
            "react import": r"\bimport\s+[^;]*\bfrom\s+['\"]react['\"]",
            "vue import": r"\bimport\s+[^;]*\bfrom\s+['\"]vue['\"]",
            "svelte import": r"\bimport\s+[^;]*\bfrom\s+['\"]svelte['\"]",
            "jquery import": r"\bimport\s+[^;]*\bfrom\s+['\"]jquery['\"]",
            "tailwind directive": r"@tailwind\b",
        }
        for label, pattern in framework_patterns.items():
            if re.search(pattern, lower, re.IGNORECASE):
                violations.append(f"Forbidden framework/library usage: {label}")
    # For framework != html_css the reference site IS a React/Solid/Tailwind
    # build, so framework names will legitimately appear in bundled JS/CSS.
    # We still keep the external-dependency-URL block above to prevent remote
    # CDN loading.

    metrics["policy_violations"] = violations
    metrics["policy_framework"] = framework
    if violations:
        failures.extend(violations)
        return False
    return True


def write_report(out_path, valid, checks, metrics, failures):
    report = {
        "valid": valid,
        "checks": checks,
        "metrics": metrics,
        "failures": failures,
    }
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
'''.strip() + "\n"
