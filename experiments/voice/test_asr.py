"""讯飞「语音听写(流式版)」(iat)最小验证脚本 —— 用免费额度跑通转写。

为什么用语音听写而不是实时语音转写:
  实时语音转写标准版没有免费额度(最低 198元/40h);语音听写有免费额度(500),
  且单段 ~60 秒以内,足够验证。生产环境再换成实时语音转写。

用法:
    python test_asr.py 你的录音.wav

要求音频是 16k 采样率 / 16bit / 单声道 的 wav。不是的话先转(转格式我来帮你跑):
    ffmpeg -i 原始文件 -ar 16000 -ac 1 -sample_fmt s16 已转.wav

脚本把音频按 40ms/帧 推给讯飞,实时打印累积的转写文字,最后一帧标 [final]。
"""
import base64
import hashlib
import hmac
import json
import sys
import threading
import time
import wave
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websocket  # pip install websocket-client

import creds

HOST = "ws-api.xfyun.cn"
PATH = "/v2/iat"
GATE = f"wss://{HOST}{PATH}"
FRAME_BYTES = 1280     # 40ms 的 16k/16bit/单声道音频 = 1280 字节
FRAME_INTERVAL = 0.04  # 每 40ms 发一帧

# 发送状态:0=第一帧 1=中间帧 2=最后一帧
STATUS_FIRST, STATUS_CONTINUE, STATUS_LAST = 0, 1, 2


def build_url() -> str:
    """按讯飞 iat 的 RFC 时间 + HMAC-SHA256 规则生成带鉴权的连接地址。"""
    date = format_date_time(mktime(datetime.now().timetuple()))
    signature_origin = f"host: {HOST}\ndate: {date}\nGET {PATH} HTTP/1.1"
    signature_sha = hmac.new(
        creds.API_SECRET.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        f'api_key="{creds.API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    params = {"authorization": authorization, "date": date, "host": HOST}
    return GATE + "?" + urlencode(params)


def parse_result(result: dict) -> str:
    """从 iat 返回的 result 里抠出这一段的文字。"""
    text = ""
    for seg in result["ws"]:
        for cw in seg["cw"]:
            text += cw["w"]
    return text


def read_pcm_frames(wav_path: str):
    """读 wav,校验格式,切成 1280 字节的帧。"""
    wf = wave.open(wav_path, "rb")
    ch, width, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
    if (ch, width, rate) != (1, 2, 16000):
        print(
            f"⚠️  音频格式是 声道={ch} 位深={width*8}bit 采样率={rate},"
            f"需要 单声道/16bit/16000。把文件给我,我帮你转。"
        )
        sys.exit(1)
    pcm = wf.readframes(wf.getnframes())
    wf.close()
    for i in range(0, len(pcm), FRAME_BYTES):
        yield pcm[i : i + FRAME_BYTES]


def main(wav_path: str) -> None:
    print(f"连接讯飞语音听写… {GATE}")
    ws = websocket.create_connection(build_url())
    print("✅ 连上了,开始喂音频\n")

    done = threading.Event()
    full_text = []  # 累积所有片段

    def receive() -> None:
        while not done.is_set():
            try:
                msg = ws.recv()
            except Exception:
                break
            if not msg:
                continue
            payload = json.loads(msg)
            if payload.get("code") != 0:
                print(f"❌ 讯飞报错:code={payload.get('code')} {payload.get('message')}")
                done.set()
                return
            data = payload.get("data") or {}
            if "result" in data:
                full_text.append(parse_result(data["result"]))
                print(f"[转写中] {''.join(full_text)}")
            if data.get("status") == STATUS_LAST:
                print(f"\n[final] {''.join(full_text)}")
                done.set()
                return

    recv_thread = threading.Thread(target=receive, daemon=True)
    recv_thread.start()

    business = {"language": "zh_cn", "domain": "iat", "accent": "mandarin", "vad_eos": 10000}
    audio_fmt = {"format": "audio/L16;rate=16000", "encoding": "raw"}

    frames = list(read_pcm_frames(wav_path))
    for idx, frame in enumerate(frames):
        status = STATUS_FIRST if idx == 0 else STATUS_CONTINUE
        frame_msg = {"data": {**audio_fmt, "status": status, "audio": base64.b64encode(frame).decode()}}
        if idx == 0:
            frame_msg["common"] = {"app_id": creds.APPID}
            frame_msg["business"] = business
        ws.send(json.dumps(frame_msg))
        time.sleep(FRAME_INTERVAL)

    # 最后一帧:告诉讯飞音频发完了
    ws.send(json.dumps({"data": {**audio_fmt, "status": STATUS_LAST, "audio": ""}}))

    done.wait(timeout=10)
    ws.close()
    print("\n— 转写结束 —")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:python test_asr.py 你的录音.wav")
        sys.exit(1)
    main(sys.argv[1])
