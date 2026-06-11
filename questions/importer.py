import re
from io import BytesIO

import pandas as pd

from .models import ImportJob, OptionGroup, OptionItem, Question


COLUMN_ALIASES = {
    "type_option": ["類型", "題型", "type"],
    "status_option": ["狀態", "status"],
    "original_domain": ["原AIE領域範疇", "原AI領域範疇", "原 AI 領域範疇", "領域", "範疇"],
    "combined_question": ["題目(包含選項)", "題目內容", "題目", "原題"],
    "answer": ["答案", "原答案"],
    "combined_revised_question": ["新題目(包含選項)", "新題目內容", "新題目"],
    "revised_answer": ["新答案"],
    "revised_explanation": ["新解析", "解析"],
    "difficulty": ["難易度", "難度"],
    "main_dimension": ["主層面"],
    "sub_dimension": ["次層面"],
    "certification_note": ["認證內容說明"],
    "classification_basis": ["分類依據"],
}


def normalize_header(value):
    return re.sub(r"[\s　()（）]", "", str(value or "")).lower()


def find_column(columns, aliases):
    normalized = {normalize_header(col): col for col in columns}
    for alias in aliases:
        match = normalized.get(normalize_header(alias))
        if match:
            return match
    return None


def read_uploaded_table(uploaded_file):
    suffix = uploaded_file.name.lower().rsplit(".", 1)[-1]
    content = uploaded_file.read()
    if suffix == "csv":
        return pd.read_csv(BytesIO(content))
    return pd.read_excel(BytesIO(content))


def clean_cell(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def split_question_block(text):
    text = clean_cell(text)
    if not text:
        return {"stem": "", "A": "", "B": "", "C": "", "D": ""}

    pattern = re.compile(r"(?P<label>[ABCD])[\.\)、）]\s*", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return {"stem": text, "A": "", "B": "", "C": "", "D": ""}

    stem = text[: matches[0].start()].strip()
    parts = {"stem": stem, "A": "", "B": "", "C": "", "D": ""}
    for index, match in enumerate(matches):
        label = match.group("label").upper()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        parts[label] = text[start:end].strip()
    return parts


def option_for(group_key, name):
    name = clean_cell(name)
    if not name:
        return None
    group, _ = OptionGroup.objects.get_or_create(key=group_key, defaults={"name": group_key})
    option, _ = OptionItem.objects.get_or_create(group=group, name=name)
    return option


def import_questions(uploaded_file):
    df = read_uploaded_table(uploaded_file)
    df = df.dropna(how="all")
    mapping = {
        target: find_column(df.columns, aliases)
        for target, aliases in COLUMN_ALIASES.items()
    }
    job = ImportJob.objects.create(file_name=uploaded_file.name, total_rows=len(df))
    imported = 0
    errors = 0

    for _, row in df.iterrows():
        try:
            original = split_question_block(clean_cell(row.get(mapping["combined_question"], "")))
            revised = split_question_block(clean_cell(row.get(mapping["combined_revised_question"], "")))
            Question.objects.create(
                type_option=option_for("type", row.get(mapping["type_option"], "")),
                status_option=option_for("status", row.get(mapping["status_option"], "")),
                original_domain=clean_cell(row.get(mapping["original_domain"], "")),
                stem=original["stem"],
                choice_a=original["A"],
                choice_b=original["B"],
                choice_c=original["C"],
                choice_d=original["D"],
                answer=clean_cell(row.get(mapping["answer"], "")).upper()[:1],
                revised_stem=revised["stem"],
                revised_choice_a=revised["A"],
                revised_choice_b=revised["B"],
                revised_choice_c=revised["C"],
                revised_choice_d=revised["D"],
                revised_answer=clean_cell(row.get(mapping["revised_answer"], "")).upper()[:1],
                revised_explanation=clean_cell(row.get(mapping["revised_explanation"], "")),
                difficulty=clean_cell(row.get(mapping["difficulty"], "")),
                main_dimension=clean_cell(row.get(mapping["main_dimension"], "")),
                sub_dimension=clean_cell(row.get(mapping["sub_dimension"], "")),
                certification_note=clean_cell(row.get(mapping["certification_note"], "")),
                classification_basis=clean_cell(row.get(mapping["classification_basis"], "")),
            )
            imported += 1
        except Exception:
            errors += 1

    job.imported_rows = imported
    job.error_rows = errors
    job.save(update_fields=["imported_rows", "error_rows"])
    return job, mapping
