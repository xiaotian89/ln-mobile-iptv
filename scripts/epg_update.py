#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""辽宁移动IPTV EPG自动更新 - 容器版，配置从环境变量读取"""
import json, urllib.request, concurrent.futures, datetime, os, sys

CHANNELS_FILE = os.environ.get("CHANNELS_FILE", "/config/epg_channels.json")
OUT_FILE = os.environ.get("OUT_FILE", "/data/epg.xml")
DAYS = int(os.environ.get("EPG_DAYS", "3"))

def load_config_env():
    """环境变量缺失时从 /config/config.env 补充（docker exec 手动执行也能取到 YAUTH）"""
    if os.environ.get("YAUTH"):
        return
    cfg = os.environ.get("CONFIG_FILE", "/config/config.env")
    try:
        with open(cfg, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v
    except FileNotFoundError:
        pass

load_config_env()
YAUTH = os.environ.get("YAUTH", "")

ABILITY = ("%257B%2522CITY_CODE%2522%253A%2522416%2522%252C%2522COUNTY_CODE%2522%253A%25221606%2522%252C"
           "%2522VILLAGE_CODE%2522%253A%2522%2522%252C%2522abilities%2522%253A%255B%25224K-1%2522%255D%252C"
           "%2522businessGroupIds%2522%253A%255B%255D%252C%2522deviceGroupIds%2522%253A%255B%25226%2522%255D%252C"
           "%2522districtCode%2522%253A%2522210700%2522%252C%2522labelIds%2522%253A%255B%25222113%2522%252C%25222135%2522%252C%25222146%2522%252C%25222134%2522%252C%2522217%2522%252C%25222153%2522%255D%252C"
           "%2522ucsUserAbilityRefresh%2522%253A%25221717397127057%2522%252C%2522userGroupIds%2522%253A%255B%255D%252C"
           "%2522userLabelIds%2522%253A%255B%25222113%2522%252C%25222135%2522%252C%25222146%2522%252C%25222134%2522%252C%2522217%2522%252C%25222153%2522%255D%257D")
HEADERS = {
    "uid": "21200107031163",
    "YAUTH": os.environ.get("YAUTH", ""),
    "Host": "iptv-cosv3.lnitv.com:8084",
    "User-Agent": "okhttp/3.12.0",
}

def log(msg):
    print("[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg), flush=True)

def fetch_epg(ch):
    url = ("http://iptv-cosv3.lnitv.com:8084/ysten-epg/epg/findPlaybills.shtml"
           "?days=%d&uuid=%s&abilityString=%s" % (DAYS, ch["uuid"], ABILITY))
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        progs = []
        for day in data.get("content", []):
            for p in day.get("programs", []):
                if p.get("programName") and p.get("startTime") and p.get("endTime"):
                    progs.append((p["programName"], p["startTime"], p["endTime"]))
        return (ch["channelName"], ch["uuid"], progs)
    except Exception as e:
        return (ch["channelName"], ch["uuid"], None)

def main():
    if not YAUTH:
        log("错误: YAUTH 环境变量未设置")
        sys.exit(1)
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        channels = json.load(f)
    log("开始更新EPG: %d频道 x %d天" % (len(channels), DAYS))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_epg, ch) for ch in channels]
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())
    ok = [r for r in results if r[2] is not None]
    fail = [r for r in results if r[2] is None]
    log("EPG拉取: 成功%d 失败%d" % (len(ok), len(fail)))
    def fmt(ts):
        return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y%m%d%H%M%S") + " +0000"
    prog_count = 0
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write('<tv source-info-url="http://www.辽宁移动IPTV.com" source-info-name="辽宁移动IPTV">\n')
        for name, uuid, progs in ok:
            f.write('  <channel id="%s">\n' % uuid)
            f.write('    <display-name lang="zh">%s</display-name>\n' % name)
            f.write('  </channel>\n')
        for name, uuid, progs in ok:
            for pname, start, end in progs:
                f.write('  <programme start="%s" stop="%s" channel="%s">\n' % (fmt(start), fmt(end), uuid))
                f.write('    <title lang="zh">%s</title>\n' % pname)
                f.write('  </programme>\n')
                prog_count += 1
        f.write('</tv>\n')
    log("EPG写入完成: %s, %d节目" % (OUT_FILE, prog_count))

if __name__ == "__main__":
    main()
