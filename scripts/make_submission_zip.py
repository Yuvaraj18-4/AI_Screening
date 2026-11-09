"""Generate submission/ShortList_submission.zip containing ONLY TDD.docx and deployment.md.
Validates that the archive size is strictly under 25 MB.
"""
import zipfile
from pathlib import Path


def make_submission_zip():
    repo_root = Path.cwd()
    submission_dir = repo_root / "submission"
    submission_dir.mkdir(parents=True, exist_ok=True)
    zip_path = submission_dir / "ShortList_submission.zip"

    files_to_pack = [
        ("TDD.docx", repo_root / "TDD.docx"),
        ("deployment.md", repo_root / "deployment.md"),
    ]

    print("=" * 60)
    print("Creating Submission Archive")
    print("=" * 60)

    for arcname, fpath in files_to_pack:
        if not fpath.exists():
            raise FileNotFoundError(f"Required submission file missing: {fpath}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, fpath in files_to_pack:
            zf.write(fpath, arcname=arcname)
            print(f"  + Added: {arcname} ({fpath.stat().st_size:,} bytes)")

    size_bytes = zip_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print("=" * 60)
    print(f"Submission Archive Created: {zip_path}")
    print(f"Total Files: {len(files_to_pack)}")
    print(f"Archive Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
    print("=" * 60)

    if size_mb >= 25.0:
        raise ValueError(f"Submission archive exceeds 25 MB limit! Size: {size_mb:.2f} MB")

    # Verify contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        print(f"Verified archive contents: {namelist}")
        assert set(namelist) == {"TDD.docx", "deployment.md"}, f"Unexpected files in zip: {namelist}"

    return zip_path


if __name__ == "__main__":
    make_submission_zip()

