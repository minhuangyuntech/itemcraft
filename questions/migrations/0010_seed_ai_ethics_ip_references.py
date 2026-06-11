from django.db import migrations


MAIN_DIMENSION = "AI政策法制"
SUB_DIMENSION = "AI應用下的倫理準則與智慧財產權實務"


REFERENCES = [
    (
        10,
        "AI應用下的倫理準則與智慧財產權實務命題總原則",
        "提升公務人員對AI生成內容可信度、使用揭露、智慧財產權、行政倫理、責任歸屬及人類監督之實務判斷能力。",
    ),
    (
        27,
        "27.最終問責與行政倫理",
        "評估公務人員應用AI之倫理與問責素養，明確理解AI僅為輔助工具，最終行政處分、公文核定與業務決策仍應由權責人員負責。評估公務人員能否在AI輔助決策過程中，進行公平性、不歧視及社會影響檢核，並確保生成內容符合我國法制、政策語彙、在地語境與文化價值，避免用語誤植、脈絡錯置或價值表述不當。",
    ),
    (
        28,
        "28.智財權、授權條款與使用揭露",
        "評估公務人員判斷AI輔助生成內容，如圖文、簡報、影音或文案之著作權、授權條款及使用風險之能力；能區辨AI僅作為輔助工具且有人類實質創意投入，與AI獨立生成且缺乏人類創作投入之差異。公務發布內容前，應檢核資料來源、授權條款、合理使用可能性、人格權、肖像權及第三方權利，並依AI參與程度進行適當揭露或標記。",
    ),
    (
        29,
        "29.資料可信度與透明度",
        "辨別AI生成內容可能存在的錯誤、偏誤、幻覺與資訊過時之風險；評估公務人員對數位浮水印等內容鑑別機制之認知，確保具備辨識與防範深偽(Deepfake)造假及錯假訊息傳播之能力；並測驗其查核AI輔助決策結果之能力，以防範自動化偏誤，落實人機協作中之人類自主與監督。",
    ),
]


def seed_references(apps, schema_editor):
    ItemWritingReference = apps.get_model("questions", "ItemWritingReference")
    for sort_order, title, content in REFERENCES:
        ItemWritingReference.objects.update_or_create(
            main_dimension=MAIN_DIMENSION,
            sub_dimension=SUB_DIMENSION,
            title=title,
            defaults={
                "content": content,
                "sort_order": sort_order,
                "is_active": True,
            },
        )


def remove_references(apps, schema_editor):
    ItemWritingReference = apps.get_model("questions", "ItemWritingReference")
    ItemWritingReference.objects.filter(
        main_dimension=MAIN_DIMENSION,
        sub_dimension=SUB_DIMENSION,
        title__in=[title for _, title, _ in REFERENCES],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("questions", "0009_seed_ai_law_security_references"),
    ]

    operations = [
        migrations.RunPython(seed_references, remove_references),
    ]

