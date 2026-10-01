#!/bin/sh
# 辽宁移动IPTV 服务容器入口：HTTP服务 + cron定时更新EPG + 可选抓包Web管理
# 兼容两种配置方式：1) /config/config.env 文件 2) 容器环境变量
if [ -f /config/config.env ]; then
    set -a
    . /config/config.env
    set +a
fi
HTTP_PORT=${HTTP_PORT:-8100}
EPG_CRON=${EPG_CRON:-"0 5 */2 * *"}
ENABLE_CAPTURE_WEB=${ENABLE_CAPTURE_WEB:-false}
WEB_PORT=${WEB_PORT:-8101}

cd /data
echo "[$(date)] 启动 HTTP 服务端口 $HTTP_PORT"
python3 -m http.server $HTTP_PORT --bind :: &
HTTP_PID=$!

# 动态生成 crontab，支持通过 EPG_CRON 环境变量自定义更新时间
echo "$EPG_CRON /usr/local/bin/python3 /app/epg_update.py >> /data/epg_update.log 2>&1" > /tmp/crontab.txt
crontab /tmp/crontab.txt
echo "[$(date)] cron 已加载（EPG更新时间: $EPG_CRON），启动 crond"
crond -f -l 2 &
CROND_PID=$!

# 可选：启动抓包 Web 管理界面
if [ "$ENABLE_CAPTURE_WEB" = "true" ]; then
    echo "[$(date)] 启动抓包 Web 管理界面，端口 $WEB_PORT"
    python3 /app/capture_web.py &
    WEB_PID=$!
    echo "[$(date)] Web 管理地址: http://<NAS_IP>:$WEB_PORT"
else
    WEB_PID=""
fi

if [ -n "$WEB_PID" ]; then
    wait -n $HTTP_PID $CROND_PID $WEB_PID
else
    wait -n $HTTP_PID $CROND_PID
fi
echo "[$(date)] 进程退出，关闭容器"
kill $HTTP_PID $CROND_PID $WEB_PID 2>/dev/null
