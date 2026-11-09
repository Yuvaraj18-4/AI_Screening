"""Seed database with realistic demo data across recruiters, clients, requisitions, scorecards, and candidates."""
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import sys

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, select
from app.ai.masking import mask_personal_data
from app.ai.scoring import evaluate_and_score_application
from app.core.security import hash_password
from app.db.base import Base
from app.db.models.entities import (
    Application,
    Candidate,
    Client,
    Consent,
    Criterion,
    CVFile,
    PipelineEvent,
    Requisition,
    Scorecard,
    Submission,
    User,
    ViewLog,
)
from app.db.session import AsyncSessionLocal, engine
from app.parsing.extract_text import extract_cv_text
from app.parsing.profile import parse_candidate_profile


def _empty_profile(filename: str) -> dict:
    return {
        "name": filename.replace(".pdf", "").replace(".docx", "").replace("_", " "),
        "email": "",
        "phone": "",
        "location": "",
        "current_role": "",
        "skills": [],
        "experience_years": 0.0,
        "notice_days": 0,
        "current_ctc": "",
        "expected_ctc": "",
        "parse_quality": 0.0,
    }


async def seed():
    print("Starting comprehensive database seeding...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if users already seeded
        existing_user = await db.execute(select(User).limit(1))
        if existing_user.scalars().first():
            print("Existing database found. Purging for clean realistic demo state...")
            # Purge existing data cleanly
            for entity in [
                PipelineEvent,
                ViewLog,
                Submission,
                Consent,
                CVFile,
                Application,
                Candidate,
                Criterion,
                Scorecard,
                Requisition,
                User,
                Client,
            ]:
                await db.execute(delete(entity))
            await db.commit()

        print("1. Creating Clients...")
        client_apex = Client(name="Apex Financial Technologies")
        client_zenith = Client(name="Zenith Retail Solutions")
        client_cloudscale = Client(name="CloudScale Systems")
        db.add_all([client_apex, client_zenith, client_cloudscale])
        await db.flush()

        print("2. Creating Users (Recruiters & Clients)...")
        r1 = User(
            email="recruiter@example.com",
            password_hash=hash_password("recruiter123"),
            name="Sarah Jenkins",
            role="recruiter",
        )
        r2 = User(
            email="recruiter2@example.com",
            password_hash=hash_password("recruiter123"),
            name="Amitabh Sen",
            role="recruiter",
        )
        c1 = User(
            email="client1@example.com",
            password_hash=hash_password("client123"),
            name="Vikram Oberoi",
            role="client",
            client_id=client_apex.id,
        )
        c2 = User(
            email="client2@example.com",
            password_hash=hash_password("client123"),
            name="Priya Sharma",
            role="client",
            client_id=client_zenith.id,
        )
        c3 = User(
            email="client3@example.com",
            password_hash=hash_password("client123"),
            name="Ananya Verma",
            role="client",
            client_id=client_cloudscale.id,
        )
        db.add_all([r1, r2, c1, c2, c3])
        await db.flush()

        print("3. Creating Requisitions & Scorecards...")

        # Requisition 1: Senior Java Developer (Apex)
        req_java = Requisition(
            client_id=client_apex.id,
            title="Senior Java Developer",
            jd_text=(
                "Apex Financial Technologies is seeking a Senior Java Developer with 5+ years of experience "
                "building high-throughput distributed systems in Noida or Delhi NCR. Must have hands-on expertise "
                "in Spring Boot, microservices architecture, and event streaming with Kafka. Notice period must not "
                "exceed 60 days."
            ),
            status="active",
            owner_id=r1.id,
        )

        # Requisition 2: Lead DevOps & Cloud SRE (Apex)
        req_devops = Requisition(
            client_id=client_apex.id,
            title="Lead DevOps & Cloud SRE",
            jd_text=(
                "Apex Financial Technologies requires a Lead DevOps & SRE Engineer with 5+ years of experience "
                "managing Kubernetes clusters, Terraform infrastructure-as-code, and AWS cloud environments. "
                "Must have strong CI/CD automation and observability experience with Prometheus or Grafana. "
                "Notice period max 45 days."
            ),
            status="active",
            owner_id=r1.id,
        )

        # Requisition 3: KYC Analyst (Zenith)
        req_kyc = Requisition(
            client_id=client_zenith.id,
            title="KYC Analyst",
            jd_text=(
                "Zenith Retail Solutions is hiring a KYC Analyst for banking back-office compliance operations. "
                "Requires 2+ years of experience in Customer Due Diligence, AML screening, and advanced Excel. "
                "Notice period maximum 30 days."
            ),
            status="active",
            owner_id=r2.id,
        )

        # Requisition 4: Full Stack Python/React Engineer (CloudScale)
        req_fullstack = Requisition(
            client_id=client_cloudscale.id,
            title="Full Stack Python/React Engineer",
            jd_text=(
                "CloudScale Systems is looking for a versatile Full Stack Engineer with 3+ years experience "
                "in Python (FastAPI/Django) and modern React with TypeScript. Experience with PostgreSQL and "
                "containerized deployments is required. Notice period maximum 30 days."
            ),
            status="active",
            owner_id=r2.id,
        )

        db.add_all([req_java, req_devops, req_kyc, req_fullstack])
        await db.flush()

        # Scorecard 1: Senior Java
        sc_java = Scorecard(requisition_id=req_java.id, version=1, is_active=True)
        db.add(sc_java)
        await db.flush()
        crit_java = [
            Criterion(scorecard_id=sc_java.id, name="Experience >= 5 years", kind="experience", must_have=True, weight=3, params={"min_years": 5.0}, description="Minimum 5 years of software engineering experience"),
            Criterion(scorecard_id=sc_java.id, name="Notice Period <= 60 days", kind="notice", must_have=True, weight=2, params={"max_days": 60}, description="Available to join within 60 calendar days"),
            Criterion(scorecard_id=sc_java.id, name="Location in Delhi/NCR/Noida", kind="location", must_have=True, weight=2, params={"target": "delhi/ncr"}, description="Candidate based in Delhi, Noida, or Gurgaon"),
            Criterion(scorecard_id=sc_java.id, name="Spring Boot & Microservices", kind="skill", must_have=True, weight=3, params={}, description="Production experience with Spring Boot microservices"),
            Criterion(scorecard_id=sc_java.id, name="Kafka & Event Streaming", kind="skill", must_have=False, weight=2, params={}, description="Hands-on experience with Apache Kafka messaging"),
            Criterion(scorecard_id=sc_java.id, name="Containers & Kubernetes", kind="skill", must_have=False, weight=1, params={}, description="Experience deploying containerized services with Docker/Kubernetes"),
        ]
        db.add_all(crit_java)

        # Scorecard 2: DevOps SRE
        sc_devops = Scorecard(requisition_id=req_devops.id, version=1, is_active=True)
        db.add(sc_devops)
        await db.flush()
        crit_devops = [
            Criterion(scorecard_id=sc_devops.id, name="Experience >= 5 years", kind="experience", must_have=True, weight=3, params={"min_years": 5.0}, description="Minimum 5 years in infrastructure or DevOps"),
            Criterion(scorecard_id=sc_devops.id, name="Notice Period <= 45 days", kind="notice", must_have=True, weight=2, params={"max_days": 45}, description="Maximum 45 days notice period"),
            Criterion(scorecard_id=sc_devops.id, name="Kubernetes & Docker", kind="skill", must_have=True, weight=3, params={}, description="Container orchestration and cluster management"),
            Criterion(scorecard_id=sc_devops.id, name="Terraform & AWS", kind="skill", must_have=True, weight=3, params={}, description="Infrastructure as code on AWS"),
            Criterion(scorecard_id=sc_devops.id, name="CI/CD & Observability", kind="skill", must_have=False, weight=2, params={}, description="GitLab CI/GitHub Actions, Prometheus, Grafana"),
        ]
        db.add_all(crit_devops)

        # Scorecard 3: KYC Analyst
        sc_kyc = Scorecard(requisition_id=req_kyc.id, version=1, is_active=True)
        db.add(sc_kyc)
        await db.flush()
        crit_kyc = [
            Criterion(scorecard_id=sc_kyc.id, name="Experience >= 2 years", kind="experience", must_have=True, weight=3, params={"min_years": 2.0}, description="Minimum 2 years of banking or compliance experience"),
            Criterion(scorecard_id=sc_kyc.id, name="Notice Period <= 30 days", kind="notice", must_have=True, weight=2, params={"max_days": 30}, description="Maximum 30 days notice period"),
            Criterion(scorecard_id=sc_kyc.id, name="KYC & AML Compliance", kind="domain", must_have=True, weight=3, params={}, description="Customer due diligence and AML regulations"),
            Criterion(scorecard_id=sc_kyc.id, name="Advanced Excel & Reporting", kind="skill", must_have=False, weight=2, params={}, description="Pivot tables, macros, and SLA reporting"),
        ]
        db.add_all(crit_kyc)

        # Scorecard 4: Full Stack Engineer
        sc_fullstack = Scorecard(requisition_id=req_fullstack.id, version=1, is_active=True)
        db.add(sc_fullstack)
        await db.flush()
        crit_fullstack = [
            Criterion(scorecard_id=sc_fullstack.id, name="Experience >= 3 years", kind="experience", must_have=True, weight=3, params={"min_years": 3.0}, description="Minimum 3 years full stack web engineering"),
            Criterion(scorecard_id=sc_fullstack.id, name="Notice Period <= 30 days", kind="notice", must_have=True, weight=2, params={"max_days": 30}, description="Maximum 30 days notice period"),
            Criterion(scorecard_id=sc_fullstack.id, name="Python & FastAPI", kind="skill", must_have=True, weight=3, params={}, description="Backend API development in Python"),
            Criterion(scorecard_id=sc_fullstack.id, name="React & TypeScript", kind="skill", must_have=True, weight=3, params={}, description="Frontend development in React with TypeScript"),
            Criterion(scorecard_id=sc_fullstack.id, name="PostgreSQL & Database Design", kind="skill", must_have=False, weight=2, params={}, description="Relational data modeling and queries"),
        ]
        db.add_all(crit_fullstack)
        await db.commit()

        # Check sample CVs
        sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_cvs"
        if not sample_dir.exists() or len(list(sample_dir.glob("*.*"))) == 0:
            print("data/sample_cvs missing or empty; generating samples...")
            from scripts.generate_samples import generate_all
            generate_all()

        cv_files = sorted(list(sample_dir.glob("*.*")))
        print(f"Loaded {len(cv_files)} sample CV files.")

        # Requisition CV routing buckets:
        # Req 1 (Java): 12 CVs (indices 0 to 11)
        # Req 2 (DevOps): 6 CVs (indices 12 to 17)
        # Req 3 (KYC): 6 CVs (indices 18 to 23)
        # Req 4 (FullStack): 6 CVs (indices 24 to 29)
        routing = [
            (req_java, cv_files[0:12], r1),
            (req_devops, cv_files[12:18], r1),
            (req_kyc, cv_files[18:24], r2),
            (req_fullstack, cv_files[24:30], r2),
        ]

        now = datetime.now(UTC)

        for req, files_slice, recruiter in routing:
            print(f"\nProcessing {len(files_slice)} candidates for Requisition '{req.title}'...")
            for cv_path in files_slice:
                filename = cv_path.name
                with open(cv_path, "rb") as f:
                    content = f.read()

                extracted = extract_cv_text(filename, content)
                text = extracted.text
                masked_text = mask_personal_data(text) if text else ""
                try:
                    profile = await parse_candidate_profile(text) if text else _empty_profile(filename)
                except Exception as exc:
                    print(f"Profile parse fallback for {filename}: {exc}")
                    profile = _empty_profile(filename)

                sha256 = hashlib.sha256(content).hexdigest()
                email_val = profile.get("email") or f"cand_{sha256[:8]}@example.com"

                # Check / Create candidate
                c_res = await db.execute(select(Candidate).where(Candidate.email == email_val))
                cand = c_res.scalars().first()
                if not cand:
                    cand = Candidate(
                        name=profile.get("name") or "Candidate",
                        email=email_val,
                        phone=profile.get("phone") or "+91 98765 43210",
                        location=profile.get("location") or "Noida, Delhi NCR",
                        current_role=profile.get("current_role") or "Software Engineer",
                        skills=profile.get("skills") or ["Python", "Java", "SQL"],
                        experience_years=profile.get("experience_years") or 5.0,
                        notice_days=profile.get("notice_days") or 30,
                        current_ctc=profile.get("current_ctc") or "18 LPA",
                        expected_ctc=profile.get("expected_ctc") or "24 LPA",
                        parse_quality=profile.get("parse_quality") or 1.0,
                    )
                    db.add(cand)
                    await db.flush()

                    # Add consent record
                    consent = Consent(
                        candidate_id=cand.id,
                        source="recruiter_attested_linkedin",
                        given_at=now - timedelta(days=5),
                        recorded_by=recruiter.id,
                    )
                    db.add(consent)

                    # Add CV file
                    cv_file_obj = CVFile(
                        candidate_id=cand.id,
                        filename=filename,
                        mime="application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        size=len(content),
                        sha256=sha256,
                        content=content,
                        text=text,
                        masked_text=masked_text,
                        parse_status=extracted.parse_status,
                        parse_error=extracted.parse_error,
                    )
                    db.add(cv_file_obj)
                    await db.flush()

                # Create application
                app_res = await db.execute(
                    select(Application).where(
                        Application.candidate_id == cand.id,
                        Application.requisition_id == req.id,
                    )
                )
                app_obj = app_res.scalars().first()
                if not app_obj:
                    app_obj = Application(
                        requisition_id=req.id,
                        candidate_id=cand.id,
                        stage="screened",
                    )
                    db.add(app_obj)
                    await db.flush()

                    # Add recruiter ViewLog (audit of review)
                    view_log = ViewLog(
                        user_id=recruiter.id,
                        candidate_id=cand.id,
                        application_id=app_obj.id,
                        context="detail",
                    )
                    db.add(view_log)

                    # Initial pipeline event
                    db.add(
                        PipelineEvent(
                            application_id=app_obj.id,
                            from_stage="sourced",
                            to_stage="screened",
                            actor_id=recruiter.id,
                            note="Candidate parsed and screened by recruiter.",
                        )
                    )

                    # Score application
                    if extracted.parse_status != "failed" and masked_text:
                        try:
                            await evaluate_and_score_application(db=db, application_id=app_obj.id)
                        except Exception as exc:
                            print(f"Scoring notice for {filename}: {exc}")

            await db.commit()

        print("\n4. Simulating Submissions & Client Review Decisions...")

        # A) Senior Java Developer (Client 1: Apex Financial - Vikram Oberoi)
        java_apps_res = await db.execute(
            select(Application).where(Application.requisition_id == req_java.id)
        )
        java_apps = java_apps_res.scalars().all()

        if len(java_apps) >= 4:
            # Candidate 0: Client Shortlisted (contacts unmasked in portal)
            sub0 = Submission(
                application_id=java_apps[0].id,
                submitted_by=r1.id,
                submitted_at=now - timedelta(days=3),
                client_decision="shortlisted",
                decided_by=c1.id,
                decided_at=now - timedelta(days=1),
            )
            java_apps[0].stage = "client_shortlisted"
            db.add(sub0)
            db.add(
                PipelineEvent(
                    application_id=java_apps[0].id,
                    from_stage="submitted",
                    to_stage="client_shortlisted",
                    actor_id=c1.id,
                    note="Strong distributed systems background, excellent match for core trading team.",
                )
            )

            # Candidate 1: Client Interview Requested
            sub1 = Submission(
                application_id=java_apps[1].id,
                submitted_by=r1.id,
                submitted_at=now - timedelta(days=3),
                client_decision="shortlisted",
                decided_by=c1.id,
                decided_at=now - timedelta(hours=18),
                proposed_slot=now + timedelta(days=2, hours=4),
            )
            java_apps[1].stage = "interview"
            db.add(sub1)
            db.add(
                PipelineEvent(
                    application_id=java_apps[1].id,
                    from_stage="submitted",
                    to_stage="interview",
                    actor_id=c1.id,
                    note="Technical round 1 scheduled with Lead Architect.",
                )
            )

            # Candidate 2: Client Rejected with reason
            sub2 = Submission(
                application_id=java_apps[2].id,
                submitted_by=r1.id,
                submitted_at=now - timedelta(days=2),
                client_decision="rejected",
                reject_reason="Notice period exceeds our project milestone deadline.",
                decided_by=c1.id,
                decided_at=now - timedelta(hours=8),
            )
            java_apps[2].stage = "rejected"
            db.add(sub2)
            db.add(
                PipelineEvent(
                    application_id=java_apps[2].id,
                    from_stage="submitted",
                    to_stage="rejected",
                    actor_id=c1.id,
                    note="Client declined: notice period exceeds project milestone deadline.",
                )
            )

            # Candidate 3: Pending review in client portal
            sub3 = Submission(
                application_id=java_apps[3].id,
                submitted_by=r1.id,
                submitted_at=now - timedelta(hours=4),
                client_decision="pending",
            )
            java_apps[3].stage = "submitted"
            db.add(sub3)
            db.add(
                PipelineEvent(
                    application_id=java_apps[3].id,
                    from_stage="screened",
                    to_stage="submitted",
                    actor_id=r1.id,
                    note="Submitted to Apex client portal for review.",
                )
            )

        # B) Lead DevOps (Apex)
        devops_apps_res = await db.execute(
            select(Application).where(Application.requisition_id == req_devops.id)
        )
        devops_apps = devops_apps_res.scalars().all()
        if devops_apps:
            sub_d = Submission(
                application_id=devops_apps[0].id,
                submitted_by=r1.id,
                submitted_at=now - timedelta(hours=6),
                client_decision="pending",
            )
            devops_apps[0].stage = "submitted"
            db.add(sub_d)
            db.add(
                PipelineEvent(
                    application_id=devops_apps[0].id,
                    from_stage="screened",
                    to_stage="submitted",
                    actor_id=r1.id,
                    note="Submitted to Apex client portal for SRE review.",
                )
            )

        # C) KYC Analyst (Zenith - Priya Sharma)
        kyc_apps_res = await db.execute(
            select(Application).where(Application.requisition_id == req_kyc.id)
        )
        kyc_apps = kyc_apps_res.scalars().all()
        if len(kyc_apps) >= 2:
            sub_k0 = Submission(
                application_id=kyc_apps[0].id,
                submitted_by=r2.id,
                submitted_at=now - timedelta(days=2),
                client_decision="shortlisted",
                decided_by=c2.id,
                decided_at=now - timedelta(days=1),
                proposed_slot=now + timedelta(days=3, hours=2),
            )
            kyc_apps[0].stage = "interview"
            db.add(sub_k0)
            db.add(
                PipelineEvent(
                    application_id=kyc_apps[0].id,
                    from_stage="submitted",
                    to_stage="interview",
                    actor_id=c2.id,
                    note="AML compliance interview scheduled.",
                )
            )

            sub_k1 = Submission(
                application_id=kyc_apps[1].id,
                submitted_by=r2.id,
                submitted_at=now - timedelta(hours=10),
                client_decision="pending",
            )
            kyc_apps[1].stage = "submitted"
            db.add(sub_k1)

        # D) Full Stack (CloudScale - Ananya Verma)
        fs_apps_res = await db.execute(
            select(Application).where(Application.requisition_id == req_fullstack.id)
        )
        fs_apps = fs_apps_res.scalars().all()
        if fs_apps:
            sub_f0 = Submission(
                application_id=fs_apps[0].id,
                submitted_by=r2.id,
                submitted_at=now - timedelta(hours=3),
                client_decision="pending",
            )
            fs_apps[0].stage = "submitted"
            db.add(sub_f0)

        await db.commit()

        # Print summary of generated data
        print("\n=== Seeding Summary ===")
        user_cnt = (await db.execute(select(User))).scalars().all()
        client_cnt = (await db.execute(select(Client))).scalars().all()
        req_cnt = (await db.execute(select(Requisition))).scalars().all()
        cand_cnt = (await db.execute(select(Candidate))).scalars().all()
        app_cnt = (await db.execute(select(Application))).scalars().all()
        sub_cnt = (await db.execute(select(Submission))).scalars().all()
        view_cnt = (await db.execute(select(ViewLog))).scalars().all()

        print(f"Clients: {len(client_cnt)}")
        print(f"Users: {len(user_cnt)} (Recruiters & Client Reviewers)")
        print(f"Requisitions: {len(req_cnt)}")
        print(f"Candidates: {len(cand_cnt)}")
        print(f"Applications: {len(app_cnt)}")
        print(f"Submissions to Clients: {len(sub_cnt)}")
        print(f"Audit ViewLogs: {len(view_cnt)}")
        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
