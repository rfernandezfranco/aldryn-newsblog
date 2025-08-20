# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError

from aldryn_newsblog.models import Article


def _generate_thumbnail_for_article(article_pk):
    """
    A standalone function to be executed in a parallel process.
    It fetches a single article and generates its thumbnail.
    """
    try:
        from easy_thumbnails.files import get_thumbnailer
        article = Article.objects.get(pk=article_pk)
        if article.featured_image:
            thumbnailer = get_thumbnailer(article.featured_image)
            options = {
                'size': (800, 450),
                'crop': True,
                'subject_location': article.featured_image.subject_location
            }
            thumbnailer.get_thumbnail(options)
            return (True, "Generated thumbnail for article '{0}'".format(article.title))
        return (True, "Article '{0}' has no featured image, skipping.".format(article.title))
    except Exception as e:
        # Catch all exceptions to prevent a single failure from stopping the whole pool
        return (False, "Could not process article {0}: {1}".format(article_pk, e))


class Command(BaseCommand):
    help = "Pregenerates thumbnails for all articles."

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            help='Specifies the number of worker processes to use. '
                 'Defaults to the number of CPUs on the machine.',
            default=None,
        )

    def handle(self, *args, **options):
        from concurrent.futures import ProcessPoolExecutor, as_completed

        max_workers = options['workers']
        self.stdout.write(
            "Starting thumbnail generation with "
            f"{max_workers or 'default'} worker processes..."
        )

        article_pks = list(Article.objects.published().exclude(
            featured_image__isnull=True
        ).values_list('pk', flat=True))

        total_articles = len(article_pks)
        if total_articles == 0:
            self.stdout.write("No articles with featured images to process.")
            return

        self.stdout.write(f"{total_articles} articles to process.")

        success_count = 0
        error_count = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_pk = {
                executor.submit(_generate_thumbnail_for_article, pk): pk
                for pk in article_pks
            }

            for i, future in enumerate(as_completed(future_to_pk)):
                pk = future_to_pk[future]
                try:
                    success, message = future.result()
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        self.stderr.write(message)
                except Exception as exc:
                    error_count += 1
                    self.stderr.write(
                        f"Article {pk} generated an exception: {exc}")

                # Simple progress indicator
                self.stdout.write(
                    f"Progress: {i + 1}/{total_articles}", ending='\r'
                )
                self.stdout.flush()

        self.stdout.write("\n" + self.style.SUCCESS(
            "Finished pregenerating thumbnails. "
            f"Successful: {success_count}, Failed: {error_count}."
        ))
