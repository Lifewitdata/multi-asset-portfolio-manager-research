"""Check the AI-drafted field mapping in docs/ai_field_mapping.md against docs/field_catalog.csv.

The draft is recorded as a fenced JSON block inside the Markdown, so the document stays the single
source of truth. This script recomputes each proposal's verdict from the catalog and refuses when
the recorded review disagrees with it, when a proposal cites a field the catalog does not hold, or
when a corrected proposal carries no correction text.

Usage: python scripts/check_field_mapping.py [--json]
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/field_catalog.csv"
DOC = ROOT / "docs/ai_field_mapping.md"
ATTRIBUTES = {"source": "source", "formula": "formula", "units": "units", "null_rule": "null_rule"}
# Units are compared verbatim: a stated unit is a claim about scale, and "USD per share" quietly
# standing in for "USD per share, split/distribution adjusted" is how an unadjusted price slips in.
EXACT = {"units"}
ALLOWED_VERDICTS = {"accepted", "corrected", "unknown_field"}


def normalise(text):
    if text is None:
        return ""
    text = unicodedata.normalize("NFKC", str(text)).replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(text.strip().lower().split())


def catalog_rows():
    import pandas as pd
    frame = pd.read_csv(CATALOG, keep_default_na=False)
    return {(r["dataset"], r["field"]): r for r in frame.to_dict("records")}


def draft_proposals():
    for block in re.findall(r"```json\n(.*?)\n```", DOC.read_text(encoding="utf-8"), flags=re.DOTALL):
        if '"proposals"' in block:
            return json.loads(block)["proposals"]
    raise ValueError(f"No JSON proposal block found in {DOC.name}")


def agrees(proposed, authoritative, exact):
    proposed, authoritative = normalise(proposed), normalise(authoritative)
    if not proposed:
        return False
    return proposed == authoritative if exact else proposed in authoritative or authoritative in proposed


def evaluate(proposal, reference):
    """Return (verdict, mismatched attributes) computed from the catalog alone."""
    if reference is None:
        return "unknown_field", []
    mismatches = [key for key, column in ATTRIBUTES.items()
                  if not agrees(proposal.get(key, ""), reference[column], key in EXACT)]
    return ("accepted", []) if not mismatches else ("corrected", mismatches)


def check():
    references, problems, rows = catalog_rows(), [], []
    for proposal in draft_proposals():
        reference = references.get((proposal["dataset"], proposal["field"]))
        verdict, mismatches = evaluate(proposal, reference)
        if verdict != proposal["reviewed_as"]:
            problems.append(f"{proposal['id']}: catalog says {verdict}, the review records {proposal['reviewed_as']}")
        if verdict != "accepted":
            if not proposal.get("correction", "").strip():
                problems.append(f"{proposal['id']}: {verdict} but no correction text")
            if not proposal.get("catalog_reference", "").strip():
                problems.append(f"{proposal['id']}: {verdict} but no catalog reference")
        if verdict == "unknown_field":
            mismatches = ["field is not in the catalog"]
        rows.append({"id": proposal["id"], "dataset": proposal["dataset"], "field": proposal["field"],
                     "verdict": verdict, "mismatched": mismatches,
                     "correction": proposal.get("correction", "")})
    return rows, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="Print verdicts as JSON.")
    args = parser.parse_args()
    rows, problems = check()
    if args.json:
        print(json.dumps({"proposals": rows, "problems": problems}, indent=2))
    else:
        widths = max(len(f"{r['dataset']},{r['field']}") for r in rows)
        for r in rows:
            print(f"{r['id']}  {(r['dataset'] + ',' + r['field']):<{widths}}  {r['verdict']:<13}  "
                  f"{', '.join(r['mismatched']) or '-'}")
        counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in ALLOWED_VERDICTS}
        print(f"\n{len(rows)} proposals: {counts['accepted']} accepted, {counts['corrected']} corrected, "
              f"{counts['unknown_field']} unknown to the catalog.")
    if problems:
        for problem in problems:
            print(f"PROBLEM: {problem}", file=sys.stderr)
        raise SystemExit(1)
    print("Review matches the catalog.")


if __name__ == "__main__":
    main()
