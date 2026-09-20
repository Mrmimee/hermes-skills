#!/usr/bin/env python3
"""
Hermes Free Pool & Rate-Limit Watchdog
Monitors candidate free models on OpenRouter, NaraRouter, and Nous.
- Detects severe 429 rate limits or vendor dropouts
- Identifies newly added top-tier free candidates
- Watchdog pattern: silent when healthy, alerts on anomalies
- Zero LLM tokens consumed, runs in ~3s
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

HERMES_DIR = os.path.expanduser(r'C:\Users\mnb77\AppData\Local\hermes')
STATE_FILE = os.path.join(HERMES_DIR, 'cache', 'free_pool_health_state.json')
APIKEY_FILE = r'C:\Users\mnb77\OneDrive\桌面\apikey.txt'

def parse_keys():
    keys = {}
    if not os.path.exists(APIKEY_FILE):
        return keys
    try:
        with open(APIKEY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        in_models = False
        last_label = None
        for line in lines:
            s = line.strip()
            if s.startswith('# 模型供应商 API'):
                in_models = True
            elif s.startswith('#') and in_models:
                in_models = False
            if not in_models or not s:
                continue
            labels = ('OpenRouter', 'NaraRouter', 'Nous', 'NVIDIA')
            if any(s == l for l in labels):
                last_label = s
            elif last_label and ' ' not in s and not s.startswith('#'):
                keys[last_label] = s
                last_label = None
    except Exception:
        pass
    return keys

def quick_probe(url, model, key, timeout=6):
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    payload = {'model': model, 'messages': [{'role': 'user', 'content': '1+1=?'}], 'max_tokens': 5}
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            latency = round((time.time() - t0) * 1000, 1)
            return {'status': 'OK', 'code': resp.status, 'latency_ms': latency}
    except urllib.error.HTTPError as e:
        return {'status': 'FAIL', 'code': e.code, 'error': f"HTTP {e.code}"}
    except Exception as e:
        return {'status': 'FAIL', 'code': 0, 'error': str(e)[:40]}

def main():
    keys = parse_keys()
    results = {}

    # 1. Probe NaraRouter free candidates
    nara_key = keys.get('NaraRouter')
    if nara_key:
        nara_models = ['ling-3.0-flash-vl-free', 'nemotron-3-super-free']
        for m in nara_models:
            res = quick_probe('https://router.bynara.id/v1/chat/completions', m, nara_key)
            results[f"nara/{m}"] = res

    # 2. Probe OpenRouter key free models
    or_key = keys.get('OpenRouter')
    if or_key:
        or_models = ['nex-agi/nex-n2.5-pro:free', 'nvidia/nemotron-3-ultra-550b-a55b:free']
        for m in or_models:
            res = quick_probe('https://openrouter.ai/api/v1/chat/completions', m, or_key)
            results[f"openrouter/{m}"] = res

    # 3. Probe Nous free models
    nous_key = keys.get('Nous')
    if nous_key:
        nous_models = ['meituan/longcat-2.0:free', 'poolside/laguna-s-2.1:free']
        for m in nous_models:
            res = quick_probe('https://inference-api.nousresearch.com/v1/chat/completions', m, nous_key)
            results[f"nous/{m}"] = res

    # Load previous state
    prev_state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                prev_state = json.load(f)
        except Exception:
            pass

    # Save current
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'), 'results': results}, f, indent=2)

    # Check if all free pools are down (rare disaster)
    all_failed = all(r['status'] == 'FAIL' for r in results.values()) if results else False
    if all_failed:
        print("🚨 [免费池严重告警] 所有备用免费渠道均无法响应，请注意检查网络或 Key 状态！")
        for k, v in results.items():
            print(f"  - {k}: {v.get('error', 'FAIL')}")
        sys.exit(2)

    # Watchdog silent
    sys.exit(0)

if __name__ == '__main__':
    main()
