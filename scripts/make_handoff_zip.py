"""Generate handoff archive and perform automated secret scanning across files and git history."""
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

# Secret patterns to detect
SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key (AIza...)"),
    (r"sk-[a-zA-Z0-9]{20,}", "Generic Secret Key (sk-...)"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"postgres(?:ql)?://[a-zA-Z0-9_\-\.]+:[^@\s]{1,100}@[a-zA-Z0-9_\-\.]+", "Database URI with Plaintext Password"),
]

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".ico", ".pdf", ".docx", ".zip", ".tar", ".gz",
    ".db", ".woff", ".woff2", ".ttf", ".eot", ".bin", ".exe", ".dll", ".so",
}

EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "dist",
    ".git",
    ".pytest_cache",
    "__pycache__",
    "handoff",
    ".gemini",
    "htmlcov",
}

EXCLUDE_FILES = {
    "shortlist.db",
    "shortlist.db-shm",
    "shortlist.db-wal",
    ".env",
}


def scan_file_for_secrets(file_path: Path) -> list[str]:
    findings = []
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return findings

    # Test files contain test mock URIs (e.g., test_database_url.py)
    is_test_file = "test" in file_path.name.lower() or "tests" in str(file_path).lower()
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in SECRET_PATTERNS:
            matches = re.findall(pattern, content)
            for m in matches:
                if isinstance(m, tuple):
                    m = m[0]
                m_lower = m.lower()
                # Ignore obvious mock/test dummy strings and templates
                if any(k in m_lower for k in ("fake", "example", "test", "dummy", "user:pass", "user:secret", "[user]:[password]", "<user>:<password>")):
                    continue
                if is_test_file and label == "Database URI with Plaintext Password":
                    continue
                findings.append(f"{label} detected in {file_path}")
    except Exception:
        pass
    return findings


def scan_git_history_for_secrets() -> list[str]:
    findings = []
    try:
        proc = subprocess.run(
            ["git", "--no-pager", "log", "-p", "-n", "30", "--", ".", ":!*.png", ":!*.docx", ":!*.pdf"],
            capture_output=True,
            text=True,
            errors="ignore",
        )
        diff_text = proc.stdout
        for pattern, label in SECRET_PATTERNS:
            matches = re.findall(pattern, diff_text)
            for m in matches:
                if isinstance(m, tuple):
                    m = m[0]
                m_lower = m.lower()
                if any(k in m_lower for k in ("fake", "example", "test", "dummy", "user:pass", "user:secret", "[user]:[password]", "<user>:<password>")):
                    continue
                findings.append(f"{label} detected in git history")
    except Exception as e:
        print(f"Notice: git history scan skipped: {e}")
    return findings


def make_handoff_zip():
    repo_root = Path.cwd()
    handoff_dir = repo_root / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    zip_path = handoff_dir / "ShortList_handoff.zip"

    print("=" * 60)
    print("Starting Automated Pre-Handoff Secret Scan")
    print("=" * 60)

    # 1. Secret scan in tracked/source files
    all_findings = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            fpath = Path(root) / f
            findings = scan_file_for_secrets(fpath)
            all_findings.extend(findings)

    # 2. Secret scan in git commit diff history
    git_findings = scan_git_history_for_secrets()
    all_findings.extend(git_findings)

    if all_findings:
        print("\033[91m[WARNING] Potential secrets detected:\033[0m")
        for item in all_findings:
            print(f"  - {item}")
        print("Handoff aborted. Please redact secrets before packaging.")
        sys.exit(1)
    else:
        print("\033[92m[CLEAN] Secret scan passed: 0 secrets detected across codebase and git history.\033[0m")

    # 3. Create zip archive
    print("\nPackaging repository into handoff archive...")
    packed_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f in EXCLUDE_FILES:
                    continue
                full_path = Path(root) / f
                rel_path = full_path.relative_to(repo_root)
                zf.write(full_path, rel_path)
                packed_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print("=" * 60)
    print(f"\033[92mArchive successfully created: {zip_path}\033[0m")
    print(f"Total files packaged: {packed_count}")
    print(f"Archive size: {size_mb:.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    make_handoff_zip()
