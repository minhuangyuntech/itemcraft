from django.db import migrations


MAIN_DIMENSION = "AI政策法制"
SUB_DIMENSION = "AI法規與資安風險管理"


REFERENCES = [
    (
        10,
        "AI法規與資安風險管理命題總原則",
        "建立公務人員對AI應用之資安、個人資料保護、機敏資料防護、使用紀錄及合規控管之風險辨識與實務判斷能力。",
    ),
    (
        24,
        "24.資安規範與資料保護",
        "評估公務人員能否辨識雲端服務、機關核准之封閉式地端部署或內部系統在資料處理、儲存、日誌紀錄、對話紀錄保存及模型訓練或微調使用上之差異，並建立正確之資安與法遵意識。強化「影子AI(Shadow AI)」風險意識，提醒公務人員不得私自使用未經機關核准之外部AI工具處理涉及公務應保密、個人資料、營業秘密或未經機關同意公開之資訊。評測宜透過具體之禁止或不宜輸入範例(負面表列範例)，如未公開之採購底價、國民身分證統一編號、未發布之政策草案、內部簽辦意見或其他機關機敏資料，強化防範資料外洩風險之實務判斷能力。",
    ),
    (
        25,
        "25.AI法規與資安風險管理實務",
        "評估公務人員落實資安規範與風險管控之能力。導入AI國際管理體系(如 ISO 42001)觀念，評估其在公務流程中落實「事前風險評估」、「使用日誌稽核」與「合規性審查」等控管程序之實務素養。評估公務人員於AI相關採購、委外開發或服務導入時，是否能辨識契約應納入之AI使用管理要求，包括資料不得外流、訓練資料來源合法性、個人資料與機敏資料保護、使用日誌保存、模型更新管理、成果驗收、資安責任，以及承商應遵守機關AI使用規範與內控管理機制。",
    ),
    (
        26,
        "26.生成式AI使用限制與適法性",
        "評估公務人員能否依據「人工智慧基本法」及「行政院及所屬機關(構)使用生成式AI參考指引」等，判斷生成式AI使用之合法性與風險。公務人員應理解機密文書、未公開公務資訊、個人資料、營業秘密及未經機關同意公開之資料，不得輸入外部生成式AI服務；機密文書應由業務承辦人親自撰寫，不得使用生成式AI代為產製。AI 產出須經承辦人查證與專業判斷，不得未經確認即直接作成行政行為，亦不得作為公務決策之唯一依據。",
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
        ("questions", "0008_itemwritingreference"),
    ]

    operations = [
        migrations.RunPython(seed_references, remove_references),
    ]

