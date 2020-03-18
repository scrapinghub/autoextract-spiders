FROM scrapinghub/scrapinghub-stack-scrapy:1.8-py3
WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
ENV SCRAPY_SETTINGS_MODULE autoextract_spiders.settings
COPY . /app
RUN python setup.py install
