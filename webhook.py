"""Smallest webhook: receive → validate → transform → log. No database."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

REQUIRED_FIELDS = ("name", "email", "company")
HOST = "127.0.0.1"
PORT = 8000


def validate(payload: dict) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None or not str(value).strip():
            missing.append(field)
    return missing


def transform(payload: dict) -> dict:
    return {
        "full_name": str(payload["name"]).strip(),
        "email_address": str(payload["email"]).strip(),
        "organization": str(payload["company"]).strip(),
    }


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.rstrip("/") != "/webhook":
            self._json(404, {"error": "Not found. POST to /webhook"})
            return

        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            print("Rejected: invalid JSON", flush=True)
            self._json(400, {"error": "Invalid JSON"})
            return

        if not isinstance(payload, dict):
            print("Rejected: payload must be a JSON object", flush=True)
            self._json(400, {"error": "Payload must be a JSON object"})
            return

        missing = validate(payload)
        if missing:
            print(f"Validation failed. Missing or empty: {missing}", flush=True)
            print("Stopped here — will not transform or forward.", flush=True)
            self._json(400, {
                "error": "Validation failed",
                "missing": missing,
            })
            return

        result = transform(payload)
        print("Transformed payload:", flush=True)
        print(json.dumps(result, indent=4), flush=True)
        self._json(200, {"status": "ok", "data": result})

    def _json(self, status: int, body: dict):
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        print(f"[http] {args[0]}", flush=True)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), WebhookHandler)
    print(f"Webhook listening on http://{HOST}:{PORT}/webhook", flush=True)
    print("POST JSON. Required fields: name, email, company", flush=True)
    server.serve_forever()
