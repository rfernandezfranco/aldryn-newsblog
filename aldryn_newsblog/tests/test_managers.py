# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from aldryn_newsblog.models import Article

from . import NewsBlogTestCase


class TestManagers(NewsBlogTestCase):

    def test_published_articles_filtering(self):
        for i in range(5):
            self.create_article()
        unpublised_article = Article.objects.first()
        unpublised_article.is_published = False
        unpublised_article.save()
        self.assertEqual(Article.objects.published().count(), 4)
        self.assertNotIn(unpublised_article, Article.objects.published())

    # TODO: Should also test for publishing_date
    def test_view_article_not_published(self):
        article = self.create_article(is_published=False)
        article_url = article.get_absolute_url()
        response = self.client.get(article_url)
        self.assertEqual(response.status_code, 404)

    def test_get_tags_returns_ordered_counts(self):
        tag_names = ("tag foo", "tag bar", "tag buzz")

        # create unpublished article to ensure it is ignored
        self.create_tagged_articles(1, tags=(tag_names[0],), is_published=False)

        tag_slug2 = list(
            self.create_tagged_articles(3, tags=(tag_names[1],)).keys()
        )[0]
        tag_slug3 = list(
            self.create_tagged_articles(5, tags=(tag_names[2],)).keys()
        )[0]

        tags = Article.objects.get_tags(
            request=None, namespace=self.app_config.namespace
        )
        tags = [(tag.slug, tag.num_articles) for tag in tags]
        self.assertEqual(tags, [(tag_slug3, 5), (tag_slug2, 3)])
