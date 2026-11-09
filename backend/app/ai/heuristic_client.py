import re
from typing import Any

COMMON_SKILLS = [
    "java",
    "spring boot",
    "spring",
    "hibernate",
    "microservices",
    "python",
    "fastapi",
    "django",
    "react",
    "typescript",
    "javascript",
    "node.js",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "sql",
    "postgresql",
    "mongodb",
    "redis",
    "kafka",
    "rest api",
    "rest apis",
    "graphql",
    "kyc",
    "aml",
    "compliance",
    "excel",
    "banking",
    "finance",
    "retail",
]


class HeuristicClient:
    """Heuristic keyword-based client when GEMINI_API_KEY is not configured."""

    async def extract_jd(self, jd_text: str) -> dict[str, Any]:
        text_lower = jd_text.lower()

        # Guess title
        title = "Job Requisition"
        first_lines = [line.strip() for line in jd_text.splitlines() if line.strip()]
        if first_lines:
            candidate_title = first_lines[0]
            if len(candidate_title) < 60:
                title = candidate_title

        if "senior java" in text_lower:
            title = "Senior Java Developer"
        elif "kyc" in text_lower:
            title = "KYC Analyst"
        elif "java" in text_lower:
            title = "Java Developer"

        criteria = []

        # Experience criterion
        exp_match = re.search(r"(\d+)(?:\s*-\s*|\s+to\s+)(\d+)\s*(?:years?|yrs?)", text_lower)
        if exp_match:
            min_yrs = float(exp_match.group(1))
            max_yrs = float(exp_match.group(2))
            criteria.append(
                {
                    "name": f"Total Experience ({int(min_yrs)}-{int(max_yrs)} years)",
                    "kind": "experience",
                    "must_have": True,
                    "weight": 5,
                    "params": {"min": min_yrs, "max": max_yrs},
                    "description": f"Must have between {min_yrs} and {max_yrs} years of relevant experience",
                }
            )
        else:
            single_exp = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text_lower)
            if single_exp:
                min_yrs = float(single_exp.group(1))
                criteria.append(
                    {
                        "name": f"Experience ({int(min_yrs)}+ years)",
                        "kind": "experience",
                        "must_have": True,
                        "weight": 5,
                        "params": {"min": min_yrs, "max": min_yrs + 4},
                        "description": f"Minimum {min_yrs} years experience",
                    }
                )

        # Notice criterion
        notice_match = re.search(
            r"notice(?:\s+period)?(?:\s+of|\s+up\s+to|\s+max|\s+within)?\s*(\d+)\s*days?",
            text_lower,
        )
        if notice_match:
            max_days = int(notice_match.group(1))
            criteria.append(
                {
                    "name": f"Notice Period (<= {max_days} days)",
                    "kind": "notice",
                    "must_have": True,
                    "weight": 4,
                    "params": {"max_days": max_days},
                    "description": f"Available to join within {max_days} days",
                }
            )

        # Location criterion
        for loc in [
            "noida",
            "delhi",
            "gurugram",
            "gurgaon",
            "bangalore",
            "mumbai",
            "hyderabad",
            "pune",
            "remote",
        ]:
            if loc in text_lower:
                display_loc = "Noida" if loc == "noida" else loc.title()
                criteria.append(
                    {
                        "name": f"Location ({display_loc})",
                        "kind": "location",
                        "must_have": False,
                        "weight": 2,
                        "params": {"city": display_loc},
                        "description": f"Candidate based in or willing to relocate to {display_loc}",
                    }
                )
                break

        # Skill criteria
        found_skills = [s for s in COMMON_SKILLS if s in text_lower]
        for skill in found_skills[:4]:
            skill_name = "Spring Boot" if skill == "spring boot" else skill.title()
            is_must = skill in ["java", "spring boot", "kyc", "python"]
            criteria.append(
                {
                    "name": skill_name,
                    "kind": "skill",
                    "must_have": is_must,
                    "weight": 4 if is_must else 3,
                    "params": {"skill": skill_name},
                    "description": f"Strong hands-on experience with {skill_name}",
                }
            )

        # Domain criteria
        for dom in ["banking", "retail", "fintech", "insurance", "it services"]:
            if dom in text_lower:
                criteria.append(
                    {
                        "name": f"{dom.title()} Domain",
                        "kind": "domain",
                        "must_have": False,
                        "weight": 2,
                        "params": {"domain": dom.title()},
                        "description": f"Prior experience in {dom.title()} domain",
                    }
                )
                break

        return {"title": title, "criteria": criteria}

    async def extract_profile(self, resume_text: str) -> dict[str, Any]:
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        name = "Candidate"
        if lines:
            # First clean line without labels
            first = lines[0]
            if len(first.split()) <= 4 and not any(
                k in first.lower() for k in ["curriculum", "resume", "cv", "page"]
            ):
                name = first

        # Regex email
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resume_text)
        email = email_match.group(0) if email_match else ""

        # Regex phone
        phone_match = re.search(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", resume_text
        )
        phone = phone_match.group(0) if phone_match else ""

        # Location
        location = ""
        for loc in [
            "Noida",
            "Delhi",
            "Gurgaon",
            "Bangalore",
            "Bengaluru",
            "Mumbai",
            "Hyderabad",
            "Pune",
        ]:
            if re.search(rf"\b{loc}\b", resume_text, re.IGNORECASE):
                location = loc
                break

        # Skills
        text_lower = resume_text.lower()
        skills = [s.title() for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s)}\b", text_lower)]

        # Experience years
        exp_match = re.search(
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", text_lower
        )
        experience_years = float(exp_match.group(1)) if exp_match else 0.0

        # Notice days
        notice_days = 0
        notice_match = re.search(
            r"notice(?:\s+period)?(?:\s*[:=-])?\s*(\d+)\s*(?:days?|months?)", text_lower
        )
        if notice_match:
            val = int(notice_match.group(1))
            unit = notice_match.group(0).lower()
            notice_days = val * 30 if "month" in unit else val
        elif "immediate" in text_lower or "serving notice" in text_lower:
            notice_days = 15

        current_role = ""
        for role_hint in [
            "Senior Java Developer",
            "Java Developer",
            "KYC Analyst",
            "Software Engineer",
            "Backend Developer",
        ]:
            if role_hint.lower() in text_lower:
                current_role = role_hint
                break

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "current_role": current_role or (name + " - Professional"),
            "skills": skills,
            "employment": [],
            "experience_years": experience_years,
            "notice_days": notice_days,
            "current_ctc": "",
            "expected_ctc": "",
            "education": [],
        }

    async def judge(
        self,
        masked_text: str,
        criteria: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results = []

        for crit in criteria:
            crit_id = crit.get("id") or crit.get("criterion_id", 0)
            kind = crit.get("kind", "")
            if kind in ("experience", "notice", "location"):
                continue  # Evaluated by code in scoring.py

            # Target skill or domain to match
            skill = crit.get("params", {}).get("skill", "")
            domain = crit.get("params", {}).get("domain", "")
            target = skill or domain or crit.get("name", "")
            target_clean = target.strip().lower()

            keywords = [k.strip() for k in re.split(r"&|/|,|\band\b|\bor\b", target_clean) if len(k.strip()) >= 3]
            if not keywords:
                keywords = [target_clean]

            match = None
            for kw in keywords:
                pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
                m = pattern.search(masked_text)
                if m:
                    match = m
                    break

            if match:
                # Find the sentence or line containing this match to use as exact quote
                start_pos = match.start()
                end_pos = match.end()

                # Expand left to start of line
                line_start = masked_text.rfind("\n", 0, start_pos)
                if line_start == -1:
                    line_start = max(0, start_pos - 40)
                else:
                    line_start += 1

                # Expand right to end of line
                line_end = masked_text.find("\n", end_pos)
                if line_end == -1:
                    line_end = min(len(masked_text), end_pos + 40)

                exact_quote = masked_text[line_start:line_end].strip()
                if not exact_quote:
                    slice_start = max(0, start_pos - 20)
                    slice_end = min(len(masked_text), end_pos + 20)
                    exact_quote = masked_text[slice_start:slice_end].strip()

                results.append(
                    {
                        "criterion_id": crit_id,
                        "verdict": "met",
                        "quote": exact_quote,
                        "confidence": 0.90,
                    }
                )
            else:
                results.append(
                    {
                        "criterion_id": crit_id,
                        "verdict": "not_found",
                        "quote": None,
                        "confidence": 0.85,
                    }
                )

        return results
