import json
import re

from django.utils import timezone

from .models import AIDatabaseOperation, OptionItem, Question


ALLOWED_UPDATE_FIELDS = {
    "type_option",
    "status_option",
    "original_domain",
    "stem",
    "choice_a",
    "choice_b",
    "choice_c",
    "choice_d",
    "answer",
    "revised_explanation",
    "difficulty",
    "main_dimension",
    "sub_dimension",
    "certification_note",
    "classification_basis",
}


def extract_json_actions(text):
    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    raw = fenced.group(1) if fenced else text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict) and isinstance(data.get("actions"), list):
        return data["actions"]
    if isinstance(data, list):
        return data
    return []


def option_by_name(group_key, name):
    if not name:
        return None
    return OptionItem.objects.filter(group__key=group_key, name=name, is_active=True).first()


def normalize_question_fields(fields):
    normalized = {}
    for key, value in fields.items():
        if key not in ALLOWED_UPDATE_FIELDS:
            continue
        if key == "type_option":
            normalized[key] = option_by_name("type", value)
        elif key == "status_option":
            normalized[key] = option_by_name("status", value)
        elif key == "answer":
            normalized[key] = str(value or "").strip().upper()[:1]
        else:
            normalized[key] = value or ""
    return normalized


def apply_ai_database_actions(actions, backup, prompt, response, user=None):
    created = 0
    updated = 0
    completed = 0
    skipped = []

    for index, action in enumerate(actions, start=1):
        action_type = action.get("action")
        if action_type == "create_question":
            fields = normalize_question_fields(action.get("fields", {}))
            choices = action.get("choices", {})
            if choices:
                fields.update(
                    {
                        "choice_a": choices.get("A", fields.get("choice_a", "")),
                        "choice_b": choices.get("B", fields.get("choice_b", "")),
                        "choice_c": choices.get("C", fields.get("choice_c", "")),
                        "choice_d": choices.get("D", fields.get("choice_d", "")),
                    }
                )
            Question.objects.create(**fields)
            created += 1
            continue

        question_id = action.get("id") or action.get("question_id")
        question = Question.objects.filter(pk=question_id).first()
        if not question:
            skipped.append(f"第 {index} 筆：找不到題目 {question_id}")
            continue
        if question.is_completed:
            skipped.append(f"題目 #{question.pk} 已完成鎖定，略過。")
            continue

        if action_type == "update_question":
            fields = normalize_question_fields(action.get("fields", {}))
            for field, value in fields.items():
                setattr(question, field, value)
            question.save()
            updated += 1
        elif action_type == "mark_completed":
            question.is_completed = True
            question.completed_at = timezone.now()
            question.save(update_fields=["is_completed", "completed_at", "updated_at"])
            completed += 1
        else:
            skipped.append(f"第 {index} 筆：不支援的操作 {action_type}")

    summary = "\n".join(
        [
            f"新增題目：{created}",
            f"更新題目：{updated}",
            f"標記完成：{completed}",
            f"略過：{len(skipped)}",
            *skipped,
        ]
    )
    AIDatabaseOperation.objects.create(
        backup=backup,
        prompt=prompt,
        response=response,
        summary=summary,
        created_by=getattr(user, "username", "") if user else "",
    )
    return summary

