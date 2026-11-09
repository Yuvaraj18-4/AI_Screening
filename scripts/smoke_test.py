"""End-to-End HTTP Smoke Test for ShortList.

Starts from a fresh database (or deployed --base-url), exercises the full recruiter and client workflow
over HTTP in heuristic mode, and asserts all key business and security rules.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.db.models.entities import AuditLog, Candidate, Client, User
from app.core.security import hash_password
from app.main import create_app


def print_step(step_num: int, title: str, passed: bool, detail: str = ""):
    status = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    detail_str = f" - {detail}" if detail else ""
    print(f"[{status}] Step {step_num}: {title}{detail_str}")
    if not passed:
        print(f"\n[ERROR] Smoke test halted at Step {step_num}: {title}")
        sys.exit(1)


async def run_smoke_test(base_url: str | None = None):
    print("=" * 70)
    print(f"Starting ShortList End-to-End HTTP Smoke Test (Target: {base_url or 'In-Process ASGI'})")
    print("=" * 70)

    is_remote = bool(base_url)
    c_apex_id = None
    worker_task = None

    if not is_remote:
        # 1. Reset database to completely fresh state
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # Seed baseline clients and users
        async with AsyncSessionLocal() as db:
            c_apex = Client(name="Apex Financial Technologies")
            c_zenith = Client(name="Zenith Retail Solutions")
            db.add_all([c_apex, c_zenith])
            await db.flush()
            c_apex_id = c_apex.id

            recruiter = User(
                email="recruiter@example.com",
                password_hash=hash_password("recruiter123"),
                name="Recruiter Lead",
                role="recruiter",
            )
            client1 = User(
                email="client1@example.com",
                password_hash=hash_password("client123"),
                name="Apex Client Approver",
                role="client",
                client_id=c_apex.id,
            )
            client2 = User(
                email="client2@example.com",
                password_hash=hash_password("client123"),
                name="Zenith Client Approver",
                role="client",
                client_id=c_zenith.id,
            )
            db.add_all([recruiter, client1, client2])
            await db.commit()

        from app.jobs.worker import start_worker, stop_worker
        worker_task = await start_worker()

    try:
        if is_remote:
            client_ctx = AsyncClient(base_url=base_url.rstrip("/"), timeout=30.0)
        else:
            app = create_app()
            transport = ASGITransport(app=app)
            client_ctx = AsyncClient(transport=transport, base_url="http://testserver", timeout=30.0)

        async with client_ctx as client:
            # Step 1: Login as recruiter
            login_res = await client.post(
                "/api/auth/login",
                json={"email": "recruiter@example.com", "password": "recruiter123"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            print_step(1, "Recruiter authentication", login_res.status_code == 200, f"HTTP {login_res.status_code}")
            recruiter_cookies = {"access_token": login_res.cookies.get("access_token")}

            # If remote, discover Apex Financial client id
            if is_remote or not c_apex_id:
                reqs_check = await client.get("/api/requisitions", cookies=recruiter_cookies)
                if reqs_check.status_code == 200 and reqs_check.json():
                    c_apex_id = reqs_check.json()[0]["client_id"]
                else:
                    c_apex_id = 1

            # Step 2: Create requisition for Apex Financial Technologies
            req_res = await client.post(
                "/api/requisitions",
                json={
                    "client_id": c_apex_id,
                    "title": "Senior Java Developer",
                    "jd_text": (
                        "Apex Financial Technologies is seeking a Senior Java Developer with 5+ years of experience "
                        "building high-throughput distributed systems in Noida or Delhi NCR. Must have hands-on expertise "
                        "in Spring Boot, microservices architecture, and event streaming with Kafka. Notice period must not "
                        "exceed 60 days."
                    ),
                    "status": "active",
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(2, "Create Requisition", req_res.status_code == 200, f"Requisition ID: {req_res.json().get('id')}")
            req_id = req_res.json()["id"]

            # Step 3: Extract and edit scorecard
            extract_res = await client.post(
                f"/api/requisitions/{req_id}/jd/extract",
                json={},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(3, "JD Scorecard Extraction", extract_res.status_code == 200)

            # Save customized scorecard with strict must-haves
            save_sc_res = await client.post(
                f"/api/requisitions/{req_id}/scorecard",
                json={
                    "criteria": [
                        {
                            "name": "Experience >= 5 years",
                            "kind": "experience",
                            "must_have": True,
                            "weight": 3,
                            "params": {"min_years": 5.0},
                            "description": "Minimum 5 years of software engineering experience",
                        },
                        {
                            "name": "Notice Period <= 60 days",
                            "kind": "notice",
                            "must_have": True,
                            "weight": 2,
                            "params": {"max_days": 60},
                            "description": "Available to join within 60 calendar days",
                        },
                        {
                            "name": "Location in Delhi/NCR/Noida",
                            "kind": "location",
                            "must_have": True,
                            "weight": 2,
                            "params": {"target": "delhi/ncr"},
                            "description": "Candidate based in Delhi, Noida, or Gurgaon",
                        },
                        {
                            "name": "Spring Boot & Microservices",
                            "kind": "skill",
                            "must_have": True,
                            "weight": 3,
                            "params": {},
                            "description": "Production experience with Spring Boot microservices",
                        },
                        {
                            "name": "Kafka & Event Streaming",
                            "kind": "skill",
                            "must_have": False,
                            "weight": 2,
                            "params": {},
                            "description": "Hands-on experience with Apache Kafka messaging",
                        },
                    ]
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(4, "Save Requisition Scorecard", save_sc_res.status_code == 200)

            # Test rejection of unsupported .exe upload
            exe_upload = await client.post(
                f"/api/requisitions/{req_id}/uploads",
                files=[("files", ("exploit.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload"))],
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            exe_passed = False
            if exe_upload.status_code == 200:
                b_info = exe_upload.json()
                prg = await client.get(f"/api/uploads/{b_info['batch_id']}/progress", cookies=recruiter_cookies)
                exe_passed = prg.status_code == 200 and prg.json()["failed"] >= 1
            else:
                exe_passed = exe_upload.status_code in (400, 422)
            print_step(5, "Reject Unsupported File (.exe upload)", exe_passed)

            # Step 4: Upload sample CVs (Ritika, Pooja, and Arjun)
            sample_dir = Path("data/sample_cvs")
            if not sample_dir.exists():
                from scripts.generate_samples import generate_all

                generate_all()

            cv_names = ["CND-91022_Ritika_Bansal.pdf", "CND-91088_Pooja_Nair.pdf", "CND-91047_Arjun_Rawat.docx"]
            files = []
            for name in cv_names:
                p = sample_dir / name
                files.append(
                    (
                        "files",
                        (
                            name,
                            open(p, "rb").read(),
                            "application/pdf"
                            if name.endswith(".pdf")
                            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        ),
                    )
                )

            upload_res = await client.post(
                f"/api/requisitions/{req_id}/uploads",
                files=files,
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(
                6,
                "Upload Sample CVs",
                upload_res.status_code == 200,
                f"Batch ID: {upload_res.json().get('batch_id')}",
            )

            # Wait / Poll progress and scoring completion
            batch_id = upload_res.json()["batch_id"]
            for _ in range(30):
                prog_res = await client.get(f"/api/uploads/{batch_id}/progress", cookies=recruiter_cookies)
                pdata = prog_res.json()
                if pdata["total"] > 0 and (pdata["done"] + pdata["failed"] >= pdata["total"]):
                    break
                await asyncio.sleep(0.5)

            await asyncio.sleep(2)

            # Step 5: Check candidate ranking
            apps_res = await client.get(
                f"/api/requisitions/{req_id}/applications?sort=score",
                cookies=recruiter_cookies,
            )
            print_step(7, "Fetch Ranked Candidate Applications", apps_res.status_code == 200)
            apps = apps_res.json()
            assert len(apps) >= 2, "Expected at least 2 candidates in application list"

            ritika_app = next((a for a in apps if "ritika" in a["candidate_name"].lower()), None)
            pooja_app = next((a for a in apps if "pooja" in a["candidate_name"].lower()), None)
            arjun_app = next((a for a in apps if "arjun" in a["candidate_name"].lower()), None)

            assert ritika_app is not None, "Ritika Bansal must exist in applications"
            assert pooja_app is not None, "Pooja Nair must exist in applications"

            ritika_score = ritika_app["score"]["total"] if ritika_app.get("score") else 0
            pooja_score = pooja_app["score"]["total"] if pooja_app.get("score") else 0

            # Assert ranking and notice gap
            print_step(
                8,
                "Assert Ritika ranks above Pooja",
                ritika_score > pooja_score,
                f"Ritika ({ritika_score}) > Pooja ({pooja_score})",
            )

            pooja_gaps = pooja_app["score"]["must_have_gaps"] if pooja_app.get("score") else []
            has_notice_gap = any("notice" in g.lower() for g in pooja_gaps)
            print_step(
                9,
                "Assert Pooja exhibits Notice Period gap",
                has_notice_gap,
                f"Gaps identified: {pooja_gaps}",
            )

            # Step 6: Recruiter opens candidate (recording view log)
            view_res = await client.get(
                f"/api/applications/{ritika_app['id']}",
                cookies=recruiter_cookies,
            )
            print_step(10, "Recruiter views candidate profile (ViewLog)", view_res.status_code == 200)

            # Step 7: Recruiter submits shortlist to client
            sub_res = await client.post(
                f"/api/applications/{ritika_app['id']}/submit",
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(11, "Submit Candidate Shortlist to Client", sub_res.status_code == 200)
            sub_id = sub_res.json()["id"]

            # Also view and submit Pooja so client has 2 submissions to review
            await client.get(f"/api/applications/{pooja_app['id']}", cookies=recruiter_cookies)
            sub2_res = await client.post(
                f"/api/applications/{pooja_app['id']}/submit",
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            sub2_id = sub2_res.json()["id"]

            # Step 8: Client 1 logs in
            c1_login = await client.post(
                "/api/auth/login",
                json={"email": "client1@example.com", "password": "client123"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            print_step(12, "Client 1 Authentication", c1_login.status_code == 200)
            client1_cookies = {"access_token": c1_login.cookies.get("access_token")}

            # Step 9: Client 1 queries submissions list
            c1_list_res = await client.get(
                f"/api/portal/requisitions/{req_id}/submissions",
                cookies=client1_cookies,
            )
            c1_list = c1_list_res.json() if c1_list_res.status_code == 200 else []
            c1_list_ok = (
                c1_list_res.status_code == 200
                and len(c1_list) >= 2
                and c1_list[0]["candidate_email"] == "[MASKED_UNTIL_SHORTLIST]"
            )
            print_step(
                13,
                "Client Portal Submissions List (Eager Load & Masking)",
                c1_list_ok,
                f"HTTP {c1_list_res.status_code}, {len(c1_list)} submissions retrieved",
            )

            # Step 10: Confirm candidate submission detail and contact masking
            c1_detail = await client.get(
                f"/api/portal/submissions/{sub_id}",
                cookies=client1_cookies,
            )
            c1_data = c1_detail.json() if c1_detail.status_code == 200 else {}
            is_masked = (
                c1_detail.status_code == 200
                and c1_data.get("masked") is True
                and c1_data.get("candidate_email") == "[MASKED_UNTIL_SHORTLIST]"
                and c1_data.get("candidate_phone") == "[MASKED_UNTIL_SHORTLIST]"
            )
            print_step(
                14,
                "Verify Candidate Submission Detail Contact Masking",
                is_masked,
                f"Email: {c1_data.get('candidate_email')}, Phone: {c1_data.get('candidate_phone')}",
            )

            # Step 11: Client 1 Shortlists candidate 1 (Ritika) -> contacts should unmask
            shortlist_decision = await client.post(
                f"/api/portal/submissions/{sub_id}/decision",
                json={"decision": "shortlisted"},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=client1_cookies,
            )
            sl_data = shortlist_decision.json()
            contacts_unmasked = (
                sl_data["stage"] == "client_shortlisted"
                and "@" in sl_data["candidate_email"]
                and sl_data["masked"] is False
            )
            print_step(
                15,
                "Client Shortlist Decision & Contact Unmasking",
                contacts_unmasked,
                f"Stage: {sl_data['stage']}, Email: {sl_data['candidate_email']}",
            )

            # Step 12: Client 1 attempts rejection WITHOUT reason -> Must fail with 422
            rej_no_reason = await client.post(
                f"/api/portal/submissions/{sub2_id}/decision",
                json={"decision": "rejected", "reject_reason": "   "},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=client1_cookies,
            )
            print_step(
                16,
                "Reject Without Reason Blocked (Validation Check)",
                rej_no_reason.status_code == 422,
                f"HTTP {rej_no_reason.status_code} as expected",
            )

            # Step 13: Client 1 Rejects candidate 2 (Pooja) with mandatory reason
            reject_decision = await client.post(
                f"/api/portal/submissions/{sub2_id}/decision",
                json={
                    "decision": "rejected",
                    "reject_reason": "Notice period of 90 days exceeds maximum client 60-day joining cutoff",
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=client1_cookies,
            )
            rej_data = reject_decision.json()
            print_step(
                17,
                "Client Rejection Decision with Mandatory Reason",
                rej_data["stage"] == "rejected" and bool(rej_data["reject_reason"]),
                f"Reason: {rej_data['reject_reason']}",
            )

            # Step 14: Client 2 logs in and verifies complete multi-tenant isolation
            c2_login = await client.post(
                "/api/auth/login",
                json={"email": "client2@example.com", "password": "client123"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            print_step(18, "Client 2 Authentication (Zenith Retail)", c2_login.status_code == 200)
            client2_cookies = {"access_token": c2_login.cookies.get("access_token")}

            c2_cross_list = await client.get(
                f"/api/portal/requisitions/{req_id}/submissions",
                cookies=client2_cookies,
            )
            c2_cross_access = await client.get(
                f"/api/portal/submissions/{sub_id}",
                cookies=client2_cookies,
            )
            c2_isolated = (c2_cross_list.status_code == 404 and c2_cross_access.status_code == 404)
            print_step(
                19,
                "Cross-Client Access Protection (Multi-Tenant Isolation 404)",
                c2_isolated,
                f"Submissions List: HTTP {c2_cross_list.status_code}, Detail: HTTP {c2_cross_access.status_code} (404 expected)",
            )

            # =================================================================
            # EXTENDED STEPS (Production Hardening)
            # =================================================================

            # Step 20: Scorecard PUT creating a new version
            sc_put_res = await client.put(
                f"/api/requisitions/{req_id}/scorecard",
                json={
                    "criteria": [
                        {
                            "name": "Experience >= 6 years",
                            "kind": "experience",
                            "must_have": True,
                            "weight": 3,
                            "params": {"min_years": 6.0},
                            "description": "Updated version 2 minimum 6 years experience",
                        },
                        {
                            "name": "Notice Period <= 30 days",
                            "kind": "notice",
                            "must_have": True,
                            "weight": 2,
                            "params": {"max_days": 30},
                            "description": "Immediate joiner preferred",
                        },
                    ]
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            sc_v2 = sc_put_res.json() if sc_put_res.status_code == 200 else {}
            print_step(
                20,
                "Scorecard PUT creates new version (Version 2)",
                sc_put_res.status_code == 200 and sc_v2.get("version") == 2,
                f"Scorecard version: {sc_v2.get('version')}",
            )

            # Step 21: Rescore application with updated scorecard
            rescore_res = await client.post(
                f"/api/applications/{ritika_app['id']}/rescore",
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            rescored_data = rescore_res.json() if rescore_res.status_code == 200 else {}
            print_step(
                21,
                "Application Rescore executes successfully",
                rescore_res.status_code == 200 and rescored_data.get("score") is not None,
                f"New score total: {rescored_data.get('score', {}).get('total')}",
            )

            # Step 22: Stage change transition
            stage_res = await client.post(
                f"/api/applications/{ritika_app['id']}/stage",
                json={"stage": "interview", "note": "Moving candidate to technical round 1"},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            st_data = stage_res.json() if stage_res.status_code == 200 else {}
            print_step(
                22,
                "Stage Change Transition (to 'interview')",
                stage_res.status_code == 200 and st_data.get("stage") == "interview",
                f"New stage: {st_data.get('stage')}",
            )

            # Step 23: Consent Record & Revoke
            cand_id = ritika_app["candidate_id"]
            consent_rec = await client.post(
                f"/api/candidates/{cand_id}/consent",
                json={"channel": "email", "notes": "Consent confirmed via email thread"},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            c_rec_ok = consent_rec.status_code == 200 and consent_rec.json().get("consent_status") == "granted"

            consent_rev = await client.delete(
                f"/api/candidates/{cand_id}/consent",
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            c_rev_ok = consent_rev.status_code == 200 and consent_rev.json().get("consent_status") == "revoked"
            print_step(
                23,
                "Consent Record and Revoke Workflow",
                c_rec_ok and c_rev_ok,
                f"Grant: HTTP {consent_rec.status_code}, Revoke: HTTP {consent_rev.status_code}",
            )

            # Step 24: Duplicate Resolution
            dup_target = arjun_app if arjun_app else pooja_app
            dup_res = await client.post(
                f"/api/candidates/{dup_target['candidate_id']}/duplicate-resolution",
                json={"action": "keep"},
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            print_step(
                24,
                "Duplicate Resolution Workflow",
                dup_res.status_code == 200,
                f"HTTP {dup_res.status_code}",
            )

            # Step 25: Candidate Deletion with hash-only audit log
            del_cand_id = dup_target["candidate_id"]
            del_res = await client.delete(
                f"/api/candidates/{del_cand_id}",
                headers={"X-Requested-With": "XMLHttpRequest"},
                cookies=recruiter_cookies,
            )
            del_ok = del_res.status_code == 200

            # Verify no personal data remains
            if not is_remote:
                async with AsyncSessionLocal() as db:
                    cand_in_db = await db.get(Candidate, del_cand_id)
                    assert cand_in_db.name == "[DELETED_CANDIDATE]"
                    assert cand_in_db.phone == "[DELETED]"
                    assert "deleted_" in cand_in_db.email

                    # Check audit log contains entity_hash without personal data
                    audit_res = await db.execute(
                        select(AuditLog).where(AuditLog.action == "delete_candidate_personal_data")
                    )
                    audit_entry = audit_res.scalars().first()
                    assert audit_entry is not None
                    assert len(audit_entry.entity_hash) == 64
                    # Meta only contains candidate_id and reason
                    assert "name" not in audit_entry.meta
                    assert "email" not in audit_entry.meta
                    assert "phone" not in audit_entry.meta

            print_step(
                25,
                "Candidate Erasure & Hash-Only Audit Log (No PII Stored)",
                del_ok,
                f"HTTP {del_res.status_code}, DB record redacted, AuditLog hash recorded",
            )

        print("=" * 70)
        print("\033[92mALL 25 SMOKE TEST STEPS PASSED SUCCESSFULLY!\033[0m")
        print("=" * 70)
    finally:
        if worker_task:
            from app.jobs.worker import stop_worker

            await stop_worker()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShortList End-to-End Smoke Test")
    parser.add_argument("--base-url", type=str, default=None, help="Deployed base URL to test against")
    args = parser.parse_args()
    asyncio.run(run_smoke_test(base_url=args.base_url))
