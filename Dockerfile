FROM ubuntu:20.04 AS builder

ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# 设置时区和软件源
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

# Install dependencies
RUN  apt update \
  && apt install -y python3 python3-dev gcc-8 g++-8 python-dev libgmp-dev python3-pip tzdata cmake libmysqlclient-dev chrpath \
  && apt install -y automake ca-certificates git libtool m4 patch pkg-config unzip make wget curl zip ninja-build npm \
  && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-8 800 --slave /usr/bin/g++ g++ /usr/bin/g++-8 \
  && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai

# install  bazelisk
RUN npm install -g @bazel/bazelisk

WORKDIR /src
ADD . /src

# Bazel build fediux-node & fediux-cli & paillier shared library
RUN bash pre_build.sh \
  && mv -f WORKSPACE_GITHUB WORKSPACE \
  && make mysql=y \
  && tar zcfh bazel-bin.tar.gz bazel-bin/cli \
        bazel-bin/node \
        bazel-bin/_solib* \
        bazel-bin/task_main \
        bazel-bin/src/fediux/pybind_warpper/opt_paillier_c2py.so \
        bazel-bin/src/fediux/pybind_warpper/linkcontext.so \
        bazel-bin/src/fediux/task/pybind_wrapper/ph_secure_lib.so \
        python \
        config \
        example \
        data

FROM docker.1ms.run/ubuntu:20.04 AS runner

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

COPY --from=builder /src/bazel-bin.tar.gz /opt/bazel-bin.tar.gz
COPY --from=builder /src/src/fediux/protos/ /app/src/fediux/protos/

WORKDIR /app

# Copy opt_paillier_c2py.so linkcontext.so to /app/python, this enable setup.py find it.
RUN tar zxf /opt/bazel-bin.tar.gz \
  && mkdir log

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

RUN apt update \
  && apt install -y python3 python3-dev gcc-8 g++-8 python-dev libgmp-dev python3-pip tzdata cmake libmysqlclient-dev chrpath \
  && apt install -y automake ca-certificates git libtool m4 patch pkg-config unzip make wget curl zip ninja-build npm locales \
  && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-8 800 --slave /usr/bin/g++ g++ /usr/bin/g++-8 \
  && locale-gen en_US.UTF-8 \
  && rm -rf /var/lib/apt/lists/*

RUN ln -s -f bazel-bin/cli fediux-cli
RUN ln -s -f bazel-bin/node fediux-node

WORKDIR /app/python

RUN python3 -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
  && python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
  && python3 setup.py install \
  && rm -rf /root/.cache/pip/


WORKDIR /app

# gRPC server port
EXPOSE 50050