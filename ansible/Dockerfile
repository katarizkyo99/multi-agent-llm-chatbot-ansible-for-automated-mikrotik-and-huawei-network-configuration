FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y sshpass openssh-client tzdata ansible sshpass python3-pip && \
    ln -fs /usr/share/zoneinfo/Asia/Jakarta /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ansible

COPY . .

CMD ["tail", "-f", "/dev/null"]
