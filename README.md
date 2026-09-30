# 辽宁移动 IPTV 服务容器

辽宁移动 IPTV 的 m3u 直播订阅 + EPG 节目单自动更新 Docker 容器。

## 快速开始

```bash
mkdir -p iptv-srv/{config,data}
cd iptv-srv
```

创建 `docker-compose.yml`：

```yaml
services:
  iptv-srv:
    image: ghcr.io/xiaotian89/ln-mobile-iptv:latest
    container_name: iptv-srv
    ports:
      - "8100:8100"
    volumes:
      - ./config:/config
      - ./data:/data
    environment:
      - TZ=Asia/Shanghai
      - YAUTH=你的YAUTH值
      - HTTP_PORT=8100
      - EPG_DAYS=3
    restart: unless-stopped
```

将频道列表 `epg_channels.json` 放入 `config/` 目录，然后：

```bash
docker compose up -d
```

访问：
- 直播列表：`http://<NAS_IP>:8100/iptv.m3u`
- 节目单：`http://<NAS_IP>:8100/epg.xml`

## 版本号与回滚

镜像支持版本号标签，便于版本管理和回滚：

| 标签格式 | 说明 | 示例 |
|---------|------|------|
| `latest` | 最新版本 | `ghcr.io/xiaotian89/ln-mobile-iptv:latest` |
| `vX.Y.Z` | 指定正式版本 | `ghcr.io/xiaotian89/ln-mobile-iptv:v1.0.0` |
| `sha-xxxxxxx` | 对应 git commit | `ghcr.io/xiaotian89/ln-mobile-iptv:sha-8ab0dab` |

### 回滚到指定版本

修改 `docker-compose.yml` 中的镜像标签：

```yaml
image: ghcr.io/xiaotian89/ln-mobile-iptv:v1.0.0
```

然后重启：

```bash
docker compose up -d
```

### 查看所有可用版本

访问 [GHCR 包页面](https://github.com/xiaotian89/ln-mobile-iptv/pkgs/container/ln-mobile-iptv) 查看所有版本标签。

## 配置

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `YAUTH` | 是 | - | 辽宁移动 IPTV 鉴权 token |
| `HTTP_PORT` | 否 | `8100` | HTTP 服务端口 |
| `EPG_DAYS` | 否 | `3` | EPG 节目单天数窗口 |

### 配置文件（可选）

也可以在 `/config/config.env` 中配置：

```env
YAUTH=你的YAUTH值
HTTP_PORT=8100
EPG_DAYS=3
```

如果同时存在环境变量和 config.env，config.env 会覆盖环境变量。

### 目录结构

```
iptv-srv/
├── docker-compose.yml
├── config/
│   └── epg_channels.json   # 频道列表（必填）
└── data/
    ├── iptv.m3u            # 自动生成
    └── epg.xml             # 自动生成
```

## EPG 自动更新

容器内置 cron 任务，每 2 天 05:00 自动更新 EPG 节目单。

手动触发更新：

```bash
docker exec iptv-srv python3 /app/epg_update.py
```

查看更新日志：

```bash
docker exec iptv-srv cat /data/epg_update.log
```

## YAUTH 获取

详见 [references/yauth-guide.md](references/yauth-guide.md)（Skill 内）。

简要步骤：
1. 重启机顶盒，用 Wireshark 抓包
2. 过滤 `http`，找目标地址 `iptv-cosv3.lnitv.com` 或 `iptv.bimsboot.lnitv.com`
3. HTTP header 中复制 `YAUTH:` 后面的完整值

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## License

MIT
