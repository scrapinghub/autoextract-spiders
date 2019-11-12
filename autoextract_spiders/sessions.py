
from crawlera_session import RequestSession as _Session


def update_redirect_middleware(settings):
    if settings.getbool('CRAWLERA_ENABLED'):
        redirect_mware = 'scrapy.downloadermiddlewares.redirect.RedirectMiddleware'
        pos = settings.get('DOWNLOADER_MIDDLEWARES_BASE').pop(redirect_mware)
        DW_MIDDLEWARES = settings.get('DOWNLOADER_MIDDLEWARES')
        DW_MIDDLEWARES['crawlera_session.CrawleraSessionRedirectMiddleware'] = pos


class RequestSession(_Session):

    def init_start_requests(self, wrapped):
        orig_wrapper = super().init_start_requests(wrapped)
        def _wrapper(spider):
            is_crawlera_enabled = spider.settings.getbool('CRAWLERA_ENABLED')
            yield from (orig_wrapper if is_crawlera_enabled else wrapped)(spider)
        _wrapper.__name__ = wrapped.__name__
        return _wrapper

    def follow_session(self, wrapped):
        orig_wrapper = super().follow_session(wrapped)
        def _wrapper(spider, response):
            is_crawlera_enabled = spider.settings.getbool('CRAWLERA_ENABLED')
            yield from (orig_wrapper if is_crawlera_enabled else wrapped)(spider, response)
        _wrapper.__name__ = wrapped.__name__
        return _wrapper


crawlera_session = RequestSession(x_crawlera_profile='desktop')
