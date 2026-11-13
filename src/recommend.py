"""
src/recommend.py
----------------
Rule-based personalized recommendations engine for the Student Performance Predictor.

Functions
---------
generate_recommendations(category, input_features)
    Return a list of recommendation dicts based on the prediction category
    and the student's input feature values.
"""

from __future__ import annotations

RULE_SETS: dict[str, dict] = {
    "At-Risk": {
        "base": [
            {
                "priority": "high",
                "category": "academic",
                "title": "Immediate Academic Intervention",
                "description": (
                    "This student is flagged as At-Risk of failing. "
                    "Immediate, targeted intervention is critical."
                ),
                "action": (
                    "Schedule an urgent meeting with the student. "
                    "Assign a peer tutor or academic mentor."
                ),
            }
        ],
        "rules": [
            {
                "condition": lambda f: f.get("G1", 20) < 8,
                "recommendation": {
                    "priority": "high",
                    "category": "academic",
                    "title": "Core Subject Tutoring Required",
                    "description": (
                        "First-period grade is critically low (below 8/20), "
                        "indicating a fundamental knowledge gap."
                    ),
                    "action": (
                        "Enroll student in a remedial support program. "
                        "Conduct a diagnostic assessment to identify specific weaknesses."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("absences", 0) > 10,
                "recommendation": {
                    "priority": "high",
                    "category": "attendance",
                    "title": "Critical Attendance Problem",
                    "description": (
                        "Excessive absences (>10) are severely impacting "
                        "academic performance."
                    ),
                    "action": (
                        "Contact parents or guardian immediately. "
                        "Investigate underlying causes (health, transport, motivation). "
                        "Create a supervised attendance recovery plan."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("failures", 0) > 1,
                "recommendation": {
                    "priority": "high",
                    "category": "behavioral",
                    "title": "Repeated Failure History",
                    "description": (
                        "Multiple past class failures suggest systemic challenges "
                        "that go beyond a single subject."
                    ),
                    "action": (
                        "Refer to the school counsellor. "
                        "Assess for learning difficulties. "
                        "Develop an Individualized Education Plan (IEP)."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("studytime", 4) < 2,
                "recommendation": {
                    "priority": "high",
                    "category": "study",
                    "title": "Critically Low Study Time",
                    "description": (
                        "Student studies less than 2 hours per week, "
                        "which is insufficient for academic recovery."
                    ),
                    "action": (
                        "Introduce a structured daily study schedule. "
                        "Explore after-school supervised study sessions."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("assignment_rate", 100) < 60,
                "recommendation": {
                    "priority": "high",
                    "category": "academic",
                    "title": "Low Assignment Submission Rate",
                    "description": (
                        "Student is missing significant homework or coursework assignments (<60% completed)."
                    ),
                    "action": (
                        "Institute assignment tracking checklists and offer structured homework support."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("assessment_trend", 0) < 0,
                "recommendation": {
                    "priority": "high",
                    "category": "academic",
                    "title": "Downward Assessment Trend",
                    "description": (
                        "Recent test and assessment scores indicate a declining performance trajectory."
                    ),
                    "action": (
                        "Conduct early check-in before the next examination to review difficult topics."
                    ),
                },
            },
        ],
    },
    "Needs Improvement": {
        "base": [
            {
                "priority": "medium",
                "category": "academic",
                "title": "Academic Improvement Plan",
                "description": (
                    "Student is performing below expectations. "
                    "Targeted support can prevent further decline."
                ),
                "action": (
                    "Create a personalised 4-week improvement plan. "
                    "Schedule monthly progress check-ins."
                ),
            }
        ],
        "rules": [
            {
                "condition": lambda f: f.get("studytime", 4) < 2,
                "recommendation": {
                    "priority": "medium",
                    "category": "study",
                    "title": "Increase Weekly Study Time",
                    "description": (
                        "Current study time is below recommended levels "
                        "(less than 2 hours/week)."
                    ),
                    "action": (
                        "Encourage 2–5 hours of focused study per week. "
                        "Share time management techniques and study skills resources."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("absences", 0) > 5,
                "recommendation": {
                    "priority": "medium",
                    "category": "attendance",
                    "title": "Improve Class Attendance",
                    "description": (
                        "Above-average absences are negatively affecting "
                        "continuity of learning."
                    ),
                    "action": (
                        "Discuss the impact of absences with the student. "
                        "Set a monthly attendance goal and review progress."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("G1", 20) < 12,
                "recommendation": {
                    "priority": "medium",
                    "category": "academic",
                    "title": "Focus on Core Grade Improvement",
                    "description": (
                        "First-period grade is below class average, "
                        "indicating room for improvement."
                    ),
                    "action": (
                        "Identify weaker subject areas via formative assessment. "
                        "Provide targeted practice materials and worked examples."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("failures", 0) >= 1,
                "recommendation": {
                    "priority": "medium",
                    "category": "behavioral",
                    "title": "Address Past Failure Patterns",
                    "description": (
                        "At least one past class failure has been recorded, "
                        "which increases risk if unaddressed."
                    ),
                    "action": (
                        "Review what led to previous failures. "
                        "Establish a support structure to prevent recurrence."
                    ),
                },
            },
        ],
    },
    "Performing Well": {
        "base": [
            {
                "priority": "low",
                "category": "academic",
                "title": "Maintain Strong Performance",
                "description": (
                    "Student is performing well. Encourage continued effort "
                    "and engagement."
                ),
                "action": (
                    "Acknowledge achievements formally. "
                    "Consider recommending advanced coursework or enrichment activities."
                ),
            }
        ],
        "rules": [
            {
                "condition": lambda f: f.get("absences", 0) > 15,
                "recommendation": {
                    "priority": "high",
                    "category": "attendance",
                    "title": "Critical Attendance Disqualification Warning",
                    "description": (
                        "Student has critically high missed classes (>15 absences recorded). "
                        "Despite strong test grades, extreme absenteeism risks mandatory course debarment."
                    ),
                    "action": (
                        "Issue urgent attendance notice to student/guardian. "
                        "Mandate attendance recovery or medical excuse verification."
                    ),
                },
            },
            {
                "condition": lambda f: 3 < f.get("absences", 0) <= 15,
                "recommendation": {
                    "priority": "low",
                    "category": "attendance",
                    "title": "Monitor Attendance Consistency",
                    "description": (
                        "Some absences noted. Maintaining attendance "
                        "will help sustain current performance."
                    ),
                    "action": (
                        "Gently remind student of the link between "
                        "attendance and long-term academic success."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("failures", 0) >= 1,
                "recommendation": {
                    "priority": "medium",
                    "category": "behavioral",
                    "title": "Monitor Prior Academic Inconsistencies",
                    "description": (
                        "Student has recorded past course failures. While current scores are high, "
                        "prior setbacks suggest vulnerability under increased exam stress."
                    ),
                    "action": (
                        "Conduct regular progress check-ins to ensure momentum is maintained into finals."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("studytime", 4) < 2,
                "recommendation": {
                    "priority": "medium",
                    "category": "study",
                    "title": "Structure Independent Study Time",
                    "description": (
                        "Reported study time is under 2 hours per week. High test scores may not be sustainable "
                        "in advanced topics without consistent independent study."
                    ),
                    "action": (
                        "Encourage 2–5 hours of weekly focused study to build long-term retention."
                    ),
                },
            },
            {
                "condition": lambda f: f.get("studytime", 4) >= 3,
                "recommendation": {
                    "priority": "low",
                    "category": "study",
                    "title": "Leverage High Study Effort",
                    "description": (
                        "Strong study habits are a key driver of this student's success."
                    ),
                    "action": (
                        "Encourage participation in academic competitions or peer tutoring roles "
                        "to further develop skills."
                    ),
                },
            },
        ],
    },
}


def generate_recommendations(
    category: str,
    input_features: dict,
    max_results: int = 5,
) -> list[dict]:
    """
    Generate personalised recommendations for a student prediction.

    Parameters
    ----------
    category : str
        One of "At-Risk", "Needs Improvement", "Performing Well".
    input_features : dict
        The feature values used in the prediction.
    max_results : int
        Maximum number of recommendations to return (default 5).

    Returns
    -------
    list[dict]
        List of recommendation dicts, ordered by priority
        (high -> medium -> low), deduplicated, capped at max_results.
    """
    rule_set = RULE_SETS.get(category, RULE_SETS["Needs Improvement"])
    results: list[dict] = list(rule_set["base"])

    for rule in rule_set["rules"]:
        try:
            if rule["condition"](input_features):
                results.append(rule["recommendation"])
        except Exception:
            continue

    seen: set[str] = set()
    unique: list[dict] = []
    for rec in results:
        if rec["title"] not in seen:
            seen.add(rec["title"])
            unique.append(rec)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique.sort(key=lambda r: priority_order.get(r["priority"], 99))

    return unique[:max_results]
