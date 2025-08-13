# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
from operator import attrgetter

from django.core.cache import cache
from django.db import models
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from django.utils.translation import get_language

from aldryn_apphooks_config.managers.base import ManagerMixin, QuerySetMixin
from aldryn_people.models import Person
from parler.managers import TranslatableManager, TranslatableQuerySet
from taggit.models import Tag, TaggedItem

from aldryn_newsblog.compat import toolbar_edit_mode_active


class ArticleQuerySet(QuerySetMixin, TranslatableQuerySet):
    def published(self):
        """
        Returns articles that are published AND have a publishing_date that
        has actually passed.
        """
        return self.filter(is_published=True, publishing_date__lte=now())


class RelatedManager(ManagerMixin, TranslatableManager):
    def get_queryset(self):
        qs = ArticleQuerySet(self.model, using=self.db)
        return qs.select_related(
            'app_config',
            'author',
            'author__user',
            'owner',
            'featured_image',
        ).prefetch_related('categories', 'tags')

    def published(self):
        return self.get_queryset().published()


    def get_months(self, request, namespace):
        """
        Get months and years with articles count for given request and namespace
        string. This means how many articles there are in each month.

        The request is required, because logged-in content managers may get
        different counts.

        Return list of dictionaries ordered by article publishing date of the
        following format:
        [
            {
                'date': date(YEAR, MONTH, ARBITRARY_DAY),
                'num_articles': NUM_ARTICLES
            },
            ...
        ]
        """
        edit_mode = (
            request and hasattr(request, 'toolbar') and request.toolbar and
            toolbar_edit_mode_active(request)
        )
        language = getattr(request, 'LANGUAGE_CODE', None) or get_language()
        cache_key = 'nb_months_%s_%s_%s' % (namespace, language, int(edit_mode))
        months = cache.get(cache_key)
        if months is not None:
            return months

        if edit_mode:
            articles = self.namespace(namespace)
        else:
            articles = self.published().namespace(namespace)

        months_qs = (
            articles.annotate(month=TruncMonth('publishing_date'))
            .values('month')
            .annotate(num_articles=Count('pk'))
            .order_by('-month')
        )
        months = [
            {'date': entry['month'].date(), 'num_articles': entry['num_articles']}
            for entry in months_qs
        ]
        cache.set(cache_key, months)
        return months
    def get_authors(self, namespace):
        """
        Get authors with articles count for given namespace string.

        Return Person queryset annotated with and ordered by 'num_articles'.
        """

        # This methods relies on the fact that Article.app_config.namespace
        # is effectively unique for Article models
        return Person.objects.filter(
            article__app_config__namespace=namespace,
            article__is_published=True).annotate(
                num_articles=models.Count('article')).order_by('-num_articles')

    def get_tags(self, request, namespace):
        """
        Get tags with articles count for given namespace string.

        Return list of Tag objects ordered by custom 'num_articles' attribute.
        """
        if (request and hasattr(request, 'toolbar') and  # noqa: #W504
                request.toolbar and toolbar_edit_mode_active(request)):
            articles = self.namespace(namespace)
        else:
            articles = self.published().namespace(namespace)
        if not articles.exists():
            # return empty iterable early not to perform useless requests
            return []
        kwargs = TaggedItem.bulk_lookup_kwargs(articles)

        # aggregate and sort
        counted_tags = dict(TaggedItem.objects
                            .filter(**kwargs)
                            .values('tag')
                            .annotate(tag_count=models.Count('tag'))
                            .values_list('tag', 'tag_count'))

        # and finally get the results
        tags = Tag.objects.filter(pk__in=counted_tags.keys())
        for tag in tags:
            tag.num_articles = counted_tags[tag.pk]
        return sorted(tags, key=attrgetter('num_articles'), reverse=True)
