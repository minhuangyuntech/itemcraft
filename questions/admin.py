from django.contrib import admin

from .models import (
    AIDatabaseOperation,
    AIModel,
    AIProviderSetting,
    DatabaseBackup,
    ImportJob,
    ItemWritingReference,
    OptionGroup,
    OptionItem,
    Question,
    ReferenceFile,
    ReferenceSource,
)


admin.site.register(AIDatabaseOperation)
admin.site.register(AIModel)
admin.site.register(AIProviderSetting)
admin.site.register(DatabaseBackup)
admin.site.register(ImportJob)
admin.site.register(ItemWritingReference)
admin.site.register(OptionGroup)
admin.site.register(OptionItem)
admin.site.register(Question)
admin.site.register(ReferenceFile)
admin.site.register(ReferenceSource)

# Register your models here.
