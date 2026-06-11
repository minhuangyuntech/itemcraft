from django.db import models


class OptionGroup(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OptionItem(models.Model):
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=20, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group__name", "sort_order", "name"]
        unique_together = [("group", "name")]

    def __str__(self):
        return self.name


class Question(models.Model):
    ANSWER_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]
    ORIGINAL_DOMAIN_CHOICES = [
        ("資料隱私、資料安全與合規", "資料隱私、資料安全與合規"),
        ("資料偏見與公平性", "資料偏見與公平性"),
    ]
    DIFFICULTY_CHOICES = [
        ("基礎", "基礎"),
        ("進階", "進階"),
    ]
    SUB_DIMENSION_CHOICES = [
        ("AI法規與資安風險管理", "AI法規與資安風險管理"),
        ("AI應用下的倫理準則與智慧財產權實務", "AI應用下的倫理準則與智慧財產權實務"),
    ]

    type_option = models.ForeignKey(
        OptionItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="type_questions",
        verbose_name="類型",
    )
    status_option = models.ForeignKey(
        OptionItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_questions",
        verbose_name="狀態",
    )
    original_domain = models.CharField(
        "原AIE領域範疇",
        max_length=200,
        choices=ORIGINAL_DOMAIN_CHOICES,
        blank=True,
    )
    stem = models.TextField("題幹", blank=True)
    choice_a = models.TextField("選項 A", blank=True)
    choice_b = models.TextField("選項 B", blank=True)
    choice_c = models.TextField("選項 C", blank=True)
    choice_d = models.TextField("選項 D", blank=True)
    answer = models.CharField("答案", max_length=1, choices=ANSWER_CHOICES, blank=True)
    revised_stem = models.TextField("新題幹", blank=True)
    revised_choice_a = models.TextField("新選項 A", blank=True)
    revised_choice_b = models.TextField("新選項 B", blank=True)
    revised_choice_c = models.TextField("新選項 C", blank=True)
    revised_choice_d = models.TextField("新選項 D", blank=True)
    revised_answer = models.CharField("新答案", max_length=1, choices=ANSWER_CHOICES, blank=True)
    revised_explanation = models.TextField("解析", blank=True)
    difficulty = models.CharField("難易度", max_length=80, choices=DIFFICULTY_CHOICES, blank=True)
    main_dimension = models.CharField("主層面", max_length=160, default="AI政策法制", blank=True)
    sub_dimension = models.CharField("次層面", max_length=160, choices=SUB_DIMENSION_CHOICES, blank=True)
    certification_note = models.TextField("認證內容說明", blank=True)
    classification_basis = models.TextField("分類依據", blank=True)
    is_completed = models.BooleanField("已完成鎖定", default=False)
    completed_at = models.DateTimeField("完成時間", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.stem[:60] or f"Question #{self.pk}"


class ReferenceSource(models.Model):
    title = models.CharField("來源名稱", max_length=200)
    url = models.URLField("來源網址", blank=True)
    citation_note = models.TextField("引用資訊", blank=True)
    accessed_on = models.DateField("存取日期", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ReferenceFile(models.Model):
    source = models.ForeignKey(
        ReferenceSource,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="files",
    )
    title = models.CharField("檔案名稱", max_length=200)
    file = models.FileField("參考檔案", upload_to="references/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class ItemWritingReference(models.Model):
    main_dimension = models.CharField("主層面", max_length=160, default="AI政策法制")
    sub_dimension = models.CharField("次層面", max_length=160)
    title = models.CharField("標題", max_length=200)
    content = models.TextField("命題參考內容")
    sort_order = models.PositiveIntegerField("排序", default=0)
    is_active = models.BooleanField("啟用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["main_dimension", "sub_dimension", "sort_order", "id"]
        unique_together = [("main_dimension", "sub_dimension", "title")]

    def __str__(self):
        return f"{self.sub_dimension} - {self.title}"


class AIProviderSetting(models.Model):
    name = models.CharField("名稱", max_length=120, unique=True, default="Default")
    provider = models.CharField("Provider", max_length=80, default="OpenAI")
    model = models.CharField("預設 Model", max_length=120, blank=True)
    base_url = models.URLField("Base URL", blank=True)
    api_key = models.CharField("API Key", max_length=500, blank=True)
    is_active = models.BooleanField("啟用", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AIModel(models.Model):
    api_setting = models.ForeignKey(AIProviderSetting, on_delete=models.CASCADE, related_name="models")
    model_id = models.CharField("Model ID", max_length=200)
    display_name = models.CharField("顯示名稱", max_length=200, blank=True)
    is_active = models.BooleanField("啟用", default=True)
    loaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["api_setting__name", "model_id"]
        unique_together = [("api_setting", "model_id")]

    def __str__(self):
        return f"{self.api_setting.name} / {self.display_name or self.model_id}"


class ImportJob(models.Model):
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} ({self.imported_rows}/{self.total_rows})"


class DatabaseBackup(models.Model):
    reason = models.CharField("備份原因", max_length=200)
    file_path = models.CharField("備份檔案", max_length=500)
    created_by = models.CharField("建立者", max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reason} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class AIDatabaseOperation(models.Model):
    backup = models.ForeignKey(DatabaseBackup, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.TextField("提示詞")
    response = models.TextField("AI 回覆", blank=True)
    summary = models.TextField("執行摘要", blank=True)
    created_by = models.CharField("執行者", max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI DB Operation #{self.pk}"
