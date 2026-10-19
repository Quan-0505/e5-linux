#!/usr/bin/python3
"""Narrow HTTPS-only bridge for the E5 screen's one-time DAED pairing."""
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.request


def reply(status, payload):
    print(f"Status: {status}")
    print("Content-Type: application/json; charset=utf-8")
    print("Cache-Control: no-store")
    print("X-Content-Type-Options: nosniff")
    print("Referrer-Policy: no-referrer\n")
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def private_client():
    try:
        addr = ipaddress.ip_address(os.environ.get("REMOTE_ADDR", ""))
        return addr.version == 4 and addr.is_private and not addr.is_loopback
    except ValueError:
        return False


def main():
    if os.environ.get("REQUEST_METHOD") != "POST":
        reply("405 Method Not Allowed", {"ok": False, "error": "仅支持登录提交。"})
        return
    if os.environ.get("HTTPS", "").lower() not in ("on", "1") and os.environ.get("REQUEST_SCHEME", "").lower() != "https":
        reply("403 Forbidden", {"ok": False, "error": "请使用设备 HTTPS 地址扫码登录。"})
        return
    host = os.environ.get("HTTP_HOST", "").split(":", 1)[0].strip("[]").lower()
    origin = os.environ.get("HTTP_ORIGIN", "")
    if not host or origin != "https://" + host:
        reply("403 Forbidden", {"ok": False, "error": "登录来源校验失败。"})
        return
    if not private_client():
        reply("403 Forbidden", {"ok": False, "error": "仅允许从设备局域网登录。"})
        return
    try:
        length = int(os.environ.get("CONTENT_LENGTH", "0"))
        if length < 1 or length > 4096:
            raise ValueError
        payload = json.loads(sys.stdin.buffer.read(length))
        if not isinstance(payload, dict) or set(payload) != {"code", "username", "password"}:
            raise ValueError
        if not isinstance(payload["code"], str) or len(payload["code"]) != 48 or any(c not in "0123456789abcdef" for c in payload["code"]):
            raise ValueError
        if not isinstance(payload["username"], str) or not 1 <= len(payload["username"]) <= 128:
            raise ValueError
        if not isinstance(payload["password"], str) or not 1 <= len(payload["password"]) <= 256:
            raise ValueError
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        reply("400 Bad Request", {"ok": False, "error": "提交内容无效。"})
        return
    request = urllib.request.Request(
        "http://127.0.0.1:8088/api/plugins/daed/pair-login",
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read(8192))
            if not isinstance(data, dict) or data.get("ok") is not True:
                reply("502 Bad Gateway", {"ok": False, "error": "DAED 登录未成功，请检查账号后重试。"})
                return
            reply("200 OK", {"ok": True})
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read(8192))
            message = body.get("error") if isinstance(body, dict) else None
        except Exception:
            message = None
        safe = message if isinstance(message, str) and len(message) < 180 else "DAED 登录未成功，请重试。"
        reply(f"{exc.code} {exc.reason}", {"ok": False, "error": safe})
    except Exception:
        reply("502 Bad Gateway", {"ok": False, "error": "无法连接 DAED 服务，请稍后重试。"})


if __name__ == "__main__":
    main()
