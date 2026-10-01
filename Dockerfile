FROM python:3-alpine
LABEL maintainer="xiaotian89"
LABEL description="辽宁移动 IPTV 服务容器 - m3u 订阅 + EPG 自动更新 + YAUTH 抓包 Web 管理"

RUN apk add --no-cache tcpdump iptables iproute2 curl tzdata && \
    pip install --no-cache-dir flask

RUN mkdir -p /app /config /data

COPY scripts/ /app/
RUN chmod +x /app/entrypoint.sh /app/capture_web.py

WORKDIR /data
EXPOSE 8100 8101

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
