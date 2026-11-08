from django.db import migrations

PALETTE = [
    "blue",
    "green",
    "amber",
    "red",
    "purple",
    "pink",
    "teal",
    "orange",
    "slate",
    "lime",
]


def backfill_colors(apps, schema_editor):
    """Give existing tags a colour, spreading them across the palette.

    New tags are coloured in Tag.save(); rows that predate the field (or that
    were created before that hook existed) need this.
    """
    Tag = apps.get_model("notes", "Tag")
    for i, tag in enumerate(Tag.objects.order_by("created_at", "slug")):
        tag.color = PALETTE[i % len(PALETTE)]
        tag.save(update_fields=["color"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0003_tag_color_and_title_source"),
    ]

    operations = [
        migrations.RunPython(backfill_colors, noop),
    ]
