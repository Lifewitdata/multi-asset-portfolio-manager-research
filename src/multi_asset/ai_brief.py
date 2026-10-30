"""Manual AI research workflow: exact typed facts plus mandatory human interpretation review."""
import argparse
import json
from pathlib import Path
from .config import ROOT

def validate(response, evidence):
    if not isinstance(response,dict) or set(response)!={"claims"} or not isinstance(response["claims"],list):
        raise ValueError("Expected an object containing claims list only")
    seen=set()
    for claim in response["claims"]:
        if not isinstance(claim,dict) or set(claim)!={"metric_key","value","explanation"}:
            raise ValueError("Each claim needs metric_key, value, explanation")
        key=claim["metric_key"]
        if not isinstance(key,str) or key not in evidence or key in seen:
            raise ValueError("Unknown or duplicate metric key")
        if type(claim["value"]) is not type(evidence[key]) or claim["value"]!=evidence[key]:
            raise ValueError(f"Wrong value or type: {key}")
        if not isinstance(claim["explanation"],str) or not claim["explanation"].strip():
            raise ValueError("Explanation must be nonempty text")
        seen.add(key)
    if seen!=set(evidence):raise ValueError("Missing evidence keys")
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--response",type=Path)
    args=parser.parse_args()
    folder=ROOT/"reports/local"
    facts=json.loads((folder/"research_facts.json").read_text())
    if args.response:
        response=json.loads(args.response.read_text(encoding="utf-8-sig"))
        validate(response,facts)
        print("Exact facts and types passed. Human review of explanations is still required.")
    else:
        prompt='Explain these historical research facts. No investment advice, invented findings, or manager-skill claims. Return JSON only: {"claims":[{"metric_key":"existing key","value":"exact typed evidence value","explanation":"plain English"}]}. Include every evidence key exactly once. Evidence: '+json.dumps(facts)
        (folder/"ai_prompt.txt").write_text(prompt)
        print("Evidence prompt written to reports/local/ai_prompt.txt. No AI API called.")

if __name__=="__main__":main()
