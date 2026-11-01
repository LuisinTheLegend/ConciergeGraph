"""scratch/evidencia_4_2h/tripwire_proxy.py

Servidor HTTP proxy local (tripwire) para o Passo 6 da Rodada 4.2h:
- Registra cada CONNECT / requisição HTTP (timestamp ISO, método e host:porta/path;
  NUNCA registra headers nem credenciais).
- Responde sempre 403 Forbidden (bloqueando qualquer tráfego externo real).
- Pode ser usado como biblioteca (TripwireProxyServer) ou via linha de comando.
"""

from __future__ import annotations

import argparse
import datetime
import http.server
import json
import threading
from pathlib import Path
from typing import Any, Optional


class TripwireProxyServer:
    """Gerencia uma instância em thread de proxy HTTP local que responde 403."""

    def __init__(self, log_file: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self.events: list[dict[str, Any]] = []
        self._log_file = log_file
        parent = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _record_and_reject(self) -> None:
                ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
                entry = {
                    "timestamp": ts,
                    "method": self.command,
                    "target": self.path,
                }
                with parent._lock:
                    parent.events.append(entry)
                    if parent._log_file is not None:
                        with parent._log_file.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                content_len = int(self.headers.get("Content-Length", 0) or 0)
                if content_len > 0:
                    try:
                        self.rfile.read(content_len)
                    except Exception:
                        pass

                body = b'{"error": "Blocked by tripwire proxy (403)"}'
                self.close_connection = True
                try:
                    self.send_response(403, "Forbidden by Tripwire Proxy")
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    pass

            def do_CONNECT(self) -> None:
                self._record_and_reject()

            def do_GET(self) -> None:
                self._record_and_reject()

            def do_POST(self) -> None:
                self._record_and_reject()

            def do_PUT(self) -> None:
                self._record_and_reject()

            def do_DELETE(self) -> None:
                self._record_and_reject()

            def do_HEAD(self) -> None:
                self._record_and_reject()

            def log_message(self, format: str, *args: Any) -> None:
                # Silencia log padrão no stderr para não poluir logs do teste
                pass

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port: int = self._server.server_address[1]
        self.proxy_url: str = f"http://127.0.0.1:{self.port}"
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "TripwireProxyServer":
        if self._log_file is not None:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:
            pass
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def clear_events(self) -> None:
        with self._lock:
            self.events.clear()

    def snapshot_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.events)

    def __enter__(self) -> "TripwireProxyServer":
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.stop()
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Tripwire HTTP Proxy (responde 403 e registra CONNECT/requests)")
    parser.add_argument("--log-file", required=True, help="Caminho do arquivo JSONL de eventos")
    args = parser.parse_args()

    proxy = TripwireProxyServer(log_file=Path(args.log_file)).start()
    print(f"TRIPWIRE_PROXY_URL={proxy.proxy_url}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        proxy.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

