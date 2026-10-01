#!/usr/bin/env python3
"""
IPTV YAUTH 抓包 Web 管理工具
提供网口选择、一键建网、抓包、token应用、服务重启等功能
"""
import os
import re
import subprocess
import threading
import time
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# 全局状态
CAPTURE_PROC = None
CAPTURE_LOG = []
CAPTURE_LOCK = threading.Lock()
CONFIGURED_IFACE = None
MAIN_IFACE = None

# 配置
CAPTURE_IP = os.environ.get('CAPTURE_IP', '192.168.10.1')
CAPTURE_NETMASK = os.environ.get('CAPTURE_NETMASK', '255.255.255.0')
CONFIG_FILE = os.environ.get('CONFIG_FILE', '/config/config.env')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'iptv-srv')


def run_cmd(cmd, timeout=10):
    """执行系统命令，返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, '', '命令超时'


def get_main_iface():
    """获取主网口（默认路由出口）"""
    rc, out, _ = run_cmd("ip route show default | awk '{print $5}' | head -1")
    return out if rc == 0 and out else 'eth0'


def list_interfaces():
    """列出所有网口"""
    rc, out, _ = run_cmd("ip -o link show | awk -F': ' '{print $2}' | grep -v lo")
    ifaces = []
    if rc == 0:
        for line in out.split('\n'):
            name = line.split('@')[0].strip()
            if name:
                # 获取 IP 地址
                rc2, addr, _ = run_cmd(f"ip -o addr show {name} | awk '{{print $4}}' | head -1")
                ifaces.append({'name': name, 'addr': addr if rc2 == 0 else ''})
    return ifaces


def setup_network(iface):
    """配置抓包网络：给网口配IP + NAT转发"""
    global MAIN_IFACE, CONFIGURED_IFACE
    MAIN_IFACE = get_main_iface()
    
    results = []
    
    # 1. 给网口配 IP
    cmd = f"ip addr add {CAPTURE_IP}/{CAPTURE_NETMASK.split('.')[-1].count('1')*8 if '.' in CAPTURE_NETMASK else 24} dev {iface} 2>&1 || true"
    # 简化：直接用 /24
    cmd = f"ip addr add {CAPTURE_IP}/24 dev {iface} 2>&1; ip link set {iface} up"
    rc, out, err = run_cmd(cmd)
    results.append(f"配置网口 {iface}: {'成功' if rc == 0 else '失败 - ' + err}")
    
    # 2. 开启 IP 转发
    rc, out, err = run_cmd("echo 1 > /proc/sys/net/ipv4/ip_forward")
    results.append(f"开启IP转发: {'成功' if rc == 0 else '失败'}")
    
    # 3. NAT 转发
    run_cmd(f"iptables -t nat -D POSTROUTING -o {MAIN_IFACE} -j MASQUERADE 2>/dev/null")
    run_cmd(f"iptables -D FORWARD -i {iface} -j ACCEPT 2>/dev/null")
    rc, out, err = run_cmd(f"iptables -t nat -A POSTROUTING -o {MAIN_IFACE} -j MASQUERADE && iptables -A FORWARD -i {iface} -j ACCEPT")
    results.append(f"配置NAT转发: {'成功' if rc == 0 else '失败 - ' + err}")
    
    CONFIGURED_IFACE = iface
    return results


def cleanup_network():
    """清理网络配置"""
    global CONFIGURED_IFACE
    if not CONFIGURED_IFACE:
        return ['未配置网络，无需清理']
    
    results = []
    iface = CONFIGURED_IFACE
    main = MAIN_IFACE or get_main_iface()
    
    # 停止抓包
    stop_capture()
    
    # 清理 iptables
    run_cmd(f"iptables -t nat -D POSTROUTING -o {main} -j MASQUERADE 2>/dev/null")
    run_cmd(f"iptables -D FORWARD -i {iface} -j ACCEPT 2>/dev/null")
    results.append("清理iptables规则")
    
    # 删除 IP
    run_cmd(f"ip addr del {CAPTURE_IP}/24 dev {iface} 2>/dev/null")
    results.append(f"删除网口 {iface} 的IP")
    
    CONFIGURED_IFACE = None
    return results


def capture_reader(proc):
    """后台线程：读取 tcpdump 输出"""
    global CAPTURE_LOG
    yauth_pattern = re.compile(r'YAUTH:\s*(\S+)', re.IGNORECASE)
    
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        with CAPTURE_LOCK:
            CAPTURE_LOG.append(line)
            # 只保留最近 500 行
            if len(CAPTURE_LOG) > 500:
                CAPTURE_LOG = CAPTURE_LOG[-500:]


def start_capture(iface):
    """开始抓包"""
    global CAPTURE_PROC
    if CAPTURE_PROC and CAPTURE_PROC.poll() is None:
        return False, '抓包已在运行中'
    
    with CAPTURE_LOCK:
        CAPTURE_LOG.clear()
    
    # 用 tcpdump 抓 HTTP 流量，过滤 YAUTH
    cmd = f"tcpdump -i {iface} -A -s 0 -l 'tcp port 80 or tcp port 8080 or tcp port 8081 or tcp port 8084' 2>&1"
    CAPTURE_PROC = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    t = threading.Thread(target=capture_reader, args=(CAPTURE_PROC,), daemon=True)
    t.start()
    return True, '抓包已启动'


def stop_capture():
    """停止抓包"""
    global CAPTURE_PROC
    if CAPTURE_PROC and CAPTURE_PROC.poll() is None:
        CAPTURE_PROC.terminate()
        try:
            CAPTURE_PROC.wait(timeout=5)
        except subprocess.TimeoutExpired:
            CAPTURE_PROC.kill()
        CAPTURE_PROC = None
        return True, '抓包已停止'
    return False, '抓包未在运行'


def extract_yauth():
    """从抓包日志中提取 YAUTH"""
    with CAPTURE_LOCK:
        log_text = '\n'.join(CAPTURE_LOG)
    
    # 匹配 YAUTH: 后面的内容
    pattern = re.compile(r'YAUTH:\s*([^\r\n]+)', re.IGNORECASE)
    matches = pattern.findall(log_text)
    
    # 去重，保留顺序
    seen = set()
    unique = []
    for m in matches:
        m = m.strip()
        if m and m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


def apply_token(token):
    """将 token 写入 config.env"""
    try:
        content = ''
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
        
        # 替换或添加 YAUTH
        if re.search(r'^YAUTH=.*$', content, re.MULTILINE):
            content = re.sub(r'^YAUTH=.*$', f'YAUTH={token}', content, flags=re.MULTILINE)
        else:
            if content and not content.endswith('\n'):
                content += '\n'
            content += f'YAUTH={token}\n'
        
        with open(CONFIG_FILE, 'w') as f:
            f.write(content)
        return True, 'Token 已写入配置文件'
    except Exception as e:
        return False, f'写入失败: {str(e)}'


def restart_service():
    """重启 IPTV 服务（通过 docker.sock）"""
    rc, out, err = run_cmd(f"curl -s --unix-socket /var/run/docker.sock http://localhost/containers/{CONTAINER_NAME}/restart -X POST", timeout=15)
    if rc == 0:
        return True, '服务重启指令已发送'
    # 尝试用 docker 命令
    rc, out, err = run_cmd(f"docker restart {CONTAINER_NAME}", timeout=15)
    if rc == 0:
        return True, f'服务已重启: {out}'
    return False, f'重启失败: {err}，请手动重启容器'


# ============ 页面 ============

PAGE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPTV YAUTH 抓包工具</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; padding: 16px; max-width: 700px; margin: 0 auto; }
  h1 { font-size: 20px; margin-bottom: 16px; color: #333; }
  .card { background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .card h2 { font-size: 15px; color: #666; margin-bottom: 10px; }
  select, button { width: 100%; padding: 10px; font-size: 14px; border-radius: 6px; border: 1px solid #ddd; margin-bottom: 8px; }
  button { cursor: pointer; font-weight: 500; border: none; color: #fff; }
  .btn-primary { background: #007bff; }
  .btn-success { background: #28a745; }
  .btn-warning { background: #ffc107; color: #333; }
  .btn-danger { background: #dc3545; }
  .btn-secondary { background: #6c757d; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .status { font-size: 13px; color: #666; margin: 6px 0; padding: 6px 10px; background: #f8f9fa; border-radius: 4px; }
  .status.ok { color: #28a745; }
  .status.err { color: #dc3545; }
  .log-box { background: #1e1e1e; color: #d4d4d4; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px; height: 240px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  .log-box .yauth { color: #4ec9b0; font-weight: bold; }
  .token-item { background: #e8f5e9; padding: 8px; border-radius: 4px; margin: 4px 0; font-family: monospace; font-size: 12px; word-break: break-all; cursor: pointer; }
  .token-item:hover { background: #c8e6c9; }
  .row { display: flex; gap: 8px; }
  .row button { flex: 1; }
  .hint { font-size: 12px; color: #999; margin-top: 4px; }
</style>
</head>
<body>
<h1>📺 IPTV YAUTH 抓包工具</h1>

<div class="card">
  <h2>1. 选择抓包网口</h2>
  <select id="iface">
    <option value="">加载中...</option>
  </select>
  <div class="row">
    <button class="btn btn-primary" onclick="setupNet()">🔧 一键配置网络</button>
    <button class="btn btn-warning" onclick="cleanupNet()">🧹 清理网络</button>
  </div>
  <div id="netStatus" class="status">未配置</div>
  <div class="hint">机顶盒设静态IP: 192.168.10.2 / 网关: 192.168.10.1</div>
</div>

<div class="card">
  <h2>2. 抓包控制</h2>
  <div class="row">
    <button class="btn btn-success" onclick="startCap()">▶ 开始抓包</button>
    <button class="btn btn-danger" onclick="stopCap()">⏹ 停止抓包</button>
  </div>
  <div id="capStatus" class="status">未启动</div>
  <div class="hint">开始抓包后，重启机顶盒，等待进入主界面</div>
</div>

<div class="card">
  <h2>3. 抓包日志</h2>
  <div id="log" class="log-box">等待抓包...</div>
  <button style="margin-top:8px" class="btn btn-secondary" onclick="clearLog()">清空日志</button>
</div>

<div class="card">
  <h2>4. 提取的 YAUTH</h2>
  <div id="tokens"><div class="hint">点击「提取Token」按钮扫描日志</div></div>
  <button class="btn btn-primary" onclick="extractToken()">🔍 提取Token</button>
</div>

<div class="card">
  <h2>5. 应用并重启</h2>
  <div class="row">
    <button class="btn btn-success" onclick="applyAndRestart()">✅ 应用Token并重启</button>
    <button class="btn btn-secondary" onclick="restartOnly()">🔄 仅重启服务</button>
  </div>
  <div id="applyStatus" class="status"></div>
</div>

<script>
let currentToken = null;

async function api(url, data) {
  const opts = data ? { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) } : {};
  const r = await fetch(url, opts);
  return r.json();
}

async function loadIfaces() {
  const d = await api('/api/interfaces');
  const sel = document.getElementById('iface');
  sel.innerHTML = d.interfaces.map(i => `<option value="${i.name}">${i.name} ${i.addr ? '('+i.addr+')' : ''}</option>`).join('');
}

async function setupNet() {
  const iface = document.getElementById('iface').value;
  if (!iface) return alert('请选择网口');
  const d = await api('/api/network/setup', {iface});
  document.getElementById('netStatus').innerHTML = d.results.map(r => '<div>'+r+'</div>').join('');
  document.getElementById('netStatus').className = 'status ok';
}

async function cleanupNet() {
  const d = await api('/api/network/cleanup');
  document.getElementById('netStatus').innerHTML = d.results.map(r => '<div>'+r+'</div>').join('');
  document.getElementById('netStatus').className = 'status';
}

async function startCap() {
  const iface = document.getElementById('iface').value;
  if (!iface) return alert('请选择网口');
  const d = await api('/api/capture/start', {iface});
  document.getElementById('capStatus').textContent = d.message;
  document.getElementById('capStatus').className = 'status ' + (d.success ? 'ok' : 'err');
  if (d.success) pollLog();
}

async function stopCap() {
  const d = await api('/api/capture/stop');
  document.getElementById('capStatus').textContent = d.message;
  document.getElementById('capStatus').className = 'status';
}

let pollTimer = null;
async function pollLog() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const d = await api('/api/capture/log');
    const logEl = document.getElementById('log');
    logEl.innerHTML = d.log.map(l => l.replace(/(YAUTH:\s*\S+)/gi, '<span class="yauth">$1</span>')).join('\n') || '等待抓包...';
    logEl.scrollTop = logEl.scrollHeight;
  }, 1000);
}

function clearLog() {
  document.getElementById('log').innerHTML = '已清空';
}

async function extractToken() {
  const d = await api('/api/token/extract');
  const el = document.getElementById('tokens');
  if (d.tokens.length === 0) {
    el.innerHTML = '<div class="hint">未找到 YAUTH，请确认机顶盒已重启并完成启动</div>';
    return;
  }
  el.innerHTML = d.tokens.map((t,i) => `<div class="token-item" onclick="selectToken(${i})">${t}</div>`).join('');
  window._tokens = d.tokens;
  currentToken = d.tokens[0];
}

function selectToken(i) {
  currentToken = window._tokens[i];
  alert('已选中此Token');
}

async function applyAndRestart() {
  if (!currentToken) return alert('请先提取并选中Token');
  const d = await api('/api/token/apply', {token: currentToken});
  let msg = d.message;
  if (d.success) {
    const r = await api('/api/service/restart');
    msg += ' | ' + r.message;
  }
  document.getElementById('applyStatus').textContent = msg;
  document.getElementById('applyStatus').className = 'status ' + (d.success ? 'ok' : 'err');
}

async function restartOnly() {
  const d = await api('/api/service/restart');
  document.getElementById('applyStatus').textContent = d.message;
  document.getElementById('applyStatus').className = 'status ' + (d.success ? 'ok' : 'err');
}

loadIfaces();
</script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(PAGE)


@app.route('/api/interfaces')
def api_interfaces():
    return jsonify({'interfaces': list_interfaces()})


@app.route('/api/network/setup', methods=['POST'])
def api_network_setup():
    data = request.get_json()
    iface = data.get('iface', '')
    if not iface:
        return jsonify({'error': '缺少网口参数'}), 400
    results = setup_network(iface)
    return jsonify({'results': results})


@app.route('/api/network/cleanup', methods=['POST'])
def api_network_cleanup():
    results = cleanup_network()
    return jsonify({'results': results})


@app.route('/api/capture/start', methods=['POST'])
def api_capture_start():
    data = request.get_json()
    iface = data.get('iface', '')
    if not iface:
        return jsonify({'error': '缺少网口参数'}), 400
    success, msg = start_capture(iface)
    return jsonify({'success': success, 'message': msg})


@app.route('/api/capture/stop', methods=['POST'])
def api_capture_stop():
    success, msg = stop_capture()
    return jsonify({'success': success, 'message': msg})


@app.route('/api/capture/log')
def api_capture_log():
    with CAPTURE_LOCK:
        log = list(CAPTURE_LOG)
    return jsonify({'log': log})


@app.route('/api/token/extract')
def api_token_extract():
    tokens = extract_yauth()
    return jsonify({'tokens': tokens})


@app.route('/api/token/apply', methods=['POST'])
def api_token_apply():
    data = request.get_json()
    token = data.get('token', '')
    if not token:
        return jsonify({'error': '缺少token'}), 400
    success, msg = apply_token(token)
    return jsonify({'success': success, 'message': msg})


@app.route('/api/service/restart', methods=['POST'])
def api_service_restart():
    success, msg = restart_service()
    return jsonify({'success': success, 'message': msg})


if __name__ == '__main__':
    port = int(os.environ.get('WEB_PORT', '8101'))
    app.run(host='0.0.0.0', port=port, debug=False)
