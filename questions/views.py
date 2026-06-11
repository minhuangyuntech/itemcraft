from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AICommandForm,
    AIProviderSettingForm,
    ImportUploadForm,
    OptionItemForm,
    QuestionForm,
    ReferenceFileForm,
    ReferenceSourceForm,
)
from .ai_client import AICommandError, fetch_available_model_ids, load_available_models, run_ai_command, test_ai_setting
from .ai_db_actions import apply_ai_database_actions, extract_json_actions
from .backup import create_database_backup, restore_database_backup
from .importer import import_questions
from .models import AIProviderSetting, DatabaseBackup, ImportJob, OptionGroup, OptionItem, Question, ReferenceFile, ReferenceSource
from .question_context import build_item_writing_reference_context, build_question_table_context


def ensure_default_options():
    defaults = {
        "type": ("類型", ["既有基礎", "既有進階", "公務基礎", "公務進階"]),
        "status": ("狀態", ["調整", "新命"]),
    }
    for key, (name, items) in defaults.items():
        group, _ = OptionGroup.objects.get_or_create(key=key, defaults={"name": name})
        if group.name != name:
            group.name = name
            group.save(update_fields=["name"])
        group.items.exclude(name__in=items).update(is_active=False)
        for index, item_name in enumerate(items, start=1):
            option, _ = OptionItem.objects.get_or_create(
                group=group,
                name=item_name,
                defaults={"sort_order": index * 10, "is_active": True},
            )
            updates = []
            if option.sort_order != index * 10:
                option.sort_order = index * 10
                updates.append("sort_order")
            if not option.is_active:
                option.is_active = True
                updates.append("is_active")
            if updates:
                option.save(update_fields=updates)


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("questions:dashboard")
    return render(request, "questions/home.html")


@staff_member_required(login_url="questions:login")
def dashboard(request):
    ensure_default_options()
    ai_form = AICommandForm(request.POST or None)
    ai_response = ""
    if request.method == "POST" and "run_ai" in request.POST:
        if ai_form.is_valid():
            try:
                question_context = ""
                if ai_form.cleaned_data["include_question_table"]:
                    question_context, question_context_count = build_question_table_context(ai_form.cleaned_data["question_limit"])
                    reference_context, reference_count = build_item_writing_reference_context()
                    question_context = f"{question_context}\n\n{reference_context}"
                    messages.info(request, f"已提供 {question_context_count} 筆題庫資料與 {reference_count} 筆命題參考給 AI 讀取。")
                ai_response = run_ai_command(
                    prompt=ai_form.cleaned_data["prompt"],
                    api_setting=ai_form.cleaned_data["api_setting"],
                    model=ai_form.cleaned_data["model"],
                    sources=ai_form.cleaned_data["reference_sources"],
                    files=ai_form.cleaned_data["reference_files"],
                    allow_database_changes=ai_form.cleaned_data["allow_database_changes"],
                    question_context=question_context,
                )
                if ai_form.cleaned_data["allow_database_changes"]:
                    actions = extract_json_actions(ai_response)
                    if actions:
                        backup = create_database_backup("AI 修改題庫前自動備份", request.user)
                        summary = apply_ai_database_actions(
                            actions,
                            backup=backup,
                            prompt=ai_form.cleaned_data["prompt"],
                            response=ai_response,
                            user=request.user,
                        )
                        messages.success(request, f"AI 已修改題庫，並已建立備份 #{backup.id}。")
                        ai_response = f"{ai_response}\n\n---\n執行摘要：\n{summary}"
                    else:
                        messages.warning(request, "已勾選允許修改題庫，但 AI 回覆中沒有可執行的 JSON actions，因此未修改資料庫。")
                else:
                    messages.success(request, "AI 已完成回覆。")
            except AICommandError as exc:
                messages.warning(request, str(exc))
    return render(
        request,
        "questions/dashboard.html",
        {
            "ai_form": ai_form,
            "ai_response": ai_response,
            "ai_model_api_map": {
                str(model.id): str(model.api_setting_id)
                for model in ai_form.fields["model"].queryset
            },
            "question_count": Question.objects.count(),
            "reference_count": ReferenceSource.objects.count() + ReferenceFile.objects.count(),
            "latest_questions": Question.objects.select_related("type_option", "status_option")[:5],
            "latest_imports": ImportJob.objects.all()[:5],
        },
    )


@staff_member_required(login_url="questions:login")
def question_list(request):
    ensure_default_options()
    query = request.GET.get("q", "").strip()
    type_id = request.GET.get("type", "")
    status_id = request.GET.get("status", "")
    questions = Question.objects.select_related("type_option", "status_option")
    if query:
        questions = questions.filter(
            Q(stem__icontains=query)
            | Q(revised_stem__icontains=query)
            | Q(revised_explanation__icontains=query)
            | Q(classification_basis__icontains=query)
        )
    if type_id:
        questions = questions.filter(type_option_id=type_id)
    if status_id:
        questions = questions.filter(status_option_id=status_id)
    return render(
        request,
        "questions/question_list.html",
        {
            "questions": questions,
            "query": query,
            "type_options": OptionItem.objects.filter(group__key="type", is_active=True),
            "status_options": OptionItem.objects.filter(group__key="status", is_active=True),
            "selected_type": type_id,
            "selected_status": status_id,
        },
    )


@staff_member_required(login_url="questions:login")
def question_create(request):
    ensure_default_options()
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        if question.is_completed and not question.completed_at:
            question.completed_at = timezone.now()
        question.save()
        messages.success(request, "題目已建立。")
        return redirect("questions:question_update", pk=question.pk)
    return render(request, "questions/question_form.html", {"form": form, "title": "新增題目"})


@staff_member_required(login_url="questions:login")
def question_update(request, pk):
    ensure_default_options()
    question = get_object_or_404(Question, pk=pk)
    if question.is_completed and request.method == "POST":
        messages.warning(request, "此題目已標記完成，不能再修改。")
        return redirect("questions:question_update", pk=question.pk)
    form = QuestionForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        if question.is_completed and not question.completed_at:
            question.completed_at = timezone.now()
        question.save()
        messages.success(request, "題目已更新。")
        return redirect("questions:question_update", pk=question.pk)
    return render(request, "questions/question_form.html", {"form": form, "title": "編輯題目", "question": question})


@staff_member_required(login_url="questions:login")
def import_questions_view(request):
    form = ImportUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        job, mapping = import_questions(form.cleaned_data["file"])
        messages.success(request, f"匯入完成：新增 {job.imported_rows} 筆，錯誤 {job.error_rows} 筆。")
        return render(request, "questions/import.html", {"form": ImportUploadForm(), "job": job, "mapping": mapping})
    return render(request, "questions/import.html", {"form": form, "jobs": ImportJob.objects.all()[:10]})


@staff_member_required(login_url="questions:login")
def references(request):
    source_form = ReferenceSourceForm(prefix="source")
    file_form = ReferenceFileForm(prefix="file")
    if request.method == "POST":
        if "save_source" in request.POST:
            source_form = ReferenceSourceForm(request.POST, prefix="source")
            if source_form.is_valid():
                source_form.save()
                messages.success(request, "來源網址已新增。")
                return redirect("questions:references")
        if "save_file" in request.POST:
            file_form = ReferenceFileForm(request.POST, request.FILES, prefix="file")
            if file_form.is_valid():
                file_form.save()
                messages.success(request, "參考檔案已上傳。")
                return redirect("questions:references")
    return render(
        request,
        "questions/references.html",
        {
            "source_form": source_form,
            "file_form": file_form,
            "sources": ReferenceSource.objects.prefetch_related("files"),
            "files": ReferenceFile.objects.select_related("source")[:20],
        },
    )


@staff_member_required(login_url="questions:login")
def settings_view(request):
    ensure_default_options()
    edit_ai_id = request.GET.get("edit_ai")
    ai_setting = None
    preview_model_ids = []
    if edit_ai_id:
        ai_setting = get_object_or_404(AIProviderSetting, pk=edit_ai_id)
    ai_form = AIProviderSettingForm(instance=ai_setting, prefix="ai")
    option_form = OptionItemForm(prefix="option")
    if request.method == "POST":
        if "save_ai" in request.POST:
            ai_id = request.POST.get("ai_id")
            instance = get_object_or_404(AIProviderSetting, pk=ai_id) if ai_id else None
            if instance and not request.POST.get("ai-api_key"):
                mutable_post = request.POST.copy()
                mutable_post["ai-api_key"] = instance.api_key
            else:
                mutable_post = request.POST
            ai_form = AIProviderSettingForm(mutable_post, instance=instance, prefix="ai")
            if ai_form.is_valid():
                saved_setting = ai_form.save()
                runtime_model_ids = request.POST.getlist("runtime_model_ids")
                for model_id in runtime_model_ids:
                    saved_setting.models.update_or_create(
                        model_id=model_id,
                        defaults={"display_name": model_id, "is_active": True},
                    )
                messages.success(request, "AI API 設定已儲存。")
                return redirect("questions:settings")
        if "preview_models" in request.POST:
            ai_id = request.POST.get("ai_id")
            instance = get_object_or_404(AIProviderSetting, pk=ai_id) if ai_id else None
            api_key = request.POST.get("ai-api_key") or (instance.api_key if instance else "")
            try:
                preview_model_ids = fetch_available_model_ids(
                    request.POST.get("ai-base_url"),
                    api_key,
                )
                mutable_post = request.POST.copy()
                if instance and not mutable_post.get("ai-api_key"):
                    mutable_post["ai-api_key"] = instance.api_key
                ai_form = AIProviderSettingForm(
                    mutable_post,
                    instance=instance,
                    prefix="ai",
                    runtime_model_choices=preview_model_ids,
                )
                messages.success(request, f"已載入 {len(preview_model_ids)} 個模型，請選擇預設模型後儲存。")
            except AICommandError as exc:
                ai_form = AIProviderSettingForm(request.POST, instance=instance, prefix="ai")
                messages.warning(request, f"載入模型失敗：{exc}")
        if "test_ai" in request.POST:
            setting = get_object_or_404(AIProviderSetting, pk=request.POST.get("ai_id"))
            try:
                response_text = test_ai_setting(setting)
                messages.success(request, f"{setting.name} 測試成功：{response_text}")
            except AICommandError as exc:
                messages.warning(request, f"{setting.name} 測試失敗：{exc}")
            return redirect("questions:settings")
        if "load_models" in request.POST:
            setting = get_object_or_404(AIProviderSetting, pk=request.POST.get("ai_id"))
            try:
                loaded = load_available_models(setting)
                messages.success(request, f"{setting.name} 已載入 {loaded} 個模型。")
            except AICommandError as exc:
                messages.warning(request, f"{setting.name} 載入模型失敗：{exc}")
            return redirect("questions:settings")
        if "delete_ai" in request.POST:
            setting = get_object_or_404(AIProviderSetting, pk=request.POST.get("ai_id"))
            setting_name = setting.name
            setting.delete()
            messages.success(request, f"{setting_name} 已刪除。")
            return redirect("questions:settings")
        if "save_option" in request.POST:
            option_form = OptionItemForm(request.POST, prefix="option")
            if option_form.is_valid():
                option_form.save()
                messages.success(request, "下拉選單項目已新增。")
                return redirect("questions:settings")
    return render(
        request,
        "questions/settings.html",
        {
            "ai_form": ai_form,
            "editing_ai": ai_setting,
            "ai_settings": AIProviderSetting.objects.prefetch_related("models"),
            "preview_model_ids": preview_model_ids,
            "option_form": option_form,
            "option_groups": OptionGroup.objects.prefetch_related("items"),
            "backups": DatabaseBackup.objects.all()[:10],
        },
    )


@staff_member_required(login_url="questions:login")
def create_backup_view(request):
    if request.method == "POST":
        backup = create_database_backup("使用者手動備份", request.user)
        messages.success(request, f"已建立備份 #{backup.id}。")
    return redirect("questions:settings")


@staff_member_required(login_url="questions:login")
def restore_backup_view(request, pk):
    if request.method == "POST":
        from .models import DatabaseBackup

        backup = get_object_or_404(DatabaseBackup, pk=pk)
        restore_database_backup(backup)
        messages.success(request, f"已還原備份 #{backup.id}。")
    return redirect("questions:settings")
