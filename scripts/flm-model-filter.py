#!/usr/bin/env python3
"""flm-model-filter — proxy filter transparan di depan FastFlowLM (FLM).

Masalah: `flm serve` AUTO-DOWNLOAD model apa pun yang diminta (mis. Open WebUI
salah pilih deepseek -> FLM menarik 5GB). FLM tak punya opsi mematikannya.

Solusi: proxy ini menempati port FLM lama (mis. 52625) dan meneruskan ke FLM
yang dipindah ke port lokal (mis. 52624). Hanya model di ALLOWLIST yang lolos:
  - GET /v1/models        -> daftar difilter ke ALLOWLIST saja
  - POST .../completions  -> kalau "model" bukan di ALLOWLIST -> 403 (TIDAK
                             diteruskan, jadi FLM tak pernah men-download)
  - selain itu            -> diteruskan apa adanya (streaming SSE aman)

Konfigurasi via env:
  FLM_ALLOWED_MODELS  (default "gemma4-it:e4b,qwen3.5:2b")
  FLM_UPSTREAM_PORT   (default 52624)  -> port FLM sebenarnya (localhost)
  FLM_PROXY_PORT      (default 52625)  -> port yang didengarkan proxy
  FLM_PROXY_HOST      (default 0.0.0.0)
"""
import http.client
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = {m.strip() for m in os.environ.get(
    "FLM_ALLOWED_MODELS", "gemma4-it:e4b,qwen3.5:2b").split(",") if m.strip()}
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = int(os.environ.get("FLM_UPSTREAM_PORT", "52624"))
LISTEN_HOST = os.environ.get("FLM_PROXY_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("FLM_PROXY_PORT", "52625"))

HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer",
       "proxy-authorization", "proxy-authenticate", "upgrade", "content-length"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _fwd_headers(self):
        h = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        h["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
        return h

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, Authorization, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p.endswith("/models"):
            return self._filtered_models()
        return self._relay("GET", None)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if n else b""
        p = self.path.split("?")[0]
        if "completions" in p or "/embeddings" in p:
            try:
                model = json.loads(body or b"{}").get("model")
            except Exception:
                model = None
            if model is not None and model not in ALLOWED:
                return self._deny(model)
        return self._relay("POST", body)

    def _send_json(self, status, obj):
        out = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self._cors()
        self.end_headers()
        self.wfile.write(out)

    def _deny(self, model):
        self._send_json(403, {"error": {
            "message": (f"Model '{model}' diblokir oleh flm-model-filter. "
                        f"Hanya {sorted(ALLOWED)} yang diizinkan; tidak di-download."),
            "type": "model_not_allowed", "code": "model_not_allowed"}})

    def _filtered_models(self):
        try:
            c = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=30)
            c.request("GET", self.path, headers=self._fwd_headers())
            r = c.getresponse()
            data = r.read()
            c.close()
            obj = json.loads(data)
            if isinstance(obj, dict) and isinstance(obj.get("data"), list):
                obj["data"] = [m for m in obj["data"] if m.get("id") in ALLOWED]
            self._send_json(200, obj)
        except Exception as e:
            self._send_json(502, {"error": {"message": f"upstream: {e}"}})

    def _relay(self, method, body):
        try:
            c = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=600)
            c.request(method, self.path, body=body, headers=self._fwd_headers())
            r = c.getresponse()
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() in HOP:
                    continue
                self.send_header(k, v)
            self._cors()
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                buf = r.read(4096)
                if not buf:
                    break
                self.wfile.write(b"%X\r\n%s\r\n" % (len(buf), buf))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            c.close()
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                self._send_json(502, {"error": {"message": f"upstream: {e}"}})
            except Exception:
                pass


if __name__ == "__main__":
    print(f"flm-model-filter: listen {LISTEN_HOST}:{LISTEN_PORT} -> "
          f"FLM 127.0.0.1:{UPSTREAM_PORT}  allow={sorted(ALLOWED)}", flush=True)
    ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler).serve_forever()
