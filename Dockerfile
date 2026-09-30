FROM python:3-alpine
LABEL maintainer="xiaotian89"
LABEL description="辽宁移动 IPTV 服务容器 - m3u 订阅 + EPG 自动更新"

RUN mkdir -p /config /data

COPY scripts/ /config/
RUN chmod +x /config/entrypoint.sh

WORKDIR /data
EXPOSE 8100

ENTRYPOINT ["sh", "/config/entrypoint.sh"]
