# 更新日志

## v1.2.2 (2026-10-08)

### 修复
- **【抓包页面"加载中"真正根因】JS 语法错误**：页面脚本中 `join('\n')` 被 Python 三引号模板解析成真实换行符，浏览器收到跨行非法 JS 导致整个脚本不运行、`/api/interfaces` 请求从未发出，网口下拉永远"加载中"（此 bug 自 v1.2.0 抓包界面诞生起存在，curl 检查 HTML 无法发现）；改为 `join('<br>')`
- **抓包网口列表只显示物理网口**：过滤 veth*/br-*/docker0/ovs-*/virbr*/tap*/vnet* 等虚拟接口（此前 NAS 返回 57 个网口，物理口被淹没，下拉框长时间"加载中"）
- **前端网口加载失败提示**：接口异常时显示"加载失败，请刷新页面"而非一直转圈
- **清理网络按钮失效**：cleanup_network 原先依赖进程内存变量 `CONFIGURED_IFACE`，容器重启后变量丢失导致按钮直接返回"未配置网络，无需清理"，而实际网络配置（网口 IP + NAT）仍在宿主机上；改为主动检测（扫描配了 192.168.10.1 的网口 + 清理 iptables 规则），幂等且不依赖内存状态
- **三个按钮 405 失效**：前端 `api()` 无参调用默认发 GET，但 `/api/network/cleanup`、`/api/capture/stop`、`/api/service/restart` 后端只接受 POST，导致清理网络、停止抓包、仅重启服务三个按钮点击后 405 无反应（停止抓包失效还会留下 tcpdump 孤儿进程）；改为传空对象强制 POST
- **"开启IP转发"假警报**：容器内 `/proc/sys` 只读导致 `echo 1 > /proc/sys/net/ipv4/ip_forward` 报错，但宿主机转发本就开启；写失败时回读宿主状态，已开启则显示"已开启(宿主默认)"
- **双 compose 文件合并为单文件 host 版**：修复飞牛容器管理界面读不到 Compose 文件（`com.docker.compose.project.config_files` 多路径）的问题；host 模式定稿，不再提供 bridge 切换

### 改进
- **Token 应用反馈明确化**：点「应用Token并重启」后显示"✅ Token 已应用: xxx（前12位）| 服务重启指令已发送"，失败显示具体原因
- **动态 token 适配说明**：辽宁移动平台每次认证下发全新 YAUTH（V1.0 新格式），token 会过期，过期后需重新抓包应用

### 说明
- 本次为纯本地迭代版本（未推送 GitHub），经豆包浏览器全流程实测：网口加载、一键配置网络（含 IP 转发检测）、开始/停止抓包、自动停止、Token 提取/应用、清理网络、播放 302、EPG 更新 139/139 全部验证通过

## v1.2.1 (2026-10-08)

### 修复
- **抓包检测到 YAUTH 后自动停止**：capture_reader 识别到 YAUTH 字段即自动终止 tcpdump，避免日志无限增长和空转（此前需手动点「停止抓包」）
- **tcpdump 进程组终止**：抓包进程独立进程组启动，停止/自动停止时 killpg 整组终止，杜绝 shell 被杀后 tcpdump 残留为孤儿进程
- **手动执行 EPG 更新也能取到 YAUTH**：epg_update.py 在环境变量缺失时自动从 /config/config.env 读取配置，`docker exec iptv-srv python3 /app/epg_update.py` 不再报「YAUTH 未设置」

### 改进
- 抓包日志 API 返回运行状态，前端轮询到自动停止后停止刷新并提示「已自动停止（检测到 YAUTH）」

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
