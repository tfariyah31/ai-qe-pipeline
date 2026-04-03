"""

Interactive CLI to rate AI-generated Gherkin test cases using a Risk-Based model.

Usage:
    python scripts/rate_tests.py tests/test_cases/login.test_case.md

Output:
    ratings/login_ratings.json

Risk Score Formula:
    ((Impact * weights[0]) + (Freq * weights[1]) + (Prob * weights[2]) + (Dep * weights[3]) + (Assert * weights[4])) / sum(weights)

Priority Mapping:
    >= 4.5  -> P0  (@smoke)
    4.0-4.4 -> P1  (@smoke)
    3.0-3.9 -> P2
    < 3.0   -> Drop
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Tuple


# ── Config ────────────────────────────────────────────────────────────────────

RATING_DIMENSIONS = [
    {
        "id": "business_impact",
        "label": "Business Impact",
        "weight": 1.5,
        "hint": "How severe is the business harm if this scenario fails? (revenue, compliance, reputation)",
    },
    {
        "id": "frequency_of_use",
        "label": "Frequency of Use",
        "weight": 1.2,
        "hint": "How often do real users exercise this flow? (daily critical path vs. rare edge case)",
    },
    {
        "id": "failure_probability",
        "label": "Failure Probability",
        "weight": 1.3,
        "hint": "How likely is this to break? (complex logic, frequent changes, known flakiness)",
    },
    {
        "id": "dependency_impact",
        "label": "Dependency Impact",
        "weight": 1.0,
        "hint": "How many downstream systems or features break if this fails? (auth, payments, etc.)",
    },
    {
        "id": "assertion_specificity",
        "label": "Assertion Specificity",
        "weight": 0.5,
        "hint": "Are 'Then' steps precise enough to verify?",
    },
]

# Priority thresholds
PRIORITY_TIERS = [
    (4.5, "P0"),
    (4.0, "P1"),
    (3.0, "P2"),
]

# Smoke-eligible priorities
SMOKE_PRIORITIES = {"P0", "P1"}

VERDICTS = {
    "a": "approve",
    "r": "revise",
    "x": "reject",
}

COLORS = {
    "header": "\033[1;36m",
    "label":  "\033[1;33m",
    "dim":    "\033[2m",
    "ok":     "\033[1;32m",
    "warn":   "\033[1;31m",
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "blue":   "\033[1;34m",
    "purple": "\033[1;35m",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def c(color: str, text: str) -> str:
    """Wrap text in ANSI color code."""
    return COLORS.get(color, "") + text + COLORS["reset"]


def hr(char: str = "-", width: int = 65) -> str:
    return char * width


def resolve_priority(risk_score: float) -> str:
    """Map a risk score to a priority tier."""
    for threshold, priority in PRIORITY_TIERS:
        if risk_score >= threshold:
            return priority
    return "Drop"


def priority_color(priority: str) -> str:
    """Return a color key for a given priority label."""
    return {
        "P0":   "warn",
        "P1":   "warn",
        "P2":   "blue",
        "Drop": "dim",
    }.get(priority, "reset")


def prompt_score(dimension: Dict) -> Tuple[int, str]:
    """
    Prompt for a 1-5 score and optional critique note for one dimension.
    Returns (score, note).
    """
    print("\n  " + c("label", dimension["label"]))
    print("  " + c("dim", dimension["hint"]))

    while True:
        raw = input("  Score (1-5): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 5:
            score = int(raw)
            break
        print(c("warn", "  ! Enter a number from 1 to 5."))

    return score, ""  # note collected separately in overall tester notes


def prompt_verdict() -> str:
    """Prompt for approve / revise / reject verdict."""
    print("\n  " + c("label", "Verdict?"))
    print(
        "  " + c("ok",   "[a]") + " approve   "
        + c("warn", "[r]") + " revise    "
        + c("warn", "[x]") + " reject"
    )

    while True:
        raw = input("  Choice (a/r/x): ").strip().lower()
        if raw in VERDICTS:
            return VERDICTS[raw]
        print(c("warn", "  ! Enter a, r, or x."))


def prompt_tester_notes() -> str:
    """Prompt for free-text tester notes."""
    print("\n  " + c("label", "Tester Notes"))
    print("  " + c("dim", "What did the AI miss? What would you add or change?"))
    return input("  > ").strip()


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_scenarios(md_path: str) -> List[Dict]:
    """
    Parse a Gherkin .md file into a list of scenario dicts.
    Each dict has keys: id, title, raw_text.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = re.split(r"(?=\n\s*Scenario[:\s])", content)

    scenarios = []
    counter = 1

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        match = re.search(r"Scenario(?:\s+Outline)?:\s*(.+)", stripped)
        if not match:
            continue

        title = match.group(1).strip()
        scenarios.append({
            "id": "TC" + str(counter).zfill(3),
            "title": title,
            "raw_text": stripped,
        })
        counter += 1

    return scenarios


# ── Core rating loop ──────────────────────────────────────────────────────────
def rate_scenario(scenario: Dict, index: int, total: int) -> Dict:
    """
    Interactive risk-based rating session for a single scenario.
    Returns a completed rating dict.
    """
    header = "  [{}/{}]  {} - {}".format(index, total, scenario["id"], scenario["title"])
    print("\n" + hr())
    print(c("header", header))
    print(hr())
    print()

    for line in scenario["raw_text"].splitlines():
        print("  " + c("dim", line))

    print("\n" + hr("."))
    print(c("bold", "  Rate the following (1–5):"))

    dimension_ratings: Dict = {}
    for dim in RATING_DIMENSIONS:
        score, _ = prompt_score(dim)
        dimension_ratings[dim["id"]] = {"score": score}

    # Compute Weighted Risk Score
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for dim in RATING_DIMENSIONS:
        score = dimension_ratings[dim["id"]]["score"]
        weight = dim.get("weight", 1.0)
        total_weighted_score += (score * weight)
        total_weight += weight

    risk_score = round(total_weighted_score / total_weight, 2)
    priority = resolve_priority(risk_score)
    
    # Show computed result before asking for verdict
    print("\n  " + hr("."))
    p_color = priority_color(priority)
    
    # Note: We determine tags AFTER the verdict is collected
    print(
        "  " + c("bold", "Rate Score : ") + c("ok", str(risk_score))
        + "   " + c("bold", "Priority : ") + c(p_color, priority)
    )
    print("  " + c("dim", _priority_explanation(priority)))

    verdict = prompt_verdict()
    tester_notes = prompt_tester_notes()

    # --- TAG ASSIGNMENT LOGIC ---
    is_smoke = priority in SMOKE_PRIORITIES
    smoke_tag = "@smoke" if is_smoke else None
    
    # Regression tag for P2 only if approved
    regression_tag = None
    if priority == "P2" and verdict == "approve":
        regression_tag = "@regression"

    return {
        "test_id":        scenario["id"],
        "title":          scenario["title"],
        "rated_at":       datetime.now().isoformat(timespec="seconds"),
        "dimensions":     dimension_ratings,
        "risk_score":     risk_score,
        "priority":       priority,
        "smoke_tag":      smoke_tag,
        "regression_tag": regression_tag,  # Added to dictionary
        "verdict":        verdict,
        "tester_notes":   tester_notes,
    }


def _priority_explanation(priority: str) -> str:
    return {
        "P0":   "Critical — must pass in every smoke run.",
        "P1":   "High — included in smoke pipeline.",
        "P2":   "Medium — regression suite only.",
        "Drop": "Low risk — drop from suite or demote to exploratory.",
    }.get(priority, "")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(ratings: List[Dict]) -> None:
    """
    Print a risk-based summary table after all scenarios are rated.
    Includes logic for @smoke (P0/P1) and @regression (P2 Approved) tags.
    """
    print("\n" + hr("="))
    print(c("header", "  TestMart — Risk-Based Rating Summary"))
    print(hr("="))

    verdict_counts: Dict[str, int] = {"approve": 0, "revise": 0, "reject": 0}
    priority_counts: Dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "Drop": 0}
    smoke_tests: List[str] = []
    regression_tests: List[str] = []

    for r in ratings:
        verdict_counts[r["verdict"]] += 1
        priority_counts[r["priority"]] += 1
        if r.get("smoke_tag"):
            smoke_tests.append("{} {}".format(r["test_id"], r["title"][:40]))

        if r.get("regression_tag"):
            regression_tests.append(f"{r['test_id']} {r['title'][:40]}")

    # Table header
    col_id      = "Test ID".ljust(8)
    col_title   = "Title".ljust(42)
    col_risk    = "Risk".rjust(5)
    col_pri     = "Priority".ljust(10)
    col_smoke   = "Smoke".ljust(7)
    col_verdict = "Verdict"
    print("\n  " + col_id + "  " + col_title + "  " + col_risk + "  " + col_pri + col_smoke + col_verdict)
    print("  " + hr("-", 78))

    for r in ratings:
        p_color     = priority_color(r["priority"])
        v_color     = "ok" if r["verdict"] == "approve" else "warn"

        # Tag display logic
        tag_display = ""
        if r.get("smoke_tag"):
            tag_display = c("purple", "@smoke")
        elif r.get("regression_tag"):
            tag_display = c("blue", "@regress")
        else:
            tag_display = c("dim", "---")

        print(
            "  "
            + r["test_id"].ljust(8) + "  "
            + r["title"][:41].ljust(42) + "  "
            + str(r["risk_score"]).rjust(5) + "  "
            + c(p_color, r["priority"]).ljust(10 + 9)   # +9 for ANSI escape chars
            + tag_display.ljust(10 + 9)                 # +9 for ANSI escape chars
            + c(v_color, r["verdict"])
        )

    # Aggregate stats
    all_scores = [r["risk_score"] for r in ratings]
    overall_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0

    print("\n  " + hr("."))
    print("  " + c("bold",   "Overall avg risk score : ") + str(overall_avg))
    print("  " + c("warn",   "P0 (Critical)          : ") + str(priority_counts["P0"]))
    print("  " + c("warn",   "P1 (High)              : ") + str(priority_counts["P1"]))
    print("  " + c("blue",   "P2 (Medium)            : ") + str(priority_counts["P2"]))
    print("  " + c("dim",    "Drop                   : ") + str(priority_counts["Drop"]))
    print("  " + c("ok",     "Approved               : ") + str(verdict_counts["approve"]))
    print("  " + c("warn",   "Needs revision         : ") + str(verdict_counts["revise"]))
    print("  " + c("warn",   "Rejected               : ") + str(verdict_counts["reject"]))

    if smoke_tests:
        print("\n  " + c("purple", "@smoke pipeline ({} tests):".format(len(smoke_tests))))
        for t in smoke_tests:
            print("    " + c("purple", "✓") + "  " + t)


    # Show Regression Pipeline
    if regression_tests:
        print("\n  " + c("blue", f"@regression suite ({len(regression_tests)} tests):"))
        for t in regression_tests:
            print("    " + c("blue", "✓") + "  " + t)

# ── Output ────────────────────────────────────────────────────────────────────

def save_ratings(ratings: List[Dict], input_path: str) -> str:
    """
    Write ratings to ratings/<stem>_ratings.json.
    Returns the output file path.
    """
    os.makedirs("ratings", exist_ok=True)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    stem = re.sub(r"\.(test_case|tests?)$", "", stem)
    output_path = os.path.join("ratings", stem + "_ratings.json")

    smoke_tests = [
        {"test_id": r["test_id"], "title": r["title"], "risk_score": r["risk_score"]}
        for r in ratings
        if r.get("smoke_tag")
    ]

    payload = {
        "source_file":      input_path,
        "generated_at":     datetime.now().isoformat(timespec="seconds"),
        "total_scenarios":  len(ratings),
        "smoke_pipeline": {
            "tag":   "@smoke",
            "count": len(smoke_tests),
            "tests": smoke_tests,
        },
        "ratings": ratings,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return output_path


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(c("warn", "Usage: python scripts/rate_tests.py <path_to_test_case.md>"))
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(c("warn", "! File not found: " + input_path))
        sys.exit(1)

    print("\n" + hr("="))
    print(c("header", "  TestMart —  Risk-Based Test Rater"))
    print(hr("="))
    print("\n  File   : " + c("blue", input_path))

    scenarios = parse_scenarios(input_path)

    if not scenarios:
        print(c("warn", "\n! No Gherkin scenarios found. Check file format."))
        sys.exit(1)

    print("  Scenarios found : " + c("bold", str(len(scenarios))))
    print("\n  Risk dimensions you will rate:")
    for dim in RATING_DIMENSIONS:
        print("    - " + dim["label"])

    print("\n  " + c("bold", "Priority tiers:"))
    print("    " + c("warn",   "≥ 4.5  → P0   @smoke  (Critical)"))
    print("    " + c("warn",   "4.0–4.4 → P1   @smoke  (High)"))
    print("    " + c("blue",   "3.0–3.9 → P2   @regression  (Medium)"))
    print("    " + c("dim",    "< 3.0   → Drop   (Deprioritise)"))

    print("\n  " + c("dim", "Press Ctrl+C at any time to exit without saving."))
    input("\n  " + c("bold", "Press Enter to start rating..."))

    ratings: List[Dict] = []

    try:
        for i, scenario in enumerate(scenarios, start=1):
            rating = rate_scenario(scenario, i, len(scenarios))
            ratings.append(rating)

            p_color = priority_color(rating["priority"])
            v_color = "ok" if rating["verdict"] == "approve" else "warn"
            smoke_note = " " + c("purple", "@smoke") if rating.get("smoke_tag") else ""
            print(
                "\n  " + c(v_color, "✓ Saved: ")
                + rating["test_id"] + " — "
                + c(p_color, rating["priority"])
                + smoke_note
                + "  risk=" + str(rating["risk_score"])
                + "  verdict=" + c(v_color, rating["verdict"].upper())
            )

    except KeyboardInterrupt:
        print(c("warn", "\n\n  Interrupted. Ratings collected so far will be saved."))

    if not ratings:
        print(c("warn", "\n  No ratings to save. Exiting."))
        sys.exit(0)

    print_summary(ratings)

    output_path = save_ratings(ratings, input_path)
    print("\n  " + c("ok", "Saved") + " → " + c("blue", output_path))
    print("\n  Next step: python scripts/enrich_tests.py " + output_path)
    print("\n" + hr("=") + "\n")


if __name__ == "__main__":
    main()