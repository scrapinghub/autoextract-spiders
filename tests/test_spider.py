import os
import sys
# import pytest
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

sys.path.insert(1, os.getcwd())
from autoextract_spiders.spiders import CrawlerSpider  # noqa: E402
from autoextract_spiders.spiders import ArticleAutoExtract, ProductAutoExtract  # noqa: E402

CrawlerSpider.name = 'crawler'


def test_simple_params():
    t = 0.33
    p = 'article'
    e = {'allow': 'example.com'}
    c = {'item_count': 9}
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(CrawlerSpider, threshold=t, page_type=p, extract_rules=str(e), count_limits=str(c))
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.threshold == t
    assert crawler.spider.page_type == p
    assert crawler.spider.extract_rules == e
    assert crawler.spider.count_limits == c


def test_more_params():
    p = 'product'
    mi = 19
    mp = 99
    al = "example.com"
    il = "'fb.com'"
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(CrawlerSpider, page_type=p, max_pages=mp, max_items=mi, allow_links=al, ignore_links=il)
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.page_type == p
    assert crawler.spider.count_limits['item_host_count'] == mi
    assert crawler.spider.count_limits['page_host_count'] == mp
    assert crawler.spider.extract_rules['allow'] == al
    assert crawler.spider.extract_rules['deny'] == il.strip("'")


def test_max_items_max_pages():
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(CrawlerSpider, page_type='article', max_items='3', max_pages='9', same_domain='no')
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.same_origin is False
    assert crawler.spider.only_discovery is False
    assert crawler.spider.page_type == 'article'
    assert crawler.spider.count_limits == {
        'item_host_count': 3,
        'page_host_count': 9,
        'item_count': 6,
        'page_count': 18,
    }


def test_allow_ignore_links():
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(CrawlerSpider, page_type='product', allow_links='/stuff', ignore_links='/whatever')
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.page_type == 'product'
    assert crawler.spider.extract_rules == {
        'allow': '/stuff',
        'deny': '/whatever',
    }


def test_simple_article():
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(ArticleAutoExtract)
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.name == 'articles'
    assert crawler.spider.page_type == 'article'
    assert crawler.spider.same_origin is True
    assert isinstance(crawler.spider.threshold, float)
    assert isinstance(crawler.spider.only_discovery, bool)


def test_simple_product():
    proc = CrawlerProcess(get_project_settings())
    proc.crawl(ProductAutoExtract)
    crawler = proc._crawlers.pop()
    proc.stop()

    assert crawler.spider.name == 'products'
    assert crawler.spider.page_type == 'product'
    assert crawler.spider.same_origin is True
    assert isinstance(crawler.spider.threshold, float)
    assert isinstance(crawler.spider.only_discovery, bool)
