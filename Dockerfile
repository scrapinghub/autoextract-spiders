FROM scrapinghub/scrapinghub-stack-scrapy:2.0
WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
ENV SCRAPY_SETTINGS_MODULE autoextract_spiders.settings
COPY . /app
RUN python setup.py install
