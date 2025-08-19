from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aldryn_newsblog', '0016_auto_20180329_1417'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['is_published', '-publishing_date', 'app_config'], name='newsblog_article_listing_idx'),
        ),
    ]
