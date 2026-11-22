"""端到端 mock 测试：本地起一个 OpenAI 兼容 mock 服务，验证 ai.summarize 的 HTTP 链路。"""
import os
import sys
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import ai  # noqa: E402

RESPONSE = {
    "choices": [{
        "message": {
            "content": '{"title":"买牛奶","note":"去超市","important":true,"urgent":false,"due_at":null}'
        }
    }]
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        req = json.loads(body)
        assert self.path == "/v1/chat/completions"
        assert req["model"] == "test-model"
        assert self.headers.get("Authorization") == "Bearer test-key"
        assert req["messages"][0]["role"] == "system"
        assert req["messages"][1]["content"] == "帮我去超市买牛奶"
        data = json.dumps(RESPONSE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    r = ai.summarize("帮我去超市买牛奶", f"http://127.0.0.1:{port}/v1", "test-key", "test-model")
    assert r["title"] == "买牛奶"
    assert r["note"] == "去超市"
    assert r["important"] is True
    assert r["urgent"] is False
    srv.shutdown()
    print("MOCK_AI OK")


if __name__ == "__main__":
    main()
