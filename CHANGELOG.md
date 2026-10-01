# 更新日志

## v1.2.0 (2026-10-01)

### 新增
- **Web 抓包管理界面**：容器内置 Flask Web 应用，端口 8101，可视化完成 YAUTH 抓包全流程
- 网口选择：下拉列出 NAS 所有网口，选择机顶盒连接的网口
- 一键建网：自动配置网口 IP（192.168.10.1/24）+ NAT 转发，机顶盒设静态 IP 即可上网
- 实时抓包：页面启动 tcpdump，日志实时滚动，自动高亮 YAUTH 字段
- Token 提取：一键扫描日志提取所有 YAUTH，点击选中
- 一键应用：选中 Token 后自动写入 config.env 并重启容器生效
- 清理网络：停止抓包 + 关闭 NAT + 删除网口 IP，恢复 NAS 网络原状

### 配置项新增
| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `ENABLE_CAPTURE_WEB` | `false` | 设为 true 启用抓包 Web 管理界面 |
| `WEB_PORT` | `8101` | Web 管理界面端口 |
| `CAPTURE_IP` | `192.168.10.1` | 抓包网口配置的 IP（机顶盒网关） |

### 容器运行要求
启用抓包功能时，容器需要额外权限：
```yaml
network_mode: host          # 才能操作宿主机网口
cap_add:
  - NET_ADMIN               # 才能配置 iptables/ip
volumes:
  - /var/run/docker.sock:/var/run/docker.sock  # 才能重启自身
```

### 使用步骤
1. 机顶盒用网线直连 NAS 第二个网口
2. 机顶盒设静态 IP：192.168.10.2，网关 192.168.10.1
3. 浏览器打开 http://NAS_IP:8101
4. 选择抓包网口 → 点「一键配置网络」
5. 点「开始抓包」→ 重启机顶盒 → 等进入主界面
6. 点「提取Token」→ 选中抓到的 YAUTH
7. 点「应用Token并重启」→ 完成
8. 用完点「清理网络」恢复 NAS 网络

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
