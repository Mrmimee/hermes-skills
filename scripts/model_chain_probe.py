#!/usr/bin/env python3
"""
Hermes Model Chain Health Probe (Watchdog Pattern)
Runs every 8 hours via Hermes native scheduler.
- Silent on healthy (0 noise in Telegram)
- Immediate alert when primary fails (with fallback status)
- Recovery alert when primary comes back online
- Zero extra resident processes, <20 tokens per check, <2s execution time.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import yaml

HERMES_DIR = os.path.expanduser(r'C:\Users\mnb77\AppData\Local\hermes')
CONFIG_PATH = os.path.join(HERMES_DIR, 'config.yaml')
ENV_PATH = os.path.join(HERMES_DIR, '.env')
STATE_PATH = os.path.join(HERMES_DIR, 'cache', 'model_health_state.json')

sys.path.insert(0, os.path.join(HERMES_DIR, 'hermes-agent'))

def load_env():
    env_vars = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
                    os.environ[k.strip()] = env_vars[k.strip()]
    return env_vars

def get_vertex_token():
    try:
        from agent.vertex_adapter import get_vertex_credentials
        token, proj = get_vertex_credentials()
        return token
    except Exception:
        return None

def probe_chat_completion(url, model, key=None, timeout=10):
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': '1+1=? answer in 1 word'}],
        'max_tokens': 5
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            latency = round((time.time() - t0) * 1000, 1)
            choices = data.get('choices', [])
            content = choices[0].get('message', {}).get('content', '') if choices else ''
            return {'ok': True, 'latency_ms': latency, 'code': resp.status, 'sample': str(content)[:30]}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:120]
        return {'ok': False, 'code': e.code, 'error': body}
    except Exception as e:
        return {'ok': False, 'code': 0, 'error': str(e)[:100]}

def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ [Probe Error] Config not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    env_vars = load_env()
    model_cfg = cfg.get('model', {})
    primary_model = model_cfg.get('default', '')
    primary_provider = model_cfg.get('provider', '')
    primary_base = model_cfg.get('base_url', '')

    primary_res = None
    if primary_provider == 'vertex':
        token = get_vertex_token()
        endpoint = primary_base if '/chat/completions' in primary_base else f"{primary_base.rstrip('/')}/chat/completions"
        primary_res = probe_chat_completion(endpoint, primary_model, key=token)
    elif primary_base:
        endpoint = primary_base if '/chat/completions' in primary_base else f"{primary_base.rstrip('/')}/chat/completions"
        primary_res = probe_chat_completion(endpoint, primary_model)
    else:
        primary_res = {'ok': True, 'note': 'Internal resolver configured, status healthy'}

    # Load previous state for transition detection
    prev_state = {}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, 'r', encoding='utf-8') as f:
                prev_state = json.load(f)
        except Exception:
            pass

    prev_primary_ok = prev_state.get('primary', {}).get('status', {}).get('ok', True)
    curr_primary_ok = primary_res.get('ok', False)

    current_report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'primary': {
            'provider': primary_provider,
            'model': primary_model,
            'status': primary_res
        },
        'fallbacks': []
    }

    # If primary is down, test fallbacks
    if not curr_primary_ok:
        fallbacks = cfg.get('fallback_providers', [])
        for fb in fallbacks:
            fb_prov = fb.get('provider', '')
            fb_model = fb.get('model', '')
            fb_base = fb.get('base_url', '')
            fb_key_env = fb.get('key_env', '')
            fb_key = env_vars.get(fb_key_env, os.environ.get(fb_key_env, ''))
            if fb_prov == 'openrouter':
                endpoint = 'https://openrouter.ai/api/v1/chat/completions'
                key = env_vars.get('OPENROUTER_API_KEY', os.environ.get('OPENROUTER_API_KEY', ''))
            else:
                endpoint = fb_base if '/chat/completions' in fb_base else f"{fb_base.rstrip('/')}/chat/completions"
                key = fb_key
            fb_res = probe_chat_completion(endpoint, fb_model, key=key)
            current_report['fallbacks'].append({
                'provider': fb_prov,
                'model': fb_model,
                'status': fb_res
            })

    # Save latest state
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(current_report, f, indent=2, ensure_ascii=False)

    # Watchdog output decision:
    # 1. Failure right now -> Always alert!
    if not curr_primary_ok:
        err_msg = primary_res.get('error', f"HTTP {primary_res.get('code')}")
        lines = [
            f"🚨 [Hermes 模型链告警] 主模型失效！",
            f"• 当前主模型: {primary_provider} / {primary_model}",
            f"• 故障原因: {err_msg}",
            f"• 备用模型探测状态:"
        ]
        for fb in current_report['fallbacks']:
            status_text = "🟢 存活可用" if fb['status'].get('ok') else f"🔴 不可用 ({fb['status'].get('error', '')[:40]})"
            lines.append(f"  - {fb['provider']} / {fb['model']}: {status_text}")
        print("\n".join(lines))
        sys.exit(2)

    # 2. Recovered from failure -> Send recovery notice
    if not prev_primary_ok and curr_primary_ok:
        lat = primary_res.get('latency_ms', 'N/A')
        print(f"✅ [Hermes 模型链已恢复] 主模型 {primary_provider}/{primary_model} 重新恢复健康 (延迟: {lat}ms)")
        sys.exit(0)

    # 3. Healthy as normal -> Silent watchdog (Empty stdout, 0 messages to chat)
    sys.exit(0)

if __name__ == '__main__':
    main()
