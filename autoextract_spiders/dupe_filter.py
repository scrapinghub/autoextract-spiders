from scrapy.dupefilters import RFPDupeFilter
from scrapy.utils.request import request_fingerprint


class DupeFilter(RFPDupeFilter):
    """
    Deduplication filter which allows configuring a custom prefix in
    the meta property ``fingerprint_prefix`` to be include in the request
    fingerprint.

    Useful to have different deduplication sets based on spider logic.
    """

    def request_fingerprint(self, request):
        slot = request.meta.get('fingerprint_prefix', '')
        fingerprint = request_fingerprint(request)
        return f'{slot}{fingerprint}'

