# AutoExtract Spiders 🧠🕷

AutoExtract Spiders are a easy to use tool, built on top of [ScrapingHub's AI Enabled Automatic Data Extraction](https://scrapinghub.com/autoextract) and designed for e-commerce and article data extraction at scale.

There are a few different use-cases for the spiders:

1. extracting multiple Products, or Articles from a list or URLs of Products, or Articles (no discovery)
2. discovering Products, or Articles from a list of seed URLs, optionally following defined discovery rules (the most popular use-case)
3. discovering only the links from a list of seed URLs, by following defined discovery rules

All three cases are available to all the spiders, as documented below.

The available spiders are:

* The articles AutoExtract spider, used to extract and discover articles
* The products AutoExtract spider, used to extract and discover products

The spiders can be started from command line, or deployed in a [ScrapyCloud](https://scrapinghub.com/scrapy-cloud) project.


## Spider options

The spiders have exactly the same options, the only difference between them is they are specialized for extracting either articles, or products.

* **seeds** (required): one, or more seed URLs (eg: https://www.example.com/home/)
* **seeds_file_url** (optional - no default value): a URL to a plain text file with a list of seed URLs, each on a separate line.
* **threshold** (optional, default 0.1): drop all items below the threshold, which represents the confidence that the URL is the page-type you specified (article, or product), as recognised by the extraction engine. The probability is returned for all the items and is between 0.0 and 1.0, where 0 means "the URL is definitely not that page-type" and 1 means "the URL is that page-type for sure" and in this case the quality of the extraction will be very good.
* **max-items** (optional - default 100): how many items (articles, or products) should the spider extract. It's important to specify this if you need a small sample and a fast extraction. When the items are extracted, the spider stops. The default limit SHOULD be changed if you specify multiple seeds, because the default limit is global, not per seed.
* **max-pages** (optional - default 1000): how many pages should the spider follow, when discovering links. It's important to limit the number of pages, otherwise the spider can run for days, looking for data.
* **allow-links** (optional - no default value): what URL patterns should the spider follow. It's important to specify this option to optimise the discovery of items, and speedup the spider 10 times or more.
  How to find the patterns? Open the website you want to extract look at the URLs of the items.
  Example 1: articles from https://www.bbc.com/news, all the article links contain "/news/" so you can allow only those links. To fine-tune even more, you could specify "/news/world" to allow only the world news.
  Example 2: articles from https://www.nytimes.com/, all the article links contain "/yyyy/mm/dd/" so the [regex](https://docs.python.org/3/library/re.html#regular-expression-syntax) for that is "/[0-9]{4}/[0-9]{2}/[0-9]{2}/".
* **ignore-links** (optional - no default value): what URL patterns NOT to follow. This is the opposite of "allow-links" and is useful when the majority of the links have items, but you want to ignore just a few specific URLs that slow down the discovery.
* **same-domain** (optional - default True): by default the spider will limit the discovery of links to the same domains as the seeds (eg: if the seed is "dailymail.co.uk", the spider will never extract the links pointing to "facebook.com"). Set to False if you need to disable this, but also check the "extract-rules" advanced option.

The options that accept multiple items (seeds, allow-links, deny-links) are strings, or lists in YAML, or JSON format. Example list as YAML: `[item1, item2, item3]`. Example list as JSON: `["item1", "item2", "item3"]`.

By default, all the spiders will ignore a lot of URLs that are obviously not items (eg: terms & conditions, privacy policy, contact pages, login & create account, etc).


### Advanced options

* **count-limits** (optional): this option is a dictionary represented as YAML or JSON, that can contain 4 fields. "page_count" and "item_count" - are used to stop the spider if the number of requests, or items scraped is larger than the value provided. "page_host_count" and "item_host_count" - are used to start ignoring requests if the number of requests, or items scraped per host is larger than the value provided (they are also exposed as "max-items" and "max-pages").
* **extract-rules** (optional): this option is also a dictionary represented as YAML or JSON, that can contain 4 fields. "allow_domains" and "deny_domains" - one, or more domains to specifically limit to, or specifically reject; make sure to disable the "same-domain" option for this to work. "allow" and "deny" - one, or more sub-strings, or patterns to specifically allow, or reject (they are also exposed as "allow-links" and "ignore-links").

**Note**: The higher level options "allow-links" and "ignore-links" will over-write the options defined in "extract-rules".<br/>
Also the higher level options "max-items" and "max-pages" will over-write the options defined in "count-limits".


The next two options will switch to **discovery-only mode**, or will switch to **extract only (no discovery)**:

* **discovery-only** (optional - default False): used to discover and return only the links, without using AutoExtract.
* **items** (used **instead of the seeds**): one, or more item URLs. Use this option if you know the exact article, or product URLs and you want to send them to AutoExtract as they are. There is no discovery when you provide the "items" option and all the discovery options above have *no effect*.


### Extra options

There are a few options that can be tweaked either in command line, or ScrapyCloud settings, that will change the behaviour of the spiders.
Be careful when changing the ScrapyCloud settings, because they will affect all the future jobs.

#### Crawlera

It's possible to use [Crawlera](https://scrapinghub.com/crawlera) to avoid bans during discovery process and significantly improve quality of your crawl in some cases.

* **CRAWLERA_ENABLED** (default ``False``): enable using Crawlera for discovery
* **CRAWLERA_APIKEY** (no default value): provide your Crawlera API key to use it

**Note**: Crawlera won't be used for your requests to AutoExtract API.

#### Frontera

[Frontera](https://github.com/scrapinghub/hcf-backend) integration is enabled by default using [HCF](https://doc.scrapinghub.com/api/frontier.html) [backend](https://github.com/scrapinghub/hcf-backend) to provide URL deduplication, a possibility to scale your crawler and some other interesting features out-of-the-box. It doesn't require additional settings: the default configuration enables producer/consumer behaviours within the same spider with fairly good defaults (using a single frontier slot).

However you could always tune it according to your needs. If that's the case, it might be useful to get familiar with [shub-workflow](https://github.com/scrapinghub/shub-workflow/wiki/Basic-Tutorial) describing the topic and related settings in more detail.

##### Scaling

Shortly, you could scale a crawler by running multiple producers and consumers in parallel. An amount of slots in a single frontier defines how many consumer jobs you may have (note that each consumer reads only from a single slot). On the other hand, each producer writes data to all slots, so there's no limit on the amount of producer jobs.

HCF backend logic can be modified by providing an additional spider argument ``frontera_settings_json`` with a settings dictionary in JSON format. For example, to launch your spider in producer-only mode, you should provide ``frontera_settings_json={"HCF_CONSUMER_FRONTIER":null}``(similarly, reset a setting ``HCF_PRODUCER_FRONTIER`` for consumer-only mode). Additional settings for the backend can be found [here](https://github.com/scrapinghub/hcf-backend/blob/0.4.3/hcf_backend/backend.py#L45) and get overwritten in the same way.

##### Manager

To facilitate periodic scheduling of consumers there's one useful tool provided by ``hcf-backend`` package called ``hcfmanager.py``, which the project installs as ``manager.py``. This script allows easy handling of consumers, by scheduling a consumer job for each free slot with at least one pending request. Basic command line:

```sh
> manager.py <spider name> <frontier name> <slots prefix> --loop-mode=<seconds> [--project-id=<project_id>] [--max-running-jobs=<max parallel jobs>] [--spider-args=<json dict>] [--job-settings=<json dict>]
```

An example for this project:

```sh
> manager.py articles autoextract articles --loop-mode=120
```

It also supports a loop mode, under which it will continue monitoring the slots and schedule jobs for them, and will not finish until there is no more pending requests available on slots. If the script runs on ScrapyCloud, no need to pass ``--project-id``, as it is automatically detected.

##### URL deduplication

URL deduplication provided by Frontera works in the following way: a frontera slot stores information about links even after consuming/deleting the links from the slot queue, so when you'll try to add the same link to the slot, it will be ignored. Sometimes the behaviour is not what's needed (like, when you want to recrawl with different parameters). The simplest solution in this case would be to drop a slot (or a whole frontier), using ``hcfpal.py`` script and recrawl from scratch. To delete a slot, launch the script from Dash UI providing a frontier name (default is ``autoextract``) and the slot prefix (default is ``articles``) or the full slot name via script arguments, like ``delete autoextract articles0``.

The [hcfpal.py](https://github.com/scrapinghub/hcf-backend/blob/0.4.3/hcf_backend/utils/hcfpal.py) has options for counting, listing, deleting, moving and dumping slots content and can be also used from your local machine after installing ``hcf-backend`` package, check its built-in command-line helper.


**Note** Frontera integration can be disabled via **FRONTERA_DISABLED** setting.

#### Other options

* **DEPTH_LIMIT** (default 2): the maximum depth that will be allowed to crawl for a site.
* **CLOSESPIDER_TIMEOUT** (no default value): if the spider is running for more than that number of seconds, it will be automatically closed.

Of course, all the other [Scrapy settings](https://scrapy.readthedocs.io/en/latest/topics/settings.html) are available as well.


## Running the spiders in command line

Running the spiders requires installing [Scrapy](https://scrapy.readthedocs.io/).

To run the articles spider, discovery and extraction:

```sh
> scrapy crawl articles -s AUTOEXTRACT_USER=<your API key> -a seeds=<one or more seed urls> -a threshold=.5
```

In this example, the spider will ignore articles that have a probability lower than 0.5.

To run the products spider, discovery and extraction:

```sh
> scrapy crawl products -s AUTOEXTRACT_USER=<your API key> -a seeds=<one or more seed urls> -a max-items=10
```

In this example, the spider will stop processing requests after extracting 10 items.


## Deploy on Scrapy Cloud

This step requires installing [Scrapinghub's command line client](https://shub.readthedocs.io/), also called "shub".

You need to create a ScrapyCloud project first. Once you're done, to deploy the spiders in the project:

```sh
> shub deploy <project ID>
```

For more info about ScrapyCloud check the [Scrapinghub's Support Center](https://support.scrapinghub.com/support/home) page.
