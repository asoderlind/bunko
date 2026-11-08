"""Seed the provider profile from env on first migrate."""

import logging

from django.conf import settings
from django.db import migrations

log = logging.getLogger(__name__)


def seed_provider(apps, schema_editor):
    ProviderProfile = apps.get_model("notes", "ProviderProfile")
    if not settings.OLLAMA_BASE_URL:
        log.info("OLLAMA_BASE_URL not set; no provider profile seeded")
        return
    if ProviderProfile.objects.exists():
        return
    ProviderProfile.objects.create(
        label="Ollama (tailnet MacBook)",
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        api_key_env="OLLAMA_API_KEY",
        is_default=True,
        is_local=True,
        enabled=True,
    )
    log.info("seeded default provider profile at %s", settings.OLLAMA_BASE_URL)


def unseed_provider(apps, schema_editor):
    ProviderProfile = apps.get_model("notes", "ProviderProfile")
    ProviderProfile.objects.filter(label="Ollama (tailnet MacBook)").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_provider, unseed_provider),
    ]
