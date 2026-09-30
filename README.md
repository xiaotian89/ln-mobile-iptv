# 辽宁移动 IPTV 服务容器

m3u 直播订阅服务 + EPG 节目单自动更新，基于 Docker 容器化部署。

## 功能

- HTTP 服务提供 m3u 直播列表和 epg.xml 节目单
- 每 2 天自动更新 EPG（3 天窗口）
- 配置文件管理，更新 YAUTH 只需重启容器
- GHCR 镜像，一键拉取部署

## 快速部署

```bash
# 创建配置目录
mkdir -p /vol1/1000/iptv-srv

# 下载配置模板
curl -o /vol1/1000/iptv-srv/config.env \
  https://raw.githubusercontent.com/xiaotian89/ln-mobile-iptv/main/scripts/config.env.example

# 编辑配置，填入 YAUTH
vi /vol1/1000/iptv-srv/config.env

# 启动容器
docker run -d \
  --name iptv-srv \
  --restart unless-stopped \
  -p 8100:8100 \
  -v /vol1/1000:/data \
  -v /vol1/1000/iptv-srv:/config \
  ghcr.io/xiaotian89/ln-mobile-iptv:latest
```

## 订阅链接

- m3u: `http://<你的域名或IP>:8100/iptv.m3u`
- epg: `http://<你的域名或IP>:8100/epg.xml`

## 常用命令

```bash
# 查看日志
docker logs iptv-srv

# 手动更新 EPG
docker exec iptv-srv python3 /config/epg_update.py

# 更新 YAUTH 后重启
docker restart iptv-srv
```

## 配置说明

编辑 `/config/config.env`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| YAUTH | 移动 IPTV 认证 token | 必填 |
| HTTP_PORT | HTTP 服务端口 | 8100 |
| EPG_DAYS | EPG 天数 | 3 |

## YAUTH 获取

YAUTH 需要从机顶盒抓包获取。重启机顶盒后，用 Wireshark 抓取启动过程中的 HTTP 请求，在 header 中找到 `YAUTH:` 字段。

更新 YAUTH 后执行 `docker restart iptv-srv` 即可生效。

## 频道列表

频道列表文件 `epg_channels.json` 需要放在配置目录中。可从机顶盒抓包获取，或使用已有的频道列表。
