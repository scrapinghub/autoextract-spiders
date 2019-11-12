# -*- coding: utf-8 -*-

# Scrapy settings for autoextract_spiders project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'autoextract_spiders'

SPIDER_MODULES = ['autoextract_spiders.spiders']
NEWSPIDER_MODULE = 'autoextract_spiders.spiders'

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'

ROBOTSTXT_OBEY = False

# Concurrency limit
CONCURRENT_REQUESTS = 16

# Maximum depth that will be allowed to crawl for any site
DEPTH_LIMIT = 2
DEPTH_STATS_VERBOSE = True

# Disable AutoThrottle middleware
AUTHTHROTTLE_ENABLED = False

# Setup Retry middleware
RETRY_TIMES = 2
RETRY_HTTP_CODES = [429]

# More spam from Link Filter Middleware
# LINK_FILTER_MIDDLEWARE_DEBUG = True

SPIDER_MIDDLEWARES = {
    'scrapy_link_filter.middleware.LinkFilterMiddleware': 950,
}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    'scrapy_crawlera.CrawleraMiddleware': 300,
    'scrapy_count_filter.middleware.GlobalCountFilterMiddleware': 541,
    'scrapy_count_filter.middleware.HostsCountFilterMiddleware': 542,
    'scrapy_autoextract.middlewares.AutoExtractMiddleware': 543,
}

AUTOEXTRACT_USER = '[API key]'

CRAWLERA_ENABLED = False
CRAWLERA_APIKEY = '[API key]'
