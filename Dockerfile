FROM alpine:latest

ARG VERSION=v1.1

RUN apk -U --no-cache add \
    python py-setuptools

RUN apk -U --no-cache add --virtual build-dependencies \
    git \
    py-pip \
    python \
    python-dev \
    gcc \
    build-base \
    libffi-dev \
    openssl \
    openssl-dev \
    musl-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev \
    libxml2 \
    libxslt 

ADD https://raw.githubusercontent.com/PokemonAlpha/AlphaBot/$VERSION/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && find / -name '*.pyc' -o -name '*.pyo' -exec rm -f {} \;

ADD https://github.com/PokemonAlpha/AlphaBot/archive/$VERSION.tar.gz /tmp
RUN apk -U --no-cache add --virtual .tar-deps tar \
    && cat /tmp/$VERSION.tar.gz | tar -zxf - --strip-components=1 -C / \
    && apk del .tar-deps \
    && rm /tmp/$VERSION.tar.gz
WORKDIR /AlphaBot

RUN apk del build-dependencies \
    && rm -rf /var/cache/apk/* \
    && rm -rf /tmp/* \
    && rm -rf /AlphaBot/.git

ENTRYPOINT ["python", "run.py", ">>", "/tmp/log/log"]
