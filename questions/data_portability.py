from io import StringIO

from django.core import serializers
from django.db import transaction

from .models import ItemWritingReference, OptionGroup, OptionItem, Question, ReferenceFile, ReferenceSource


EXPORT_MODELS = [
    OptionGroup,
    OptionItem,
    ReferenceSource,
    ReferenceFile,
    ItemWritingReference,
    Question,
]


def export_content_bundle():
    objects = []
    for model in EXPORT_MODELS:
        objects.extend(model.objects.all().order_by("pk"))
    return serializers.serialize("json", objects, indent=2)


def import_content_bundle(uploaded_file):
    text = uploaded_file.read().decode("utf-8-sig")
    stream = StringIO(text)
    imported = 0
    with transaction.atomic():
        for deserialized in serializers.deserialize("json", stream):
            deserialized.save()
            imported += 1
    return imported
