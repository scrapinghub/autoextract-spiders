import hashlib
import logging

from scrapy import signals
from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.exceptions import IgnoreRequest, DropItem
from scrapy.utils.request import request_fingerprint

from .util import load_sources, is_valid_url, is_blacklisted_url
from .util import utc_iso_date, maybe_is_article, maybe_is_product

DEFAULT_THRESHOLD = .1

SUPPORTED_TYPES = ('article', 'product')


class AutoExtractRequest(Request):

    def __init__(self, url, **kwargs):
        meta = kwargs.pop('meta', None) or {}
        meta.update(  # disable crawlera for all AE requests
            dont_proxy=True,
            no_crawlera_session=True,
        )
        page_type = kwargs.pop('page_type', None)
        feed_url = kwargs.pop('feed_url', None)
        if feed_url:
            meta['feed_url'] = feed_url
        source_url = kwargs.pop('source_url', None)
        if source_url:
            meta['source_url'] = source_url
        without_autoextract = kwargs.pop('without_autoextract', None)

        super().__init__(url, meta=meta, **kwargs)
        if without_autoextract is not True:
            self.meta['autoextract'] = {'enabled': True}
            if page_type:
                self.meta['autoextract']['pageType'] = page_type

        # Request fingerprint for Frontera requests
        if meta.get('cf_store') and 'source_url' in meta:
            fp = request_fingerprint(self).encode()
            meta['frontier_fingerprint'] = hashlib.sha1(fp).hexdigest()

    def __str__(self):
        return f'<AutoExtract {self.url}>'

    __repr__ = __str__


class AutoExtractSpider(Spider):
    """
    Simple AutoExtract spider that sends all URLs directly to AutoExtract API.

    Required params:
    * page-type: the kind of document to be extracted;
        current available options are "product"` and `"article"
    * url: one item URL
    * items: a local file, or a URL with a list of item URLs
    * articles: a file, or URL with a list of item URLs, just like the "items",
        but also defines the page-type as "article"
    * products: a file, or URL with a list of item URLs, just like the "items",
        but also defines the page-type as "product"

    Example:
    > -a page-type=article -a items=item-urls.jl
    Or:
    > -a articles="http://gist.github.com/whatever/items-list.json"
    """
    # name = 'base'
    threshold = DEFAULT_THRESHOLD

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # Less noise from the Depth Spider Middleware
        logging.getLogger('scrapy.spidermiddlewares.depth').setLevel(logging.INFO)
        spider = super().from_crawler(crawler, *args, **kwargs)

        # Default page-type for all requests
        if spider.get_arg('page-type', ''):
            spider.page_type = spider.get_arg('page-type')
        # Minimum probability threshold (Float in range [0.0 to 1.0])
        spider.threshold = float(spider.threshold)

        crawler.signals.connect(spider.open_spider, signals.spider_opened)
        return spider

    def open_spider(self):
        """
        Check possible config errors after the Spider is open.
        """
        if self.page_type and self.page_type not in SUPPORTED_TYPES:
            raise ValueError('Invalid page type "{}"'.format(self.page_type))
        if self.threshold < 0 or self.threshold > 1:
            raise ValueError('Threshold must be in range [0.0 to 1.0]')
        return self

    def get_arg(self, key: str, default=None):
        """
        Helper function to normalize getting args with - and _ characters.
        """
        spider_vars = vars(self)
        spider_vars.update({k.replace('-', '_'): v for k, v in spider_vars.items()})
        key = key.replace('-', '_')
        return spider_vars.get(key, default)

    def start_requests(self):
        """
        The main Spider function.
        """
        # Just a quick item URL and exit. Used for testing.
        one_url = getattr(self, 'url', '')
        if one_url:
            self.logger.info('Using one item URL: %s', one_url)
            autoextract_req = self.make_extract_request(one_url, check_page_type=False)
            if autoextract_req:
                yield autoextract_req
            return

        yield from self._process_item_list()

    def _process_item_list(self) -> str:
        """
        Process exact item URLs (can be JSON, JL, TXT, or CSV with 1 column)
        Because the list is expected to be large, the input must be file, or URL.
        The links from the list will be sent directly to AutoExtract, without processing.
        """
        articles_src = getattr(self, 'articles', '')
        products_src = getattr(self, 'products', '')
        if articles_src and len(articles_src) > 3:
            items = articles_src
            self.page_type = 'article'
        elif products_src and len(products_src) > 3:
            items = products_src
            self.page_type = 'product'
        else:
            items = getattr(self, 'items', '')

        if items and len(items) > 3:
            self.logger.info('Using item list: %s', items)
            try:
                links = load_sources(items)
            except Exception as err:
                self.logger.warning('Invalid sources file: %s %s', items, err)
            for link in links:
                autoextract_req = self.make_extract_request(link, check_page_type=False)
                if autoextract_req:
                    yield autoextract_req

    def make_extract_request(self, url, meta=None, check_page_type=True):
        """
        Create a AutoExtract Request with all the meta and info.
        The blacklisted domains will be dropped.
        The URLs that are unlikely to be content pages are dropped by default.
        """
        if not is_valid_url(url):
            self.logger.warning('Cannot make AutoExtract request, invalid URL: %s', url)
            return
        if is_blacklisted_url(url):
            self.crawler.stats.inc_value('error/blacklisted_url')
            return
        meta = meta or {}
        meta['cf_store'] = True
        req = AutoExtractRequest(url,
                                 meta=meta,
                                 page_type=self.page_type,
                                 callback=self.parse_item,
                                 errback=self.errback_item,
                                 dont_filter=True)

        if check_page_type and self.page_type == 'article':
            if maybe_is_article(url):
                return req
            self.logger.debug('Dropping URL: %s because is not an article', url)
            self.crawler.stats.inc_value('error/probably_not_article')
            return

        elif check_page_type and self.page_type == 'product':
            if maybe_is_product(url):
                return req
            self.logger.debug('Dropping URL: %s because is not a product', url)
            self.crawler.stats.inc_value('error/probably_not_product')
            return

        return req

    def parse_item(self, response):
        """
        Return the AutoExtract item containing the full HTML page + enriched data.
        """
        if not response.meta.get('autoextract'):
            self.crawler.stats.inc_value('error/empty')
            return

        autoextract = response.meta['autoextract']
        # Try all supported page types
        for page_type in SUPPORTED_TYPES:
            item = autoextract.get(page_type, {})
            if not item:
                continue
            if self.threshold > 0 and item.get('probability', 0) < self.threshold:
                self.logger.debug('Dropping %s URL: %s, low probability=%f', page_type,
                                  response.url, item['probability'])
                self.crawler.stats.inc_value('error/probability')
                continue
            # Remove empty values from the item to enable ScrapyCloud stats
            item = {k: v for k, v in item.items() if v}
            # Add source URL
            if response.meta.get('source_url'):
                item['source_url'] = response.meta['source_url']
            # Add current timestamp
            item['scraped_at'] = utc_iso_date()
            yield item

    def errback_item(self, failure):
        if failure.check(IgnoreRequest, DropItem):
            return
        request = getattr(failure, 'request', None)
        if request:
            self.logger.warning('Item %s failed: %s', request.body, failure)
            self.crawler.stats.inc_value('error/failed_item')
