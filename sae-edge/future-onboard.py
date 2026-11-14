#!/usr/bin/env python3
"""SAE EDGE CORE future repository enroller. No merges, deployments or routing."""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OWNER = "pergolessi9-star"
BRANCH = "chore/sae-edge-catalog"
PORTAL = "https://sae-edge-core-30.pages.dev/"
UA = "SAE-EDGE-CORE-Federation/1.0"

def api(token, method, path, payload=None):
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        body = e.read(300).decode("utf-8", "replace")
        raise RuntimeError(f"GitHub HTTP {e.code} on {method} {path}: {body}") from e

def catalog_manifest(full_name):
    return {"schema_version": 1, "repository": full_name,
            "control_plane_url": PORTAL,
            "gateway": {"mode": "catalog-only", "enabled": False, "origin": None}}

def workflow_text():
    return """name: SAE EDGE CORE policy
on:
  pull_request:
    paths: ['.sae/edge-core.json', '.github/workflows/sae-edge-core.yml']
  workflow_dispatch:
permissions: {contents: read}
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      - name: Validate inactive enrollment
        run: |
          python3 - <<'PY'
          import json,os
          j=json.load(open('.sae/edge-core.json'))
          assert j['schema_version']==1 and j['repository']==os.environ['GITHUB_REPOSITORY']
          assert j['control_plane_url']=='https://sae-edge-core-30.pages.dev/'
          assert j['gateway']=={'mode':'catalog-only','enabled':False,'origin':None}
          print('PASS: no active gateway routes')
          PY
"""

def list_owned(token):
    for page in range(1, 21):
        rows = api(token, "GET", f"/user/repos?affiliation=owner&per_page=100&page={page}")
        if not isinstance(rows, list):
            raise RuntimeError("Could not list authenticated repositories")
        for row in rows:
            if row.get("owner", {}).get("login") == OWNER:
                yield row
        if len(rows) < 100:
            break

def existing_pr(token, full_name):
    items = api(token, "GET", f"/repos/{full_name}/pulls?state=open&per_page=100&head={OWNER}:{urllib.parse.quote(BRANCH, safe='')}")
    return any(x.get("head", {}).get("ref") == BRANCH for x in (items or []))

def create_file(token, full_name, path, branch, text):
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return api(token, "PUT", f"/repos/{full_name}/contents/{path}",
               {"message": "chore(sae): enroll catalog-only, no gateway routes", "content": encoded, "branch": branch})

def enroll(token, repo, apply):
    full_name = repo["full_name"]
    default = repo.get("default_branch")
    if full_name == f"{OWNER}/workflows-starter-template":
        return "controller"
    if repo.get("archived") or repo.get("disabled") or repo.get("size", 0) == 0 or not default:
        return "skip-inactive-or-empty"
    ref = urllib.parse.quote(default, safe="")
    exists = api(token, "GET", f"/repos/{full_name}/contents/.sae/edge-core.json?ref={ref}")
    if exists is not None:
        return "already-onboarded"
    if existing_pr(token, full_name):
        return "draft-pr-exists"
    if not apply:
        return "would-open-draft-pr"
    head = api(token, "GET", f"/repos/{full_name}/git/ref/heads/{ref}")
    if not head or not head.get("object", {}).get("sha"):
        return "blocked-no-default-head"
    branch_ref = api(token, "GET", f"/repos/{full_name}/git/ref/heads/{urllib.parse.quote(BRANCH, safe='')}")
    if branch_ref is None:
        api(token, "POST", f"/repos/{full_name}/git/refs",
            {"ref": "refs/heads/" + BRANCH, "sha": head["object"]["sha"]})
    manifest = json.dumps(catalog_manifest(full_name), ensure_ascii=False, indent=2) + "\n"
    on_branch = api(token, "GET", f"/repos/{full_name}/contents/.sae/edge-core.json?ref={urllib.parse.quote(BRANCH, safe='')}")
    if on_branch is None:
        create_file(token, full_name, ".sae/edge-core.json", BRANCH, manifest)
    wf_exists = api(token, "GET", f"/repos/{full_name}/contents/.github/workflows/sae-edge-core.yml?ref={urllib.parse.quote(BRANCH, safe='')}")
    if wf_exists is None:
        create_file(token, full_name, ".github/workflows/sae-edge-core.yml", BRANCH, workflow_text())
    pr = api(token, "POST", f"/repos/{full_name}/pulls",
             {"title": "SAE EDGE CORE — alta federada (sin tráfico)", "head": BRANCH,
              "base": default, "draft": True,
              "body": "Catalog-only enrollment. No origin, gateway disabled, no secrets, no production changes. Never auto-merge."})
    return "created-draft-pr " + str(pr.get("html_url", ""))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Create draft PRs; defaults to read-only")
    args = parser.parse_args()
    token = os.environ.get("SAE_FEDERATION_TOKEN", "")
    if not token:
        print("SAE_FEDERATION_TOKEN is absent: cross-repository automation is inactive.")
        return 0
    counts = {}
    for repo in list_owned(token):
        try:
            status = enroll(token, repo, args.apply)
        except Exception as exc:
            status = "ERROR " + str(exc)[:250]
        counts[status.split(" ", 1)[0]] = counts.get(status.split(" ", 1)[0], 0) + 1
        print(repo["full_name"] + ": " + status)
    print("SUMMARY " + json.dumps(counts, sort_keys=True))
    return 1 if "ERROR" in counts else 0

if __name__ == "__main__":
    sys.exit(main())
