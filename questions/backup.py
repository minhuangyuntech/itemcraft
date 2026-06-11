import shutil
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone

from .models import DatabaseBackup


def create_database_backup(reason, user=None):
    db_path = Path(settings.DATABASES["default"]["NAME"])
    backup_dir = Path(settings.BASE_DIR) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"db-{timestamp}.sqlite3"
    shutil.copy2(db_path, backup_path)
    return DatabaseBackup.objects.create(
        reason=reason,
        file_path=str(backup_path),
        created_by=getattr(user, "username", "") if user else "",
    )


def restore_database_backup(backup):
    source_path = Path(backup.file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"找不到備份檔案：{source_path}")
    target_path = Path(settings.DATABASES["default"]["NAME"])
    connections.close_all()
    shutil.copy2(source_path, target_path)

