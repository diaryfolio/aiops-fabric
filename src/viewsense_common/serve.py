from __future__ import annotations

import importlib
import os
import ssl

import uvicorn

from viewsense_common.logging import LOGGING_CONFIG, RequestLogMiddleware
from viewsense_common.settings import required


def main() -> None:
    app_module = required("VS_APP_MODULE")
    module = importlib.import_module(app_module)
    app = module.app
    app.add_middleware(RequestLogMiddleware)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("VS_PORT", "8443")),
        server_header=False,
        ssl_keyfile=required("VS_TLS_KEY_FILE"),
        ssl_certfile=required("VS_TLS_CERT_FILE"),
        ssl_ca_certs=required("VS_TLS_CA_FILE"),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        access_log=False,
        log_config=LOGGING_CONFIG,
    )


if __name__ == "__main__":
    main()
