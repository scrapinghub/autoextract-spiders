from setuptools import setup, find_packages

setup(
    name='autoextract-spiders',
    version='0.1.0',
    author='Scrapinghub Inc',
    description='Scrapinghub AutoExtract spiders',
    packages=find_packages(exclude=['tests']),
    entry_points={'scrapy': ['settings = autoextract_spiders.settings']},
)
