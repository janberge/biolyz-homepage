#!/usr/bin/env python3
"""Dev server with SPA fallback.

The app routes on real paths now, so `python3 -m http.server` is no longer
enough: it answers /compare/point-of-care with a 404 because no such file
exists. Anything that is not a real file falls back to index.html here, which
is the same rule serve/_redirects asks the host for in production.

    python3 tools/serve.py [port] [--dir DIR]
"""
import http.server
import os
import socketserver
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "serve")
PORT = 3000
args = sys.argv[1:]
if "--dir" in args:
    i = args.index("--dir")
    ROOT = os.path.abspath(args[i + 1])
    del args[i:i + 2]
if args:
    PORT = int(args[0])


class SPA(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        # The build is regenerated constantly; a cached index.html makes an
        # edit look like it did nothing.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path):
        full = super().translate_path(path)
        if os.path.isdir(full):
            idx = os.path.join(full, "index.html")
            if os.path.exists(idx):
                return idx
        if not os.path.exists(full):
            # A route has no extension; an asset does. Falling back for BOTH
            # means a missing /assets/hero.mp4 is answered with index.html at
            # 200 and text/html, so the video silently does not play instead
            # of failing where you can see it. That is exactly how an emptied
            # scratchpad went unnoticed for two days. A route still falls
            # back; a file that is not there 404s.
            if os.path.splitext(full)[1]:
                self.send_error(404, "Not found: %s" % path)
                return None
            return os.path.join(ROOT, "index.html")   # the SPA fallback
        return full

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), SPA) as httpd:
    print(f"serving {ROOT} on http://localhost:{PORT} (SPA fallback on)")
    httpd.serve_forever()
