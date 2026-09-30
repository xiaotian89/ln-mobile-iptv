#!/bin/sh
# 辽宁移动IPTV 服务容器入口：HTTP服务 + cron定时更新EPG
if [ -f /config/config.env ]; then
    set -a
    . /config/config.env
    set +a
fi
HTTP_PORT=${HTTP_PORT:-8100}

cd /data
echo "[$(date)] 启动 HTTP 服务端口 $HTTP_PORT"
python3 -m http.server $HTTP_PORT --bind :: &
HTTP_PID=$!

crontab /config/crontab.txt
echo "[$(date)] cron 已加载，启动 crond"
crond -f -l 2 &
CROND_PID=$!

wait -n $HTTP_PID $CROND_PID
echo "[$(date)] 进程退出，关闭容器"
kill $HTTP_PID $CROND_PID 2>/dev/null
