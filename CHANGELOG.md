# 更新日志

## v1.1.0 (2026-09-30)

### 新增
- 支持通过 `EPG_CRON` 环境变量自定义 EPG 节目单更新时间，不再写死
- entrypoint.sh 动态生成 crontab，容器启动时打印当前 EPG 更新时间

### 配置项新增
| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `EPG_CRON` | `0 5 */2 * *` | EPG 更新 cron 表达式（每2天 05:00） |

### 示例
```yaml
# 每天凌晨 3 点更新
environment:
  - EPG_CRON=0 3 * * *

# 每周一 04:30 更新
environment:
  - EPG_CRON=30 4 * * 1
```

## v1.0.0 (2026-09-30)

首个正式版本。

### 新增
- m3u 直播订阅 HTTP 服务（默认端口 8100，支持 IPv6）
- EPG 节目单自动更新（每 2 天 05:00 执行，默认 3 天窗口）
- 支持两种配置方式：`/config/config.env` 文件 或 容器环境变量
- 辽宁移动 IPTV 频道列表（139 个频道）
- EPG 抓取脚本（10 线程并发，支持断点续传）

### 修复
- 修复挂载覆盖问题：脚本移至镜像内 `/app/` 目录，`/config/` 仅挂载用户配置，避免挂载覆盖镜像内脚本

### 配置项
| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `YAUTH` | （必填） | 辽宁移动 IPTV 鉴权 token |
| `HTTP_PORT` | `8100` | HTTP 服务端口 |
| `EPG_DAYS` | `3` | EPG 节目单天数窗口 |

### 镜像标签
- `latest` - 最新版本
- `v1.0.0` - 指定版本
- `sha-xxxxxxx` - 对应 git commit 的版本

### 回滚方式
```bash
# 修改 docker-compose.yml 中的镜像标签
image: ghcr.io/xiaotian89/ln-mobile-iptv:v1.0.0
# 重启生效
docker compose up -d
```
