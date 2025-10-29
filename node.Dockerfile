FROM docker.1ms.run/ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

COPY fediux-linux-amd64.tar.gz fediux-linux-arm64.tar.gz /opt/
COPY src/fediux/protos/ /app/src/fediux/protos/

WORKDIR /app

RUN tar zxf /opt/fediux-linux-$(dpkg --print-architecture).tar.gz \
  && mkdir log \
  && rm -rf /opt/fediux-linux-amd64.tar.gz \
  && rm -rf /opt/fediux-linux-arm64.tar.gz

RUN ln -s -f bazel-bin/cli fediux-cli
RUN ln -s -f bazel-bin/node fediux-node

COPY python/ /app/python/
COPY example/ /app/example/

WORKDIR /app/python

# Install python3 and GCC openmp (Depends with cryptFlow2 library)
RUN apt-get update \
  && apt-get install -y python3 python3-dev libgmp-dev python3-pip tzdata wget libmysqlclient-dev \
  && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
  && pip install -e . \
  && rm -rf /root/.cache/pip/

WORKDIR /app

# gRPC server port
EXPOSE 50050
# docker buildx build  --platform linux/amd64,linux/arm64 -t image.onecode.cmict.cloud/bigmodel-yfzx/fediux-node:1.7.1.0724 -f node.Dockerfile . --push