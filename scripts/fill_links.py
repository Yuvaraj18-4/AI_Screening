"""Replace placeholder tokens in TDD.md, deployment.md, and README.md.

Usage:
  python scripts/fill_links.py --github <GITHUB_URL> [--live <LIVE_URL>]
                               [--gemini-verified] [--postgres-verified] [--deployed]

Rules:
  - Validates that provided URLs start with https://
  - Replaces {{GITHUB_URL}} with the given GitHub URL
  - Replaces {{LIVE_URL}} with the given Live URL, or 'Live: not deployed' if omitted
  - When --gemini-verified is given, flips 'REAL Gemini output | NOT VERIFIED - pending'
    to 'REAL Gemini output | VERIFIED on YYYY-MM-DD'
  - When --postgres-verified is given, flips 'PostgreSQL / Neon | NOT VERIFIED - pending'
    to 'PostgreSQL / Neon | VERIFIED on YYYY-MM-DD'
  - When --deployed is given, flips 'Deployment | NOT DEPLOYED - pending'
    to 'Deployment | VERIFIED on YYYY-MM-DD'
  - Asserts that zero '{{' tokens remain in any updated file
  - Automatically regenerates TDD.docx and rebuilds submission/ShortList_submission.zip
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

# Subprocess to run make_tdd_docx and make_submission_zip
import subprocess


def validate_url(url: str, label: str):
    if not url.startswith("https://"):
        raise ValueError(f"{label} URL must start with 'https://': {url}")


def update_file_tokens(
    file_path: Path,
    github_url: str,
    live_url: str | None,
    gemini_verified: bool,
    postgres_verified: bool,
    deployed: bool,
    today_str: str,
):
    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping.")
        return

    content = file_path.read_text(encoding="utf-8")

    # Replace GitHub URL
    content = content.replace("{{GITHUB_URL}}", github_url)

    # Replace Live URL
    if live_url:
        content = content.replace("{{LIVE_URL}}", live_url)
    else:
        # If live omitted, replace 'Live: {{LIVE_URL}}' with 'Live: not deployed'
        content = re.sub(r"Live:\s*\{\{LIVE_URL\}\}", "Live: not deployed", content)
        content = content.replace("{{LIVE_URL}}", "not deployed")

    # Flip verification markers in status tables if flags provided
    if gemini_verified:
        content = content.replace(
            "| **REAL Gemini Output** | NOT VERIFIED - pending |",
            f"| **REAL Gemini Output** | VERIFIED on {today_str} |",
        )
        content = content.replace(
            "| REAL Gemini output | NOT VERIFIED - pending |",
            f"| REAL Gemini output | VERIFIED on {today_str} |",
        )

    if postgres_verified:
        content = content.replace(
            "| **PostgreSQL / Neon** | NOT VERIFIED - pending |",
            f"| **PostgreSQL / Neon** | VERIFIED on {today_str} |",
        )
        content = content.replace(
            "| PostgreSQL/Neon | NOT VERIFIED - pending |",
            f"| PostgreSQL/Neon | VERIFIED on {today_str} |",
        )

    if deployed:
        content = content.replace(
            "| **Deployment** | NOT DEPLOYED - pending |",
            f"| **Deployment** | VERIFIED on {today_str} |",
        )
        content = content.replace(
            "| Deployment | NOT DEPLOYED - pending |",
            f"| Deployment | VERIFIED on {today_str} |",
        )

    # Check for remaining {{ tokens
    remaining_tokens = re.findall(r"\{\{[^}]+\}\}", content)
    if remaining_tokens:
        raise ValueError(
            f"Error: Unresolved template tokens found in {file_path}: {remaining_tokens}"
        )

    file_path.write_text(content, encoding="utf-8")
    print(f"[OK] Updated {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Fill placeholder links in ShortList documentation.")
    parser.add_argument("--github", required=True, help="GitHub repository URL (must start with https://)")
    parser.add_argument("--live", required=False, help="Live deployment URL (must start with https://)")
    parser.add_argument("--gemini-verified", action="store_true", help="Mark REAL Gemini output as VERIFIED")
    parser.add_argument("--postgres-verified", action="store_true", help="Mark PostgreSQL/Neon as VERIFIED")
    parser.add_argument("--deployed", action="store_true", help="Mark Deployment as VERIFIED")

    args = parser.parse_args()

    # Validate URLs
    validate_url(args.github, "GitHub")
    if args.live:
        validate_url(args.live, "Live")

    today_str = datetime.date.today().isoformat()
    repo_root = Path.cwd()

    target_files = [
        repo_root / "TDD.md",
        repo_root / "deployment.md",
        repo_root / "README.md",
    ]

    print("=" * 60)
    print("ShortList Link & Verification Marker Filler")
    print(f"GitHub URL: {args.github}")
    print(f"Live URL:   {args.live or 'not deployed'}")
    print(f"Gemini Verified:   {args.gemini_verified}")
    print(f"Postgres Verified: {args.postgres_verified}")
    print(f"Deployed:          {args.deployed}")
    print("=" * 60)

    for target in target_files:
        update_file_tokens(
            file_path=target,
            github_url=args.github,
            live_url=args.live,
            gemini_verified=args.gemini_verified,
            postgres_verified=args.postgres_verified,
            deployed=args.deployed,
            today_str=today_str,
        )

    # Regenerate TDD.docx
    print("\nRegenerating TDD.docx...")
    python_bin = sys.executable
    subprocess.run([python_bin, str(repo_root / "scripts" / "make_tdd_docx.py")], check=True)

    # Rebuild submission zip
    print("\nRebuilding submission zip...")
    subprocess.run([python_bin, str(repo_root / "scripts" / "make_submission_zip.py")], check=True)

    print("\n" + "=" * 60)
    print("ALL DOCUMENTATION TOKENS SUCCESSFULLY FILLED & PACKAGED!")
    print("=" * 60)


if __name__ == "__main__":
    main()

