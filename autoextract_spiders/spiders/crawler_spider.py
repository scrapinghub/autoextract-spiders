import yaml
from urllib.parse import urlsplit

from scrapy import signals
from scrapy.http import Request, TextResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.exceptions import IgnoreRequest, DropItem
from scrapy.utils.misc import arg_to_iter

from ..middlewares import reset_scheduler_on_disabled_frontera
from ..sessions import crawlera_session, update_redirect_middleware
from .rule import Rule
from .autoextract_spider import AutoExtractSpider
from .util import is_valid_url, utc_iso_date, is_autoextract_request, \
    FingerprintPrefix

META_TO_KEEP = ('source_url',)

DEFAULT_ALLOWED_DOMAINS = ['xod.scrapinghub.com', 'autoextract.scrapinghub.com']

DEFAULT_COUNT_LIMITS = {'page_count': 1000, 'item_count': 100}


class CrawlerSpider(AutoExtractSpider):
    """
    Crawler Spider discovers links and returns AutoExtract items too.

    Required params:
    * seeds: one, or more seed URLs (as YAML list)
    Example:
    > -a seeds=http://example.com/
    Or:
    > -a seeds='[http://blog.example.com/, http://shop.example.com/]'

    The mandatory "page-type" param from the parent AutoExtract Spider is also required.

    Optional params:
    * seeds-file-url: an optional URL to a plain text file with a list of seed URLs;
    * max-items: how many items (articles, or products) should the spider extract, per host;
        When the items are extracted, the spider stops. default: 100;
    * max-pages: how many pages should the spider follow per host, when discovering links;
        default: 1000;
    * count-limits: a YAML dict with page or item max count;
        example: {page_count: 90, item_count: 10}
    * extract-rules: a YAML dict with allowed and denied hosts and patterns;
        They will be used to initialize a scrapy.linkextractors.LinkExtractor;
        example: {allow: "/en/items/", deny: ["/privacy-?policy/?$", "/about-?(us)?$"]}
    * same-domain: limit the discovery of links to the same domains as the seeds;
        default: True
    * discovery-only: discover the links and return them, without AutoExtract items;
        default: False

    Extra options:
    * DEPTH_LIMIT: maximum depth that will be allowed to crawl; default: 1.
    * CLOSESPIDER_TIMEOUT: if the spider is running for more than that number of seconds,
        it will be automatically closed. default: 21600 seconds.
    """
    # name = 'crawler'
    only_discovery = False
    same_origin = True
    seed_urls = None
    seeds_file_url = None
    count_limits = DEFAULT_COUNT_LIMITS
    rules = [
        Rule(LinkExtractor(),
             process_links='_rule_process_links',
             process_req_resp='_rule_process_req_resp',
             follow=True),
    ]

    frontera_settings = {
        'HCF_PRODUCER_FRONTIER': 'autoextract',
        'HCF_PRODUCER_SLOT_PREFIX': 'queue',
        'HCF_PRODUCER_NUMBER_OF_SLOTS': 1,
        'HCF_PRODUCER_BATCH_SIZE': 100,

        'HCF_CONSUMER_FRONTIER': 'autoextract',
        'HCF_CONSUMER_SLOT': 'queue0',
        'HCF_CONSUMER_MAX_REQUESTS': 100,
    }

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        reset_scheduler_on_disabled_frontera(settings)
        update_redirect_middleware(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.main_callback = spider.parse_page
        spider.main_errback = spider.errback_page

        for rule in spider.rules:
            rule._compile(spider)

        # Discovery only for seeds, without items
        if spider.get_arg('discovery-only'):
            spider.only_discovery = yaml.load(spider.get_arg('discovery-only'))
        # Limit requests to the same domain
        if spider.get_arg('same-domain'):
            spider.same_origin = yaml.load(spider.get_arg('same-domain'))

        # Seed URLs
        if getattr(spider, 'seeds', None):
            seeds = spider.seeds
            if isinstance(seeds, str):
                try:
                    spider.seed_urls = yaml.load(seeds)
                except Exception as err:
                    raise ValueError('Invalid seed URLs: %s %s', seeds, err)
            elif isinstance(seeds, (list, tuple)):
                spider.seed_urls = seeds
            del spider.seeds
        if spider.seed_urls:
            spider.seed_urls = arg_to_iter(spider.seed_urls)
        # Seeds file URL
        if spider.get_arg('seeds-file-url'):
            spider.seeds_file_url = spider.get_arg('seeds-file-url')

        # Domains allowed to be crawled, for OffsiteMiddleware and others
        if spider.same_origin and spider.seed_urls:
            if not hasattr(spider, 'allowed_domains'):
                spider.allowed_domains = DEFAULT_ALLOWED_DOMAINS
            spider.allowed_domains.extend(urlsplit(u).netloc.lower() for u in spider.seed_urls)

        crawler.signals.connect(spider.open_spider, signals.spider_opened)
        return spider

    def open_spider(self):  # noqa: C901
        """
        Parse command line args.
        """
        super().open_spider()

        # JSON count limits for pages or items
        if self.get_arg('count-limits'):
            limits = self.get_arg('count-limits')
            try:
                self.count_limits = yaml.load(limits) if not isinstance(limits, dict) else limits
            except Exception as err:
                raise ValueError('Invalid count limits: %s %s', limits, err)
        # JSON link extraction rules
        if self.get_arg('extract-rules'):
            rules = self.get_arg('extract-rules')
            try:
                self.extract_rules = yaml.load(rules) if not isinstance(rules, dict) else rules
            except Exception as err:
                raise ValueError('Invalid extraction rules: %s %s', rules, err)
        else:
            self.extract_rules = {}

        # Shortcut to limit global requests
        if self.get_arg('max-pages'):
            max_pages = int(self.get_arg('max-pages'))
            self.count_limits['page_host_count'] = max_pages
            if self.seed_urls:
                self.count_limits['page_count'] = max_pages * len(self.seed_urls) * 2
            else:
                self.count_limits['page_count'] = max_pages * 2
        if self.get_arg('max-items'):
            max_items = int(self.get_arg('max-items'))
            self.count_limits['item_host_count'] = max_items
            if self.seed_urls:
                self.count_limits['item_count'] = max_items * len(self.seed_urls) * 2
            else:
                self.count_limits['item_count'] = max_items * 2
        if self.count_limits:
            self.logger.debug('Using count limits: %s', self.count_limits)

        # Shortcut to allow and ignore links
        if self.get_arg('allow-links'):
            try:
                self.extract_rules['allow'] = yaml.load(self.get_arg('allow-links'))
            except Exception as err:
                raise ValueError('Invalid allow-links: %s', err)
        if self.get_arg('ignore-links'):
            try:
                self.extract_rules['deny'] = yaml.load(self.get_arg('ignore-links'))
            except Exception as err:
                raise ValueError('Invalid ignore-links: %s', err)
        if self.extract_rules:
            self.logger.debug('Using extract rules: %s', self.extract_rules)

        if self.only_discovery:
            self.logger.debug('Discovery ONLY mode enabled')

        return self

    @crawlera_session.init_start_requests
    def start_requests(self):
        """
        The main function.
        """
        # Process exact item URLs for Articles, or Products (if any)
        yield from super().start_requests()
        # Discover links and process the items
        yield from self._process_seeds()

    def _process_seeds(self) -> str:
        """
        Seeds are website URLs (can be JSON, JL, TXT, or CSV with 1 column)
        Because the list is expected to be small, the input can be one, or more URLs.
        Seed URLs will be crawled deeply, trying to find articles, or products.
        """
        if self.seeds_file_url:
            yield Request(self.seeds_file_url,
                          meta={'source_url': self.seeds_file_url},
                          callback=self.parse_seeds_file,
                          errback=self.main_errback,
                          dont_filter=True)

        if not self.seed_urls:
            return

        self.logger.info('Using seeds: %s', self.seed_urls)
        yield from self._schedule_seed_urls(self.seed_urls)

    def parse_seeds_file(self, response):
        """
        Process seeds file url response and schedule seed urls for processing.
        """
        if not isinstance(response, TextResponse):
            return
        seeds = response.text.split()
        yield from self._schedule_seed_urls(seeds)

    def _schedule_seed_urls(self, seed_urls):
        """
        A helper to process seed urls and yield appropriate requests.
        """
        for url in seed_urls:
            url = url.strip()
            if not is_valid_url(url):
                self.logger.warning('Ignoring invalid seed URL: %s', url)
                continue
            # Initial request to the seed URL
            self.crawler.stats.inc_value('x_request/seeds')
            request = Request(url,
                          meta={'source_url': url},
                          callback=self.main_callback,
                          errback=self.main_errback,
                          dont_filter=True)
            # Trick required to avoid some seeds to be never processed or too late.
            try:
                self.crawler.engine.crawl(request, self)
            except AssertionError:
                yield request


    def parse_page(self, response):
        """
        Parse the spider response.
        """
        if not isinstance(response, TextResponse):
            return

        # Try to parse the AutoExtract response (if available) and return the correct Item
        is_autoextract_response = is_autoextract_request(response)
        if not self.only_discovery:
            if is_autoextract_response:
                yield from self.parse_item(response)
        else:
            # For discovery-only mode, return only the URLs
            item = {'url': response.url}
            item['scraped_at'] = utc_iso_date()
            if response.meta.get('source_url'):
                item['source_url'] = response.meta['source_url']
            if response.meta.get('link_text'):
                item['link_text'] = response.meta['link_text'].strip()
            yield item

        # Cycle and follow links
        # Currently AutoExtract responses don't contain the full page HTML,
        # so there are no links and nothing to follow
        if response.body and not is_autoextract_response:
            for request in self._requests_to_follow(response):
                yield crawlera_session.init_request(request)
        elif is_autoextract_response:
            # Make another request to fetch the full page HTML
            # Risk of being banned
            self.crawler.stats.inc_value('x_request/discovery')
            meta = {'source_url': response.meta['source_url'],
                    'fingerprint_prefix': FingerprintPrefix.SCRAPY.value}
            request = Request(response.url,
                          meta=meta,
                          callback=self.main_callback,
                          errback=self.main_errback)
            yield crawlera_session.init_request(request)

    def _rule_process_links(self, links):
        """
        Simple helper used by the default Rule to drop links,
        when the same-origin option is enabled.
        """
        if not self.same_origin:
            return links
        valid_links = []
        for lnk in links:
            host = urlsplit(lnk.url).netloc.lower()
            if not hasattr(self, 'allowed_domains') or host in self.allowed_domains:
                valid_links.append(lnk)
        return valid_links

    def _rule_process_req_resp(self, request, response):
        """
        Simple helper used by the default Rule to fix the current request.
        """
        for m in META_TO_KEEP:
            if response.meta.get(m):
                request.meta[m] = response.meta[m]
        request.meta['scraped_at'] = utc_iso_date()
        request.callback = self.parse_page
        request.errback = self.errback_page
        return request

    def _requests_to_follow(self, response):
        seen = set()
        for n, rule in enumerate(self.rules):
            links = [lnk for lnk in rule.link_extractor.extract_links(response) if lnk.url not in seen]
            if links and callable(rule.process_links):
                links = rule.process_links(links)
            for link in links:
                seen.add(link.url)
                meta = {'rule': n, 'link_text': link.text}
                request = self.make_extract_request(link.url, meta=meta)
                if not request:
                    continue
                if callable(rule.process_req_resp):
                    request = rule.process_req_resp(request, response)
                yield request

    def errback_page(self, failure):
        if failure.check(IgnoreRequest, DropItem):
            return
        request = getattr(failure, 'request', None)
        if request:
            self.logger.warning('Page %s failed: %s', request.body, failure)
            self.crawler.stats.inc_value('error/failed_page')
