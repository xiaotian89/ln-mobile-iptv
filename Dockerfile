FROM python:3-alpine
LABEL maintainer="xiaotian89"
LABEL description="辽宁移动 IPTV 服务容器 - m3u 订阅 + EPG 自动更新"

RUN mkdir -p /app /config /data

COPY scripts/ /app/
RUN chmod +x /app/entrypoint.sh

WORKDIR /data
EXPOSE 8100

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
