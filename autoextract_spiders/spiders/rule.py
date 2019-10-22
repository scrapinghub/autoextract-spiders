def _get_method(method, spider):
    if callable(method):
        return method
    elif isinstance(method, str):
        return getattr(spider, method, None)


class Rule:
    """
    Rule similar to the Crawl Rule, but simpler.
    """

    def __init__(self,
                 link_extractor,
                 callback=None,
                 cb_kwargs=None,
                 follow=None,
                 process_links=None,
                 process_req_resp=None):
        self.link_extractor = link_extractor
        self.callback = callback
        self.cb_kwargs = cb_kwargs or {}
        self.process_links = process_links
        self.process_req_resp = process_req_resp
        if follow is None:
            self.follow = False if callback else True
        else:
            self.follow = follow

    def _compile(self, spider):
        self.callback = _get_method(self.callback, spider)
        self.process_links = _get_method(self.process_links, spider)
        self.process_req_resp = _get_method(self.process_req_resp, spider)

    def __str__(self):
        proc_links = 'yes' if self.process_links else 'no'
        proc_req_resp = 'yes' if self.process_req_resp else 'no'
        return (f'Rule({self.link_extractor}, follow={self.follow}, ' +  # noqa: W504
                f'process_links={proc_links}, process_req_resp={proc_req_resp})')

    __repr__ = __str__
