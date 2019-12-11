from setuptools import setup, find_packages

NAME = 'autoextract-spiders'


def get_version():
    about = {}
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, NAME.replace('-', '_'), '__version__.py')) as f:
        exec(f.read(), about)
    return about['__version__']


setup(
    name=NAME,
    version=get_version(),
    author='Scrapinghub Inc',
    description='Scrapinghub AutoExtract spiders',
    packages=find_packages(exclude=['tests']),
    scripts=['scripts/hcfpal.py', 'scripts/manager.py'],
    entry_points={'scrapy': ['settings = autoextract_spiders.settings']},
)
