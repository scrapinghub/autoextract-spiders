from .crawler_spider import CrawlerSpider


class ProductAutoExtract(CrawlerSpider):
    name = 'products'
    page_type = 'product'
