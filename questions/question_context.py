from .models import ItemWritingReference, Question


def build_question_table_context(limit=50):
    limit = max(1, min(int(limit or 50), 200))
    rows = []
    questions = Question.objects.select_related("type_option", "status_option").order_by("-updated_at", "-id")[:limit]
    for question in questions:
        rows.append(
            {
                "id": question.id,
                "completed": question.is_completed,
                "type": question.type_option.name if question.type_option else "",
                "status": question.status_option.name if question.status_option else "",
                "original_domain": question.original_domain,
                "difficulty": question.difficulty,
                "stem": question.stem,
                "choices": {
                    "A": question.choice_a,
                    "B": question.choice_b,
                    "C": question.choice_c,
                    "D": question.choice_d,
                },
                "answer": question.answer,
                "explanation": question.revised_explanation,
                "main_dimension": question.main_dimension,
                "sub_dimension": question.sub_dimension,
                "certification_note": question.certification_note,
                "classification_basis": question.classification_basis,
            }
        )
    lines = [
        "以下是目前題庫資料表摘要。若要修改既有題目，請使用 id 指定題目。",
        "completed=true 的題目已完成鎖定，不能修改。",
    ]
    for row in rows:
        lines.extend(
            [
                f"\nID: {row['id']} | completed: {row['completed']} | type: {row['type']} | status: {row['status']} | difficulty: {row['difficulty']}",
                f"原AIE領域範疇: {row['original_domain']}",
                f"題幹: {row['stem']}",
                f"A: {row['choices']['A']}",
                f"B: {row['choices']['B']}",
                f"C: {row['choices']['C']}",
                f"D: {row['choices']['D']}",
                f"答案: {row['answer']}",
                f"解析: {row['explanation']}",
                f"主層面: {row['main_dimension']}",
                f"次層面: {row['sub_dimension']}",
                f"認證內容說明: {row['certification_note']}",
                f"分類依據: {row['classification_basis']}",
            ]
        )
    return "\n".join(lines), len(rows)


def build_item_writing_reference_context():
    references = ItemWritingReference.objects.filter(is_active=True)
    lines = ["以下是命題參考資料，命題與審題時應依照對應主層面與次層面使用。"]
    count = 0
    for reference in references:
        count += 1
        lines.extend(
            [
                f"\n主層面: {reference.main_dimension}",
                f"次層面: {reference.sub_dimension}",
                f"標題: {reference.title}",
                f"內容: {reference.content}",
            ]
        )
    return "\n".join(lines), count
