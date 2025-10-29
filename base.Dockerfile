FROM image.onecode.cmict.cloud/bigmodel-yfzx/fediux-node:1.7.1.amd64.build
#FROM image.onecode.cmict.cloud/bigmodel-yfzx/fediux-node:1.7.1.arm64.build

COPY python/ /app/python/
COPY example/ /app/example/

WORKDIR /app/python

RUN python3 setup.py develop --uninstall \
    && python3 -m pip install -r requirements.txt \
    && python3 -m pip install -e . \
    && rm -rf /root/.cache/pip/

WORKDIR /app
