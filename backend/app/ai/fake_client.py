from typing import Any


class FakeClient:
    """Deterministic Fake LLM client for testing with no network."""

    def __init__(
        self,
        canned_jd: dict[str, Any] | None = None,
        canned_profile: dict[str, Any] | None = None,
        canned_judgments: list[dict[str, Any]] | None = None,
        inject_hallucination: bool = False,
    ):
        self.canned_jd = canned_jd
        self.canned_profile = canned_profile
        self.canned_judgments = canned_judgments
        self.inject_hallucination = inject_hallucination
        self.calls: list[tuple[str, Any]] = []

    async def extract_jd(self, jd_text: str) -> dict[str, Any]:
        self.calls.append(("extract_jd", jd_text))
        if self.canned_jd is not None:
            return self.canned_jd

        return {
            "title": "Senior Java Developer",
            "criteria": [
                {
                    "name": "Java Experience",
                    "kind": "experience",
                    "must_have": True,
                    "weight": 5,
                    "params": {"min": 5, "max": 8},
                    "description": "5 to 8 years of Java experience",
                },
                {
                    "name": "Spring Boot",
                    "kind": "skill",
                    "must_have": True,
                    "weight": 4,
                    "params": {"skill": "Spring Boot"},
                    "description": "Hands on with Spring Boot microservices",
                },
                {
                    "name": "Notice Period",
                    "kind": "notice",
                    "must_have": True,
                    "weight": 3,
                    "params": {"max_days": 60},
                    "description": "Notice period 60 days or fewer",
                },
                {
                    "name": "Location",
                    "kind": "location",
                    "must_have": False,
                    "weight": 2,
                    "params": {"city": "Noida"},
                    "description": "Based in or willing to relocate to Noida",
                },
            ],
        }

    async def extract_profile(self, resume_text: str) -> dict[str, Any]:
        self.calls.append(("extract_profile", resume_text))
        if self.canned_profile is not None:
            return self.canned_profile

        return {
            "name": "Test Candidate",
            "email": "candidate@example.com",
            "phone": "+91 9876543210",
            "location": "Noida, India",
            "current_role": "Senior Software Engineer",
            "skills": ["Java", "Spring Boot", "Microservices", "Docker"],
            "employment": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start": "2020-01",
                    "end": "Present",
                },
                {
                    "title": "Software Engineer",
                    "company": "StartUp Labs",
                    "start": "2017-06",
                    "end": "2019-12",
                },
            ],
            "experience_years": 6.5,
            "notice_days": 30,
            "current_ctc": "18 LPA",
            "expected_ctc": "24 LPA",
            "education": [
                {"degree": "B.Tech Computer Science", "institution": "IIT", "year": "2017"}
            ],
        }

    async def judge(
        self,
        masked_text: str,
        criteria: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.calls.append(("judge", (masked_text, criteria)))
        if self.canned_judgments is not None:
            return self.canned_judgments

        results = []
        for crit in criteria:
            crit_id = crit.get("id") or crit.get("criterion_id", 0)
            name = crit.get("name", "").lower()
            skill = crit.get("params", {}).get("skill", "").lower()
            target = skill if skill else name

            if self.inject_hallucination:
                results.append(
                    {
                        "criterion_id": crit_id,
                        "verdict": "met",
                        "quote": "This is a hallucinated quote that does not appear anywhere in the CV.",
                        "confidence": 0.9,
                    }
                )
                continue

            # Check if target appears in masked_text
            if target and target in masked_text.lower():
                # Extract exact sentence or fragment containing target
                idx = masked_text.lower().find(target)
                start = max(0, idx - 15)
                end = min(len(masked_text), idx + len(target) + 15)
                exact_quote = masked_text[start:end].strip()

                results.append(
                    {
                        "criterion_id": crit_id,
                        "verdict": "met",
                        "quote": exact_quote,
                        "confidence": 0.95,
                    }
                )
            else:
                results.append(
                    {
                        "criterion_id": crit_id,
                        "verdict": "not_found",
                        "quote": None,
                        "confidence": 0.8,
                    }
                )

        return results
