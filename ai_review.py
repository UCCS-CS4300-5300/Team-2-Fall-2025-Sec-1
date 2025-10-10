# ai_review.py
import os
import sys
import subprocess
from pathlib import Path

from github import Github            # pip install PyGithub
from openai import OpenAI            # pip install openai


MAX_DIFF_BYTES = 60_000  # keep payload modest for the model
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def run(cmd: list[str]) -> str:
    """Run a shell command and return stdout as str (raise on failure)."""
    out = subprocess.check_output(cmd)
    return out.decode("utf-8", errors="ignore").strip()


def build_pr_diff(base_ref_env: str | None) -> str:
    """
    Compute a unified diff between PR HEAD and the merge-base with the PR's base branch.
    Requires actions/checkout with fetch-depth: 0.
    """
    base_ref = base_ref_env or "main"
    # Ensure we have the base ref locally
    subprocess.run(["git", "fetch", "origin", base_ref], check=True)
    merge_base = run(["git", "merge-base", "HEAD", f"origin/{base_ref}"])
    diff_bytes = subprocess.check_output(["git", "diff", "--unified=0", f"{merge_base}...HEAD"])
    if len(diff_bytes) > MAX_DIFF_BYTES:
        diff_bytes = diff_bytes[:MAX_DIFF_BYTES] + b"\n\n[...diff truncated for length...]\n"
    diff_text = diff_bytes.decode("utf-8", errors="ignore")
    return diff_text or "[No changes detected in diff.]"


def make_prompt(diff: str) -> str:
    return f"""
You are a strict senior reviewer. Given a unified git diff, produce:

1) Top risks (security/auth/secrets/injections, unsafe regex/file I/O, deserialization, SSRF, etc.).
2) Correctness & edge cases (null/None, off-by-one, race conditions, error handling).
3) Performance hot spots / complexity (N^2 loops, unnecessary I/O, DB queries).
4) Missing tests (suggest test names + intent: unit vs integration).
5) Concrete, line-anchored notes using the format "path:line -> comment".

Only comment on things visible in the diff. Be concise and actionable.

DIFF START
{diff}
DIFF END
""".strip()


def call_openai(prompt: str, api_key: str, model: str = DEFAULT_MODEL) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(model=model, input=prompt)
    # Prefer the SDK's text helper when available
    text = getattr(resp, "output_text", None)
    if not text:
        # Fallback: concatenate any text segments if the helper isn't present
        try:
            parts = []
            for block in (resp.output or []):
                if isinstance(block, dict) and block.get("type") == "output_text":
                    parts.append(block.get("text", ""))
            text = "".join(parts)
        except Exception:
            text = ""
    return text.strip() or "No findings."


def post_pr_comment(gh_token: str, repo_full: str, pr_number: int, body: str) -> None:
    gh = Github(gh_token)
    repo = gh.get_repo(repo_full)
    pr = repo.get_pull(pr_number)
    pr.create_issue_comment("### 🤖 AI Code Review\n" + body)


def maybe_fail_on_severity(text: str) -> None:
    """
    Optional: fail the job if high-severity keywords are present.
    Set AI_FAIL_ON_SEVERITY=1 in env to enable.
    """
    if os.getenv("AI_FAIL_ON_SEVERITY") not in {"1", "true", "True"}:
        return
    import re
    if re.search(r"(critical|high severity|sql injection|rce|remote code|secret leak|leaked secret|privilege escalation)", text, re.I):
        print("High severity findings detected — failing the job.")
        sys.exit(1)


def main() -> None:
    # --- Required env (provided by your workflow) ---
    gh_token        = os.environ["GITHUB_TOKEN"]
    openai_key      = os.environ["OPENAI_API_KEY"]
    pr_number       = int(os.environ["GITHUB_PR_ID"])
    repo_full       = os.environ["GITHUB_REPOSITORY"]   # e.g., "owner/repo"
    base_ref        = os.environ.get("GITHUB_BASE_REF") # e.g., "main" on the PR

    # 1) Build diff
    diff = build_pr_diff(base_ref)

    # 2) Ask OpenAI
    prompt = make_prompt(diff)
    review_text = call_openai(prompt, openai_key)

    # 3) Post back to PR
    post_pr_comment(gh_token, repo_full, pr_number, review_text)

    # 4) (Optional) severity gate
    maybe_fail_on_severity(review_text)

    print(f"Posted AI review to PR #{pr_number}.")
