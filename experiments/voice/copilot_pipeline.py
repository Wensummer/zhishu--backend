"""Copilot「大脑」管线 —— 把转写 + 意图 + 触发判断串成一条流。

语音(wav)→ 讯飞实时转写 → DeepSeek 意图识别 → 决定是否触发推荐/话术。
这是后端 /ws/copilot 真管线的核心逻辑,先用 wav 在命令行跑通,再包进 WebSocket。

用法:
    python copilot_pipeline.py test16k.wav
"""
import json
import sys
import threading

import websocket

from test_asr import build_url, parse_result, read_pcm_frames, FRAME_INTERVAL, STATUS_LAST
from test_intent import classify

# 哪些意图该触发"弹屏"(对齐后端 copilot_svc.py 的 r-1/r-2/s-3 逻辑)
TRIGGER_MAP = {
    "价格异议": "💡 推荐:包年锁价续约(r-1) + 话术:应对比价异议(s-3)",
    "成本敏感": "💡 推荐:包年锁价续约(r-1),给预算确定性",
    "新需求": "💡 推荐:加推质检 Agent 增值包(r-2)",
    "质量顾虑": "💡 话术:合规直连 + SLA + 证据链可核验",
    "成交信号": "✅ 提示销售:确认续约、发送方案、推进签约",
}


def transcribe(wav_path: str) -> str:
    """流式转写整段音频,返回最终文字(实时打印转写过程)。"""
    ws = websocket.create_connection(build_url())
    pieces, done = [], threading.Event()

    def receive():
        while not done.is_set():
            try:
                msg = ws.recv()
            except Exception:
                break
            if not msg:
                continue
            payload = json.loads(msg)
            if payload.get("code") != 0:
                done.set()
                return
            data = payload.get("data") or {}
            if "result" in data:
                pieces.append(parse_result(data["result"]))
                print(f"   [转写中] {''.join(pieces)}")
            if data.get("status") == STATUS_LAST:
                done.set()
                return

    threading.Thread(target=receive, daemon=True).start()

    import base64, json as _json, time
    audio_fmt = {"format": "audio/L16;rate=16000", "encoding": "raw"}
    business = {"language": "zh_cn", "domain": "iat", "accent": "mandarin", "vad_eos": 10000}
    for idx, frame in enumerate(read_pcm_frames(wav_path)):
        m = {"data": {**audio_fmt, "status": 0 if idx == 0 else 1, "audio": base64.b64encode(frame).decode()}}
        if idx == 0:
            m["common"] = {"app_id": __import__("creds").APPID}
            m["business"] = business
        ws.send(_json.dumps(m))
        time.sleep(FRAME_INTERVAL)
    ws.send(_json.dumps({"data": {**audio_fmt, "status": STATUS_LAST, "audio": ""}}))
    done.wait(timeout=10)
    ws.close()
    return "".join(pieces)


def run(wav_path: str) -> None:
    print("🎙️  开始实时转写……")
    text = transcribe(wav_path)
    if not text:
        print("❌ 没转出文字,检查音频/密钥")
        return
    print(f"\n📝 客户说:{text}")

    print("\n🧠 意图识别中……")
    raw = classify(text)
    print(f"   意图:{raw}")

    try:
        intent = json.loads(raw)
    except json.JSONDecodeError:
        print("   (意图返回不是合法 JSON,真管线里要加容错重试)")
        return

    need = intent.get("needType", "")
    print(f"\n🎯 商机:{intent.get('level')} · {need}  (把握 {intent.get('confidence')})")
    print(f"   提示销售:{intent.get('note')}")
    trigger = TRIGGER_MAP.get(need)
    print(f"\n{trigger}" if trigger else "\n(无明显意图,不弹屏)")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "test16k.wav")
