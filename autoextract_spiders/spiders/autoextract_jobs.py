from .crawler_spider import CrawlerSpider


class JobsAutoExtract(CrawlerSpider):
    name = 'jobs'
    page_type = 'jobPosting'
