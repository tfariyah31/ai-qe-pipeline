"""

Reads login_ratings.json and the original test case .md, then produces
.enriched.md — filtered (rejects dropped), tagged, and prioritized.

Usage:
    python scripts/enrich_tests.py ratings/login_ratings.json \
                                   tests/test_cases/login.test_case.md

Output:
    tests/test_cases/login.enriched.md
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ── Tag + priority logic ──────────────────────────────────────────────────────

# Keywords in scenario titles/text that signal a tag
TAG_RULES: List[Tuple[str, str]] = [
    # (regex pattern, tag to apply)
    (r"successful.{0,20}login|happy.path|valid.credential", "@smoke"),
    (r"invalid.credential|wrong.password|incorrect.password",  "@smoke"),
    (r"lockout|lock.{0,5}account|failed.attempt",              "@regression"),
    (r"merchant|super.admin|customer.role|role.{0,10}access",  "@regression"),
    (r"unauthori[sz]|redirect|protected.route|direct.navig",   "@smoke"),
    (r"rate.limit|brute.force|throttl",                        "@regression"),
    (r"refresh.token|token.expir|jwt",                         "@regression"),
    (r"xss|injection|helmet|header",                           "@regression"),
]

DOMAIN_TAG_RULES: List[Tuple[str, str]] = [
    (r"login|credential|password|logout",                      "@auth"),
    (r"lockout|rate.limit|brute|xss|injection|helmet|security", "@security"),
    (r"merchant|admin|customer|role|rbac|permission|access",   "@rbac"),
    (r"token|jwt|refresh|session",                             "@jwt"),
]

# Priority based on risk_score thresholds + business risk signals
PRIORITY_RULES: List[Tuple[str, str, str]] = [
    # (scope_tag, domain_tag_pattern, priority)
    # P0 = must pass on every deploy
    (r"@smoke",      r"@security|@auth|@rbac", "P0"),
    (r"@smoke",      r".*",                    "P0"),
    # P1 = release gate
    (r"@regression", r"@security|@rbac",       "P1"),
    (r"@regression", r"@jwt",                  "P1"),
    # P2 = important but not blocking
    (r"@regression", r".*",                    "P2"),
]

SCORE_PRIORITY_BOOST = {
    # If risk_score <= threshold, bump priority one level (P1->P0, P2->P1)
    "threshold": 2.5,
}


def infer_scope_tag(text: str) -> str:
    """Return @smoke or @regression based on scenario text."""
    lower = text.lower()
    for pattern, tag in TAG_RULES:
        if re.search(pattern, lower):
            return tag
    return "@regression"  # safe default


def infer_domain_tags(text: str) -> List[str]:
    """Return all matching domain tags for the scenario text."""
    lower = text.lower()
    tags = []
    for pattern, tag in DOMAIN_TAG_RULES:
        if re.search(pattern, lower) and tag not in tags:
            tags.append(tag)
    return tags if tags else ["@auth"]


def infer_priority(scope_tag: str, domain_tags: List[str], risk_score: float) -> str:
    """Derive P0/P1/P2 from scope, domain tags, and quality score."""
    domain_str = " ".join(domain_tags)
    priority = "P2"

    for scope_pattern, domain_pattern, p in PRIORITY_RULES:
        if re.search(scope_pattern, scope_tag) and re.search(domain_pattern, domain_str):
            priority = p
            break

    # Low quality score = higher business risk = bump priority
    if avg_score <= SCORE_PRIORITY_BOOST["threshold"]:
        if priority == "P2":
            priority = "P1"
        elif priority == "P1":
            priority = "P0"

    return priority


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_scenarios(md_path: str) -> Dict[str, Dict]:
    """
    Parse Gherkin .md into a dict keyed by zero-padded index string.
    Matches the TC001..TCN IDs assigned by rate_tests.py.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = re.split(r"(?=\n\s*Scenario[:\s])", content)
    scenarios: Dict[str, Dict] = {}
    counter = 1

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        match = re.search(r"Scenario(?:\s+Outline)?:\s*(.+)", stripped)
        if not match:
            continue
        tc_id = "TC" + str(counter).zfill(3)
        scenarios[tc_id] = {
            "id": tc_id,
            "title": match.group(1).strip(),
            "raw_text": stripped,
        }
        counter += 1

    return scenarios


def load_ratings(ratings_path: str) -> List[Dict]:
    with open(ratings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ratings"]


# ── Enrichment ────────────────────────────────────────────────────────────────

def enrich(scenario: Dict, rating: Dict) -> Optional[Dict]:
    """
    Combine scenario + rating into a single enriched record.
    Uses the weighted risk_score and tags from the rating session.
    Returns None for rejected scenarios (they are dropped).
    """
    if rating["verdict"] == "reject":
        return None
    
    current_risk_score = rating.get("risk_score", 0.0)
    full_text = scenario["raw_text"]
    combined_text = scenario["title"] + " " + full_text

    # Prioritize manual tags from rating session
    if rating.get("smoke_tag"):
        scope_tag = rating["smoke_tag"]
    elif rating.get("regression_tag"):
        scope_tag = rating["regression_tag"]
    else:
        scope_tag = infer_scope_tag(combined_text)

    domain_tags = infer_domain_tags(combined_text)
    priority = rating.get("priority", "P2")
    all_tags = [scope_tag] + domain_tags

    return {
        "id":           scenario["id"],
        "title":        scenario["title"],
        "verdict":      rating["verdict"],
        "risk_score":   current_risk_score,
        "priority":     priority,
        "tags":         all_tags,
        "tester_notes": rating.get("tester_notes", ""), # Maps to the rating's note
        "dimensions":   rating.get("dimensions", {}),
        "raw_text":     full_text,
    }


# ── Markdown writer ───────────────────────────────────────────────────────────

def build_enriched_md(enriched_scenarios: List[Dict], source_md: str, ratings_path: str) -> str:
    """
    Render enriched scenarios as a tagged, prioritized Gherkin markdown file.
    Uses risk_score and tester_notes from the weighted rating session.
    """

    lines: List[str] = []

    lines.append("# Enriched Test Cases")
    lines.append("")
    lines.append("> **Generated by:** `enrich_tests.py`  ")
    lines.append("> **Source tests:** `" + source_md + "`  ")
    lines.append("> **Ratings file:** `" + ratings_path + "`  ")
    lines.append("> **Enriched at:** " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| ID | Title | Priority | Tags | Score | Verdict |")
    lines.append("|---|---|---|---|---|---|")
    for s in enriched_scenarios:
        tags_str = " ".join(s["tags"])
        lines.append(
            "| " + s["id"]
            + " | " + s["title"]
            + " | **" + s["priority"] + "**"
            + " | `" + tags_str + "`"
            + " | " + f"{s['risk_score']:.2f}"
            + " | " + s["verdict"]
            + " |"
        )
    lines.append("")

    # Individual scenarios
    lines.append("---")
    lines.append("")
    lines.append("## Test Scenarios")
    lines.append("")

    for s in enriched_scenarios:
        tags_inline = " ".join(s["tags"])
        priority    = s["priority"]

        lines.append("### " + s["id"] + " — " + s["title"])
        lines.append("")
        lines.append("**Priority:** `" + priority + "`  ")
        lines.append("**Tags:** `" + tags_inline + "`  ")
        lines.append("**Quality score:** " + f"{s['risk_score']:.2f}" + " / 5  ")
        lines.append("**Verdict:** " + s["verdict"])
        lines.append("")

        # Dimension scores
        lines.append("<details>")
        lines.append("<summary>Rating breakdown</summary>")
        lines.append("")
        lines.append("| Dimension | Score | Note |")
        lines.append("|---|---|---|")
        for dim_id, dim_data in s["dimensions"].items():
            label = dim_id.replace("_", " ").title()
            note  = dim_data.get("note", "—") if dim_data.get("note") else "—"
            lines.append("| " + label + " | " + str(dim_data["score"]) + " / 5 | " + note + " |")
        lines.append("")

        if s["tester_notes"]:
            lines.append("> **Tester note:** " + s["tester_notes"])
            lines.append("")

        lines.append("</details>")
        lines.append("")

        # Tag header lines above the Gherkin block
        lines.append("```gherkin")
        lines.append("# Priority: " + priority)
        for tag in s["tags"]:
            lines.append(tag)
        lines.append(s["raw_text"])
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ── Output path ───────────────────────────────────────────────────────────────

def resolve_output_path(source_md: str) -> str:
    """
    Place output next to the source file with .enriched.md suffix.
    e.g. tests/test_cases/login.test_case.md
      -> tests/test_cases/login.enriched.md
    """
    directory  = os.path.dirname(source_md)
    basename   = os.path.basename(source_md)
    stem       = re.sub(r"\.(test_case|tests?|md)$", "", basename, flags=re.IGNORECASE)
    stem       = stem.rstrip(".")
    output     = os.path.join(directory, stem + ".enriched.md")
    return output


# ── CLI ───────────────────────────────────────────────────────────────────────

COLORS = {
    "header": "\033[1;36m",
    "ok":     "\033[1;32m",
    "warn":   "\033[1;31m",
    "blue":   "\033[1;34m",
    "dim":    "\033[2m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}


def c(color: str, text: str) -> str:
    return COLORS.get(color, "") + text + COLORS["reset"]


def hr(char: str = "-", width: int = 65) -> str:
    return char * width


def main() -> None:
    if len(sys.argv) < 3:
        print(c("warn", "Usage: python scripts/enrich_tests.py <ratings.json> <test_case.md>"))
        print(c("dim",  "  e.g. python scripts/enrich_tests.py ratings/login_ratings.json tests/test_cases/login.test_case.md"))
        sys.exit(1)

    ratings_path = sys.argv[1]
    source_md    = sys.argv[2]

    for path in [ratings_path, source_md]:
        if not os.path.exists(path):
            print(c("warn", "! File not found: " + path))
            sys.exit(1)

    print("\n" + hr("="))
    print(c("header", "  TestMart - Test Enricher"))
    print(hr("="))
    print("  Ratings : " + c("blue", ratings_path))
    print("  Source  : " + c("blue", source_md))

    ratings  = load_ratings(ratings_path)
    scenarios = parse_scenarios(source_md)

    print("\n  Scenarios in ratings file : " + str(len(ratings)))
    print("  Scenarios parsed from md  : " + str(len(scenarios)))

    # Align by index (TC001 ... TCN)
    enriched_scenarios: List[Dict] = []
    skipped: List[str] = []

    for rating in ratings:
        tc_id    = rating["test_id"]
        scenario = scenarios.get(tc_id)

        if scenario is None:
            print(c("warn", "  ! " + tc_id + " not found in source md — skipping"))
            continue

        result = enrich(scenario, rating)

        if result is None:
            skipped.append(tc_id + " (" + scenario["title"][:40] + ")")
        else:
            enriched_scenarios.append(result)

    print("\n  " + hr("."))
    print("  Approved / Revise : " + c("ok",   str(len(enriched_scenarios))) + " scenarios kept")
    print("  Rejected (dropped): " + c("warn", str(len(skipped))))
    for s in skipped:
        print("    - " + s)

    if not enriched_scenarios:
        print(c("warn", "\n  Nothing to enrich. Check your ratings file."))
        sys.exit(1)

    # Print enrichment decisions
    print("\n  " + hr("."))
    print("  Enrichment decisions:\n")
    print("  " + "ID".ljust(7) + "  " + "Priority".ljust(10) + "  " + "Tags".ljust(38) + "  Score")
    print("  " + hr("-", 72))
    for s in enriched_scenarios:
        tags_str = " ".join(s["tags"])
        print(
            "  " + s["id"].ljust(7)
            + "  " + s["priority"].ljust(10)
            + "  " + tags_str.ljust(38)
            + "  " + f"{s['risk_score']:.2f}"
        )

    # Write output
    md_content  = build_enriched_md(enriched_scenarios, source_md, ratings_path)
    output_path = resolve_output_path(source_md)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n  " + c("ok", "Saved") + " -> " + c("blue", output_path))
    print("\n  Next step: python scripts/finalize_tests.py " + output_path)
    print("\n" + hr("=") + "\n")


if __name__ == "__main__":
    main()