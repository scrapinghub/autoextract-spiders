from scrapy.settings import default_settings
from scrapy_frontera.middlewares import (
    SchedulerSpiderMiddleware as _SSpiderMiddleware,
    SchedulerDownloaderMiddleware as _SDownloaderMiddleware,
)


def reset_scheduler_on_disabled_frontera(settings):
    if settings.getbool('FRONTERA_DISABLED'):
        settings['SCHEDULER'] = default_settings.SCHEDULER


class FronteraDisabledMixin:
    @property
    def is_frontera_enabled(self):
        return not self.crawler.settings.getbool('FRONTERA_DISABLED')


class SchedulerSpiderMiddleware(_SSpiderMiddleware, FronteraDisabledMixin):
    def process_spider_output(self, response, result, spider):
        if self.is_frontera_enabled:
            return self.scheduler.process_spider_output(response, result, spider)
        yield from result

    def process_start_requests(self, start_requests, spider):
        redirect_setting = 'FRONTERA_SCHEDULER_START_REQUESTS_TO_FRONTIER'
        redirect_requests = self.crawler.settings.getbool(redirect_setting)
        if self.is_frontera_enabled and redirect_requests:
            return []
        return start_requests

class SchedulerDownloaderMiddleware(_SDownloaderMiddleware, FronteraDisabledMixin):
    def process_exception(self, request, exception, spider):
        if self.is_frontera_enabled:
            return self.scheduler.process_exception(request, exception, spider)
