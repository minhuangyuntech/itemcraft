from django import forms

from .ai_client import is_chat_completion_model
from .models import AIModel, AIProviderSetting, OptionItem, Question, ReferenceFile, ReferenceSource


CERTIFICATION_NOTE_BY_SUB_DIMENSION = {
    "AI法規與資安風險管理": "對應之AI安全、法規規範等內容",
    "AI應用下的倫理準則與智慧財產權實務": "對應之智慧財產權、AI倫理原則等內容",
}


def active_options(group_key):
    return OptionItem.objects.filter(group__key=group_key, is_active=True)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
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
            "is_completed",
        ]
        widgets = {
            "original_domain": forms.Select(),
            "difficulty": forms.Select(),
            "sub_dimension": forms.Select(),
            "stem": forms.Textarea(attrs={"rows": 4}),
            "choice_a": forms.Textarea(attrs={"rows": 2}),
            "choice_b": forms.Textarea(attrs={"rows": 2}),
            "choice_c": forms.Textarea(attrs={"rows": 2}),
            "choice_d": forms.Textarea(attrs={"rows": 2}),
            "revised_explanation": forms.Textarea(attrs={"rows": 5}),
            "certification_note": forms.Textarea(attrs={"rows": 3}),
            "classification_basis": forms.Textarea(attrs={"rows": 3}),
            "is_completed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type_option"].queryset = active_options("type")
        self.fields["status_option"].queryset = active_options("status")
        if not self.instance.pk:
            first_type = self.fields["type_option"].queryset.first()
            first_status = self.fields["status_option"].queryset.first()
            first_sub_dimension = Question.SUB_DIMENSION_CHOICES[0][0]
            if first_type:
                self.fields["type_option"].initial = first_type
            if first_status:
                self.fields["status_option"].initial = first_status
            self.fields["original_domain"].initial = Question.ORIGINAL_DOMAIN_CHOICES[0][0]
            self.fields["difficulty"].initial = Question.DIFFICULTY_CHOICES[0][0]
            self.fields["main_dimension"].initial = "AI政策法制"
            self.fields["sub_dimension"].initial = first_sub_dimension
            self.fields["certification_note"].initial = CERTIFICATION_NOTE_BY_SUB_DIMENSION[first_sub_dimension]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["type_option"].widget.attrs["class"] = "form-select"
        self.fields["status_option"].widget.attrs["class"] = "form-select"
        self.fields["original_domain"].widget.attrs["class"] = "form-select"
        self.fields["difficulty"].widget.attrs["class"] = "form-select"
        self.fields["sub_dimension"].widget.attrs["class"] = "form-select"
        self.fields["answer"].widget.attrs["class"] = "form-select"
        self.fields["is_completed"].widget.attrs["class"] = "form-check-input"


class OptionItemForm(forms.ModelForm):
    class Meta:
        model = OptionItem
        fields = ["group", "name", "color", "sort_order", "is_active"]
        widgets = {
            "group": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "color": forms.TextInput(attrs={"class": "form-control", "placeholder": "例如 #0d6efd"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ImportUploadForm(forms.Form):
    file = forms.FileField(
        label="Excel 或 CSV 檔案",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".xlsx,.xls,.csv"}),
    )


class DataBundleImportForm(forms.Form):
    file = forms.FileField(
        label="資料匯入檔",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".json"}),
    )


class AICommandForm(forms.Form):
    api_setting = forms.ModelChoiceField(
        label="API 來源",
        queryset=AIProviderSetting.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    prompt = forms.CharField(
        label="提示詞",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 6,
                "placeholder": "例如：請依選定參考來源產生 3 題四選一題目，並附答案與解析。",
            }
        ),
    )
    model = forms.ModelChoiceField(
        label="模型",
        queryset=AIModel.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    reference_sources = forms.ModelMultipleChoiceField(
        label="參考來源網址",
        queryset=ReferenceSource.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
    )
    reference_files = forms.ModelMultipleChoiceField(
        label="參考檔案",
        queryset=ReferenceFile.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
    )
    allow_database_changes = forms.BooleanField(
        label="允許 AI 直接修改題庫",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    include_question_table = forms.BooleanField(
        label="提供題庫資料表給 AI 讀取",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    question_limit = forms.IntegerField(
        label="讀取題目數",
        min_value=1,
        max_value=200,
        initial=50,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 200}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["api_setting"].queryset = AIProviderSetting.objects.filter(is_active=True)
        chat_model_ids = [
            model.pk
            for model in AIModel.objects.filter(is_active=True, api_setting__is_active=True)
            if is_chat_completion_model(model.model_id, model.api_setting)
        ]
        self.fields["model"].queryset = AIModel.objects.filter(pk__in=chat_model_ids).select_related("api_setting")
        self.fields["reference_sources"].queryset = ReferenceSource.objects.all()
        self.fields["reference_files"].queryset = ReferenceFile.objects.select_related("source")

    def clean(self):
        cleaned_data = super().clean()
        api_setting = cleaned_data.get("api_setting")
        model = cleaned_data.get("model")
        if api_setting and model and model.api_setting_id != api_setting.id:
            self.add_error("model", "請選擇屬於該 API 來源的模型。")
        return cleaned_data


class AIProviderSettingForm(forms.ModelForm):
    model = forms.ChoiceField(
        label="預設 Model",
        choices=[],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = AIProviderSetting
        fields = ["name", "provider", "model", "base_url", "api_key", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "例如 OpenAI 官方"}),
            "provider": forms.TextInput(attrs={"class": "form-control", "placeholder": "OpenAI"}),
            "base_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "可留空"}),
            "api_key": forms.PasswordInput(render_value=True, attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        runtime_model_choices = kwargs.pop("runtime_model_choices", None)
        super().__init__(*args, **kwargs)
        choices = [("", "請先儲存並載入 Model")]
        if self.instance and self.instance.pk:
            loaded_models = self.instance.models.filter(is_active=True).order_by("model_id")
            choices = [("", "不指定預設模型")]
            choices.extend((model.model_id, model.model_id) for model in loaded_models)
            if self.instance.model and self.instance.model not in [value for value, _ in choices]:
                choices.append((self.instance.model, f"{self.instance.model}（未在目前模型清單）"))
        elif runtime_model_choices:
            choices = [("", "不指定預設模型")]
            choices.extend((model_id, model_id) for model_id in runtime_model_choices)
        self.fields["model"].choices = choices


class ReferenceSourceForm(forms.ModelForm):
    class Meta:
        model = ReferenceSource
        fields = ["title", "url", "citation_note", "accessed_on"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "citation_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "accessed_on": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class ReferenceFileForm(forms.ModelForm):
    class Meta:
        model = ReferenceFile
        fields = ["source", "title", "file"]
        widgets = {
            "source": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.FileInput(attrs={"class": "form-control"}),
        }
