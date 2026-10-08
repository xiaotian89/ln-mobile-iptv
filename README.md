# 辽宁移动 IPTV 服务容器

辽宁移动 IPTV 的 m3u 直播订阅 + EPG 节目单自动更新 Docker 容器，内置 YAUTH 抓包 Web 管理界面。

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
      - EPG_CRON=0 5 */2 * *
    restart: unless-stopped
```

将频道列表 `epg_channels.json` 放入 `config/` 目录，然后：

```bash
docker compose up -d
```

访问：
- 直播列表：`http://<NAS_IP>:8100/iptv.m3u`
- 节目单：`http://<NAS_IP>:8100/epg.xml`

## 配置

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `YAUTH` | 是 | - | 辽宁移动 IPTV 鉴权 token |
| `HTTP_PORT` | 否 | `8100` | HTTP 服务端口 |
| `EPG_DAYS` | 否 | `3` | EPG 节目单天数窗口 |
| `EPG_CRON` | 否 | `0 5 */2 * *` | EPG 更新时间（cron 表达式） |
| `ENABLE_CAPTURE_WEB` | 否 | `false` | 启用抓包 Web 管理界面 |
| `WEB_PORT` | 否 | `8101` | 抓包 Web 界面端口 |
| `CAPTURE_IP` | 否 | `192.168.10.1` | 抓包网口配置的 IP（机顶盒网关） |
| `STB_IP` | 否 | `192.168.10.2` | 机顶盒静态 IP（界面提示参考值） |
| `CAPTURE_NETMASK` | 否 | `255.255.255.0` | 抓包网口子网掩码（/24 网段） |

> ⚠️ `STB_IP` / `CAPTURE_IP` / `CAPTURE_NETMASK` 这三个值通常不需要写在 compose 里，抓包 Web 界面可以直接修改并保存到 `/config/config.env`，容器重启后依然生效。首次部署建议通过界面设置。

### EPG_CRON 自定义示例

```yaml
# 每天凌晨 3 点更新
- EPG_CRON=0 3 * * *

# 每周一 04:30 更新
- EPG_CRON=30 4 * * 1

# 每天 02:00 和 14:00 各更新一次
- EPG_CRON=0 2,14 * * *
```

cron 表达式格式：`分 时 日 月 周`

### 配置文件（可选）

也可以在 `/config/config.env` 中配置：

```env
YAUTH=你的YAUTH值
HTTP_PORT=8100
EPG_DAYS=3
EPG_CRON=0 5 */2 * *
ENABLE_CAPTURE_WEB=false
WEB_PORT=8101
STB_IP=192.168.10.2
CAPTURE_IP=192.168.10.1
CAPTURE_NETMASK=255.255.255.0
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

容器内置 cron 任务，默认每 2 天 05:00 自动更新 EPG 节目单。可通过 `EPG_CRON` 环境变量自定义时间。

手动触发更新：

```bash
docker exec iptv-srv python3 /app/epg_update.py
```

查看更新日志：

```bash
docker exec iptv-srv cat /data/epg_update.log
```

查看当前 cron 配置：

```bash
docker exec iptv-srv crontab -l
```

## YAUTH 抓包 Web 管理界面（v1.2.0+）

容器内置可视化抓包工具，无需 Wireshark，在浏览器里完成 YAUTH 获取全流程。

### 启用抓包模式

修改 `docker-compose.yml`，增加网络权限和抓包开关：

```yaml
services:
  iptv-srv:
    image: ghcr.io/xiaotian89/ln-mobile-iptv:latest
    container_name: iptv-srv
    network_mode: host              # 必须：才能操作宿主机网口
    cap_add:
      - NET_ADMIN                   # 必须：才能配置 iptables/ip
    volumes:
      - ./config:/config
      - ./data:/data
      - /var/run/docker.sock:/var/run/docker.sock  # 必须：才能重启自身
    environment:
      - TZ=Asia/Shanghai
      - YAUTH=你的YAUTH值
      - ENABLE_CAPTURE_WEB=true     # 启用抓包界面
      - WEB_PORT=8101
    restart: unless-stopped
```

> ⚠️ 抓包模式使用 `network_mode: host`，不再需要 `ports` 映射，8100 和 8101 端口直接在宿主机上监听。

### 抓包操作步骤（v1.2.3 起，网络参数可自定义）

1. **物理连接**：机顶盒用网线直连 NAS 第二个网口（如 enp4s0，选择空闲网口，不要选 NAS 主网口）
2. **打开管理界面**：浏览器访问 `http://<NAS_IP>:8101`
3. **选择网口**：下拉选择机顶盒连接的那个网口
4. **确认网络参数**：页面顶部输入框显示「机顶盒静态IP / 网关(抓包网口IP) / 子网掩码」——默认 192.168.10.2 / 192.168.10.1 / 255.255.255.0，**如需自定义按自己家庭网络改完后点「💾 保存IP设置」**（保存成功后顶部提示会更新）
5. **一键配置网络**：点「🔧 一键配置网络」，自动给选中网口配 IP（使用保存的网关+掩码）+ NAT 转发
6. **机顶盒设置**：机顶盒设静态 IP = 界面显示的「机顶盒设静态IP」，网关 = 界面显示的「网关」，掩码 = 界面显示的「掩码」
7. **开始抓包**：点「▶ 开始抓包」
8. **重启机顶盒**：机顶盒断电再通电，等它完全启动进入主界面（冷启动才会重新认证获取新 token）
9. **提取 Token**：点「🔍 提取Token」，页面会显示抓到的 YAUTH
10. **应用并重启**：点「✅ 应用Token并重启」，自动写入配置并重启容器
11. **清理网络**：用完点「🧹 清理网络」，恢复 NAS 网络原状（按实际配置的 CIDR 精确删除）

### 自定义机顶盒网络参数（v1.2.3+）

每个人的家庭网络环境不一样，抓包用的内网网段可以完全自定义：

| 输入框 | 配置项 | 默认值 | 说明 |
|--------|--------|--------|------|
| 机顶盒静态IP | `STB_IP` | `192.168.10.2` | 机顶盒需要设置的静态 IP |
| 网关(抓包网口IP) | `CAPTURE_IP` | `192.168.10.1` | 一键配置网络时给抓包网口配的 IP，同时是机顶盒的网关 |
| 子网掩码 | `CAPTURE_NETMASK` | `255.255.255.0` | 抓包网口和机顶盒的子网掩码（支持 /8~/30 任意网段） |

- 修改后点「💾 保存IP设置」→ 写入 `/config/config.env`，容器重启不丢
- 再点「🔧 一键配置网络」才会按新参数配网口
- 示例：家里路由器用 10.0.0.x 网段，可以设 机顶盒 10.0.0.2 / 网关 10.0.0.1 / 掩码 255.0.0.0

### 界面功能说明

| 控件 | 功能 |
|------|------|
| 网口下拉框 | 选择机顶盒连接的物理网口（自动过滤虚拟网口） |
| 机顶盒静态IP / 网关 / 子网掩码 输入框 | 自定义抓包网络参数 |
| 💾 保存IP设置 | 校验并保存 IP/掩码到 config.env（重启生效） |
| 🔧 一键配置网络 | 给选中网口配 IP（自定义网关+掩码）+ 开启 NAT 转发 |
| 🧹 清理网络 | 停止抓包 + 删除网口 IP（按实际 CIDR）+ 清理 iptables 规则 |
| ▶ 开始抓包 | 启动 tcpdump 监听选中网口的 HTTP 流量 |
| ⏹ 停止抓包 | 停止 tcpdump |
| 🔍 提取Token | 扫描抓包日志，提取所有 YAUTH 值 |
| ✅ 应用Token并重启 | 将选中的 YAUTH 写入 config.env 并重启容器 |
| 🔄 仅重启服务 | 只重启容器，不修改配置 |

### 注意事项

- 抓包界面仅在内网使用，不要暴露到公网
- 操作主网口以外的网口，不会影响 NAS 正常上网（NAS 主网口不要选）
- 清理网络后，机顶盒需要改回原来的网络设置
- 如果抓不到 YAUTH，确认机顶盒完全冷启动（断电再通电），热启动可能不重新获取
- YAUTH 是动态 token：平台每次认证下发全新值，过期后需重新抓包应用（机顶盒重启时会发起新认证，重新抓一次即可）
- token 获取**不需要宽带账号密码**：机顶盒播放时平台自动下发，容器只是旁路抓包提取

## YAUTH 手动获取（备用）

如果不用 Web 界面，也可以手动抓包：

1. 机顶盒和电脑连接同一交换机（或电脑做端口镜像）
2. Wireshark 抓包，过滤 `http`
3. 找目标地址 `iptv-cosv3.lnitv.com` 或 `iptv.bimsboot.lnitv.com`
4. HTTP header 中复制 `YAUTH:` 后面的完整值

## 版本号与回滚

镜像支持版本号标签，便于版本管理和回滚：

| 标签格式 | 说明 | 示例 |
|---------|------|------|
| `latest` | 最新版本 | `ghcr.io/xiaotian89/ln-mobile-iptv:latest` |
| `vX.Y.Z` | 指定正式版本 | `ghcr.io/xiaotian89/ln-mobile-iptv:v1.2.3` |
| `sha-xxxxxxx` | 对应 git commit | `ghcr.io/xiaotian89/ln-mobile-iptv:sha-ef0a0b1` |

### 回滚到指定版本

修改 `docker-compose.yml` 中的镜像标签：

```yaml
image: ghcr.io/xiaotian89/ln-mobile-iptv:v1.2.2
```

然后重启：

```bash
docker compose up -d
```

### 查看所有可用版本

访问 [GHCR 包页面](https://github.com/xiaotian89/ln-mobile-iptv/pkgs/container/ln-mobile-iptv) 查看所有版本标签。

## 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## License

MIT
