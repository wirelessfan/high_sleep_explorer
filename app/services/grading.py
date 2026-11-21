"""判分逻辑。"""
from __future__ import annotations

from typing import Any


def grade_quiz(questions: list[dict], answers: dict[str, int], multi_answers: dict[str, list[int]] | None = None) -> dict:
    """选择题判分。answers: {question_id: option_index}"""
    multi_answers = multi_answers or {}
    details = []
    correct = 0
    for q in questions:
        qid = q["id"]
        qtype = q.get("qtype", "choice")
        picked = answers.get(qid)
        if qtype == "multi_choice":
            selected = multi_answers.get(qid)
            expected = q.get("answer_indices")
            valid = (isinstance(selected, list) and bool(selected)
                     and all(type(x) is int and 0 <= x < len(q["options"]) for x in selected)
                     and len(set(selected)) == len(selected)
                     and isinstance(expected, list) and bool(expected)
                     and all(type(x) is int and 0 <= x < len(q["options"]) for x in expected)
                     and len(set(expected)) == len(expected))
            is_right = valid and set(selected) == set(expected)
            detail = {"id": qid, "skill": q.get("skill", ""), "qtype": qtype,
                      "picked_indices": selected, "answer_indices": expected,
                      "correct": is_right, "explain": q.get("explain", "")}
        else:
            is_right = type(picked) is int and picked == q["answer"] and 0 <= picked < len(q.get("options", []))
            detail = {"id": qid, "skill": q.get("skill", ""), "picked": picked,
                      "answer": q["answer"], "correct": is_right,
                      "explain": q.get("explain", "")}
        if is_right:
            correct += 1
        details.append(detail)
    total = len(questions)
    return {
        "total": total,
        "correct": correct,
        "score": round(correct / total * 100) if total else 0,
        "details": details,
    }


def grade_levels(levels: list[dict], answers: dict[str, int], multi_answers: dict[str, list[int]] | None = None) -> dict:
    """闯关判分：按关卡分别计算，返回每关通过情况。"""
    level_results = []
    total_correct = 0
    total_count = 0
    for lv in levels:
        qs = lv["questions"]
        res = grade_quiz(qs, answers, multi_answers)
        passed = res["score"] >= 80
        total_correct += res["correct"]
        total_count += res["total"]
        level_results.append({
            "id": lv["id"],
            "name": lv["name"],
            "score": res["score"],
            "passed": passed,
            "details": res["details"],
        })
    return {
        "levels": level_results,
        "total": total_count,
        "correct": total_correct,
        "score": round(total_correct / total_count * 100) if total_count else 0,
        "all_passed": all(lv["passed"] for lv in level_results),
    }


def grade_myths(myths: list[dict], answers: dict[str, int]) -> dict:
    """误区小测：每题一个 check。"""
    details = []
    correct = 0
    for i, myth in enumerate(myths):
        chk = myth["check"]
        qid = f"m{i}"
        picked = answers.get(qid)
        is_right = picked is not None and picked == chk["answer"]
        if is_right:
            correct += 1
        details.append({
            "id": qid,
            "picked": picked,
            "answer": chk["answer"],
            "correct": is_right,
            "explain": chk.get("explain", ""),
        })
    total = len(myths)
    return {
        "total": total,
        "correct": correct,
        "score": round(correct / total * 100) if total else 0,
        "details": details,
    }


def grade_steps(problems: list[dict], answers: dict[str, int]) -> dict:
    """分步大题：每步一题，全部答完才算完成。"""
    details = []
    correct = 0
    total = 0
    for pi, prob in enumerate(problems):
        for si, step in enumerate(prob["steps"]):
            qid = f"p{pi}s{si}"
            total += 1
            picked = answers.get(qid)
            is_right = picked is not None and picked == step["answer"]
            if is_right:
                correct += 1
            details.append({
                "id": qid,
                "picked": picked,
                "answer": step["answer"],
                "correct": is_right,
                "explain": step.get("explain", ""),
            })
    return {
        "total": total,
        "correct": correct,
        "score": round(correct / total * 100) if total else 0,
        "details": details,
    }


def weak_skills(details: list[dict]) -> list[str]:
    """从判分明细里挑出答错的 skill，去重保序。"""
    out: list[str] = []
    for d in details:
        if not d.get("correct") and d.get("skill"):
            if d["skill"] not in out:
                out.append(d["skill"])
    return out


def grade_section(section: dict, answers: dict[str, int], multi_answers: dict[str, list[int]] | None = None) -> dict:
    """按版块类型分派。"""
    stype = section.get("type")
    if stype == "quiz":
        return grade_quiz(section["questions"], answers, multi_answers)
    if stype == "levels":
        return grade_levels(section["levels"], answers, multi_answers)
    if stype == "myths":
        return grade_myths(section["myths"], answers)
    if stype == "steps":
        return grade_steps(section["problems"], answers)
    if stype == "boss":
        return grade_quiz(section["questions"], answers, multi_answers)
    raise ValueError(f"不支持的版块类型: {stype}")




def flatten_details(result: dict) -> list[dict]:
    """从判分结果中提取全部逐题明细（levels 类型嵌套在 levels[].details 里）。"""
    details = list(result.get("details", []))
    for lv in result.get("levels", []):
        details.extend(lv.get("details", []))
    return details

def collect_skills(details: list[dict]) -> None:
    """占位：预留给后续按 skill 聚合统计。"""
    return None
