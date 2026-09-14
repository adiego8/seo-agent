"""
Offline end-to-end test: discover -> plan -> fetch, against a throwaway site served
from a background thread on localhost. No external network, no API, no cost.

Run: python3 scripts/tests/test_pipeline.py
"""
import os, sys, json, threading, http.server, socketserver, functools, tempfile, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fetch_pages as fp

PRICING = """<!doctype html><html lang="en"><head><title>Pricing — Acme</title>
<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>
<header><nav><a href="/">Home</a><a href="/contact">Contact</a></nav></header>
<main><h1>Plans that scale with your trade</h1>
<p>From £49 a month. Cancel any time. 30 day money-back guarantee.</p>
<a href="/contact" class="btn">Get a quote</a><a href="/">Learn more</a></main></body></html>"""

CONTACT = """<!doctype html><html lang="en"><head><title>Contact — Acme</title></head><body>
<main><h1>Request a quote</h1>
<form action="/lead" method="post">
<input type="text" name="name" required><input type="email" name="email" required>
<input type="submit" value="Submit"></form></main></body></html>"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{base}/</loc></url><url><loc>{base}/pricing</loc></url>
<url><loc>{base}/contact</loc></url><url><loc>{base}/blog/post-one</loc></url>
</urlset>"""

def build_site(root):
    shutil.copy(os.path.join(HERE, "fixture_landing.html"),
                os.path.join(root, "index.html"))
    for name, body in (("pricing", PRICING), ("contact", CONTACT)):
        os.makedirs(os.path.join(root, name), exist_ok=True)
        with open(os.path.join(root, name, "index.html"), "w", encoding="utf-8") as f:
            f.write(body)
    with open(os.path.join(root, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

# A client-rendered shell, as served by a Vite/React build: no text, no links.
SPA_SHELL = """<!doctype html><html lang="en"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Online Tax Filing | Example</title>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>
<script>window.dataLayer = window.dataLayer || [];</script>
<script type="application/ld+json">{"@type": "FinancialService", "name": "Example"}</script>
<script type="module" crossorigin src="/assets/index-abc123.js"></script>
</head><body><div id="root"></div></body></html>"""

# What a browser hands back after running the shell's JavaScript (served by the fake Chrome).
RENDERED = """<!doctype html><html lang="en"><head><title>Rendered</title></head><body>
<main><h1>Rendered by fake Chrome</h1><a class="btn" href="/pricing">See pricing</a></main>
</body></html>"""

# A real JS app for the real-Chrome test: the H1 and link exist only after the script runs.
JS_APP = """<!doctype html><html lang="en"><head><title>JS app</title></head><body>
<div id="root"></div>
<script>document.getElementById('root').innerHTML =
  '<main><h1>Built by JavaScript</h1><a href="/pricing">See pricing</a></main>';</script>
</body></html>"""

WP_FATAL = """<!DOCTYPE html><html><head><title>WordPress &rsaquo; Error</title></head>
<body><p>There has been a critical error on this website.</p></body></html>"""

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

class Broken(http.server.BaseHTTPRequestHandler):
    """Every path is a 500 with an HTML body -- a WordPress fatal behind a CDN."""
    def do_GET(self):
        body = WP_FATAL.encode("utf-8")
        self.send_response(500)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

def serve(root, handler_cls=None):
    handler = handler_cls or functools.partial(Quiet, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port

def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + detail))
    return bool(cond)

def main():
    root = tempfile.mkdtemp(prefix="cro-pipeline-")
    try:
        build_site(root)
        httpd, port = serve(root)
        base = "http://127.0.0.1:%d" % port
        for p in ("robots.txt", "sitemap.xml"):
            path = os.path.join(root, p)
            content = (open(path, encoding="utf-8").read().format(base=base)
                       if p == "robots.txt" else SITEMAP.format(base=base))
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        results = []

        print("discover")
        d = fp.discover(base)
        urls = {c["url"]: c for c in d["candidates"]}
        roles = {c["url"]: c["role"] for c in d["candidates"]}
        results.append(check("homepage fetched", d["fetched"][0]["status"] == 200,
                             str(d["fetched"][0])))
        results.append(check("robots.txt read", any(f["url"] == "/robots.txt" and f["status"] == 200
                                                    for f in d["fetched"])))
        results.append(check("sitemap URLs merged in",
                             base + "/blog/post-one" in urls,
                             str(sorted(urls))))
        results.append(check("pricing classified as offer",
                             roles.get(base + "/pricing") == "offer", str(roles)))
        results.append(check("contact classified as conversion",
                             roles.get(base + "/contact") == "conversion", str(roles)))
        results.append(check("home classified as entry",
                             roles.get(base) == "entry", str(roles)))
        results.append(check("blog classified as content",
                             roles.get(base + "/blog/post-one") == "content", str(roles)))
        results.append(check("candidates sorted funnel-first",
                             d["candidates"][0]["role"] == "entry",
                             d["candidates"][0]["role"]))
        results.append(check("only three documents fetched", len(d["fetched"]) == 3,
                             str([f["url"] for f in d["fetched"]])))
        results.append(check("healthy homepage is not flagged as client-rendered",
                             d["homepage"]["render_risk"] is False, str(d["homepage"])))

        print("fetch")
        plan = {"site": base, "delay_seconds": 0, "pages": [
            {"url": base + "/", "role": "entry", "label": "Home"},
            {"url": base + "/pricing", "role": "offer", "label": "Pricing"},
            {"url": base + "/contact", "role": "conversion", "label": "Contact"},
            {"url": base + "/does-not-exist", "role": "other", "label": "Missing"},
        ]}
        out = fp.run_fetch(plan)
        by_role = {p["role"]: p for p in out["pages"]}

        results.append(check("all four attempted", out["page_count"] == 4, str(out["page_count"])))
        results.append(check("three succeeded", out["ok_count"] == 3, str(out["ok_count"])))
        results.append(check("404 recorded as an error", len(out["errors"]) == 1,
                             str(out["errors"])))
        results.append(check("404 page still present in output",
                             any(p.get("error") for p in out["pages"])))
        results.append(check("no page falsely at render risk",
                             out["render_risk_count"] == 0, str(out["render_risk_count"])))
        results.append(check("offer page H1 extracted",
                             by_role["offer"]["structure"]["h1"] == ["Plans that scale with your trade"],
                             str(by_role["offer"]["structure"]["h1"])))
        results.append(check("offer page risk reversal found",
                             by_role["offer"]["trust"]["risk_reversal"] >= 2,
                             str(by_role["offer"]["trust"])))
        results.append(check("conversion page lead form found",
                             by_role["conversion"]["form_summary"]["lead_forms"] == 1,
                             str(by_role["conversion"]["form_summary"])))
        results.append(check("weak submit copy captured",
                             by_role["conversion"]["forms"][0]["submit_text"] == "Submit"))
        results.append(check("missing viewport detected on conversion page",
                             by_role["conversion"]["head"]["has_viewport"] is False))
        results.append(check("relative CTA href resolved to absolute",
                             any(c["href"] == base + "/contact"
                                 for c in by_role["offer"]["ctas"]["items"] if c["href"]),
                             str([c["href"] for c in by_role["offer"]["ctas"]["items"]])))
        results.append(check("generic CTA flagged on offer page",
                             by_role["offer"]["ctas"]["generic_count"] >= 1,
                             str([c["text"] for c in by_role["offer"]["ctas"]["items"]])))
        results.append(check("fetched_at stamped", bool(out["fetched_at"])))

        print("json round-trip")
        s = json.dumps(out, ensure_ascii=False)
        results.append(check("output is JSON-serialisable", len(s) > 1000))
        results.append(check("round-trips cleanly",
                             json.loads(s)["page_count"] == 4))

        httpd.shutdown()

        print("discover: site down")
        down, down_port = serve(root, Broken)
        dd = fp.discover("http://127.0.0.1:%d" % down_port)
        down.shutdown()
        results.append(check("500 homepage yields no candidates", dd["candidates"] == [],
                             str(dd["candidates"])))
        results.append(check("500 homepage stops before robots and sitemap",
                             len(dd["fetched"]) == 1, str(dd["fetched"])))
        results.append(check("500 homepage marked failed", dd["homepage"]["failed"] is True,
                             str(dd["homepage"])))
        results.append(check("note names the status", "HTTP 500" in " ".join(dd["notes"]),
                             str(dd["notes"])))

        print("discover: client-rendered site")
        spa_root = tempfile.mkdtemp(prefix="cro-spa-", dir=root)
        with open(os.path.join(spa_root, "index.html"), "w", encoding="utf-8") as f:
            f.write(SPA_SHELL)
        spa, spa_port = serve(spa_root)
        ds = fp.discover("http://127.0.0.1:%d" % spa_port)
        spa.shutdown()
        results.append(check("shell homepage flagged as client-rendered",
                             ds["homepage"]["render_risk"] is True, str(ds["homepage"])))
        results.append(check("shell homepage is not a failure",
                             ds["homepage"]["failed"] is False, str(ds["homepage"])))
        results.append(check("client-rendered warning in notes",
                             any("client-rendered" in n for n in ds["notes"]), str(ds["notes"])))

        print("render: fake Chrome")
        spa2, spa2_port = serve(spa_root)
        spa_base = "http://127.0.0.1:%d" % spa2_port
        fake = os.path.join(root, "fake_chrome.sh")
        with open(fake, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\ncat <<'HTML'\n" + RENDERED + "\nHTML\n")
        os.chmod(fake, 0o755)
        broken = os.path.join(root, "broken_chrome.sh")
        with open(broken, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(broken, 0o755)
        old_env = os.environ.get("CHROME_PATH")
        try:
            os.environ["CHROME_PATH"] = fake
            results.append(check("CHROME_PATH is honoured", fp.find_chrome() == fake,
                                 str(fp.find_chrome())))
            rplan = {"site": spa_base, "render": True, "delay_seconds": 0,
                     "pages": [{"url": spa_base + "/", "role": "entry", "label": "Home"}]}
            ro = fp.run_fetch(rplan)
            page = ro["pages"][0]
            results.append(check("rendered DOM is what gets extracted",
                                 page.get("structure", {}).get("h1") == ["Rendered by fake Chrome"],
                                 str(page.get("structure", {}).get("h1") or page.get("error"))))
            results.append(check("page marked rendered",
                                 page.get("http", {}).get("rendered") is True, str(page.get("http"))))
            results.append(check("raw shell size kept for reference",
                                 page.get("http", {}).get("raw_html_bytes", 0) > 0,
                                 str(page.get("http"))))
            results.append(check("rendered page not at render risk",
                                 page.get("render_risk") is False))
            rd = fp.discover(spa_base, render=True)
            results.append(check("discover --render finds links in the rendered DOM",
                                 spa_base + "/pricing" in {c["url"] for c in rd["candidates"]},
                                 str([c["url"] for c in rd["candidates"]])))
            results.append(check("discover --render homepage rendered and readable",
                                 rd["homepage"]["rendered"] is True
                                 and rd["homepage"]["render_risk"] is False, str(rd["homepage"])))

            os.environ["CHROME_PATH"] = broken
            bo = fp.run_fetch(rplan)
            results.append(check("failed render is an error, not an empty-shell audit",
                                 bo["ok_count"] == 0 and bool(bo["errors"])
                                 and bo["errors"][0]["error"].startswith("render failed"),
                                 str(bo["errors"])))
            os.environ["CHROME_PATH"] = os.path.join(root, "no-such-chrome")
            results.append(check("a missing CHROME_PATH binary means no Chrome",
                                 fp.find_chrome() is None))
        finally:
            if old_env is None:
                os.environ.pop("CHROME_PATH", None)
            else:
                os.environ["CHROME_PATH"] = old_env
        spa2.shutdown()

        print("render: real Chrome")
        if not fp.find_chrome():
            print("  skip no Chrome on this machine")
        else:
            js_root = tempfile.mkdtemp(prefix="cro-js-", dir=root)
            with open(os.path.join(js_root, "index.html"), "w", encoding="utf-8") as f:
                f.write(JS_APP)
            js, js_port = serve(js_root)
            js_base = "http://127.0.0.1:%d" % js_port
            t0 = time.time()
            jd = fp.discover(js_base, render=True)
            took = time.time() - t0
            js.shutdown()
            results.append(check("real Chrome runs the page's JavaScript",
                                 jd["homepage"].get("render_risk") is False
                                 and not jd["homepage"].get("failed"),
                                 str(jd["homepage"]) + " " + str(jd["notes"])))
            results.append(check("JS-injected link discovered",
                                 js_base + "/pricing" in {c["url"] for c in jd["candidates"]},
                                 str([c["url"] for c in jd["candidates"]])))
            results.append(check("render finishes even when Chrome lingers",
                                 took < fp.RENDER_TIMEOUT - 15, "%.1fs" % took))

        passed, total = sum(1 for r in results if r), len(results)
        print("\n%d/%d checks passed" % (passed, total))
        return 0 if passed == total else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
