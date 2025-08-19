# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError

from aldryn_newsblog.models import Article

class Command(BaseCommand):
    help = "Pregenerates thumbnails for all articles."

    def handle(self, *args, **options):
        self.stdout.write("Starting to pregenerate thumbnails for articles...")

        try:
            from easy_thumbnails.files import get_thumbnailer
        except ImportError:
            raise CommandError(
                "easy-thumbnails is not installed. Please install it with "
                "'pip install easy-thumbnails'")

        articles = Article.objects.published().exclude(featured_image__isnull=True)
        total_articles = articles.count()
        self.stdout.write("{0} articles with featured images to process.".format(
            total_articles))

        processed_count = 0
        for article in articles:
            try:
                thumbnailer = get_thumbnailer(article.featured_image)
                options = {
                    'size': (800, 450),
                    'crop': True,
                    'subject_location': article.featured_image.subject_location
                }
                thumbnailer.get_thumbnail(options)
                processed_count += 1
                self.stdout.write(
                    "({0}/{1}) Generated thumbnail for article '{2}'".format(
                        processed_count, total_articles, article.title))
            except Exception as e:
                self.stderr.write(
                    "Could not generate thumbnail for article '{0}': {1}".format(
                        article.title, e))

        self.stdout.write(self.style.SUCCESS(
            "Finished pregenerating thumbnails. "
            "{0} thumbnails processed.".format(processed_count)
        ))
