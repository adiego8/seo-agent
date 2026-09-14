"""
CRO Funnel Report -- page fetcher & signal extractor.

Two modes:

  discover:  python fetch_pages.py discover https://example.com [--out candidates.json]
             Fetches the homepage, robots.txt and sitemap.xml, collects internal
             URLs with their anchor text, and guesses a funnel role for each.
             Produces a CANDIDATE list for a human to confirm -- it fetches
             nothing beyond those three documents.

  fetch:     python fetch_pages.py fetch plan.json [--out pages.json] [--render]
             plan.json = {"site": "...", "render": false, "pages": [{"url","role","label"}, ...]}
             Fetches each page once and extracts structured conversion signals.

  --render   For sites built in JavaScript. Each page is still fetched raw first (status,
             headers, redirects), then loaded in the local headless Chrome, and the rendered
             DOM is what gets extracted. Works on discover too. Free; needs Chrome, or
             CHROME_PATH pointing at a Chrome/Chromium binary. Off by default.

Everything here is deterministic extraction. No scoring, no judgement, no LLM,
no third-party API -- the skill's analysis step reads this output and does that.

Stdlib only, apart from certifi if it happens to be installed (for a working CA
bundle on macOS python.org builds). Without --render, JavaScript is never executed, so client-rendered pages
come back thin. That is detected and reported per page as render_risk rather
than silently producing a hollow audit.
"""

import sys, os, json, re, time, gzip, io, ssl, glob, shutil, signal, subprocess, tempfile
import urllib.request, urllib.error, urllib.parse

# python.org builds on macOS ship without a CA bundle, so every https fetch dies with
# CERTIFICATE_VERIFY_FAILED. Use certifi's bundle when it is installed and fall back to
# the system store otherwise. Verification stays ON either way -- never disable it.
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 CRO-Audit/1.0")
TIMEOUT = 20
MAX_BYTES = 4_000_000

# ── Funnel role guessing ──────────────────────────────────────────────────────

ROLE_PATTERNS = [
    ("conversion", r"/(contact|signup|sign-up|register|demo|book|booking|checkout|"
                   r"cart|apply|get-started|start|trial|quote|enquire|inquiry|order)"),
    ("offer",      r"/(pricing|prices|plans|packages|rates|cost|subscribe|shop|store|"
                   r"products?|collections?)"),
    ("proof",      r"/(case-stud|testimonial|review|customer|client|portfolio|work|"
                   r"success|result)"),
    ("value",      r"/(features?|product|service|solution|how-it-works|platform|"
                   r"what-we-do|benefits?|use-cases?)"),
    ("trust",      r"/(about|team|company|story|mission|guarantee|security|privacy|"
                   r"terms|refund|shipping|returns?)"),
    ("support",    r"/(faq|help|support|docs|documentation|knowledge)"),
    ("content",    r"/(blog|news|articles?|resources?|guides?|insights?|learn)"),
]

ANCHOR_HINTS = [
    ("conversion", r"\b(get started|start (free|now)|sign up|book|schedule|request|"
                   r"contact|buy|order|checkout|apply|try|demo|quote|call)\b"),
    ("offer",      r"\b(pricing|plans|packages|shop|store)\b"),
    ("proof",      r"\b(case stud|testimonial|review|customer|client|portfolio)\b"),
]

def guess_role(url, anchor=""):
    path = urllib.parse.urlparse(url).path.lower().rstrip("/")
    if path in ("", "/index.html", "/index.php", "/home"):
        return "entry"
    # A locale root (/en, /es, /en-us, /es-419) IS the homepage on a localised site.
    if re.fullmatch(r"/[a-z]{2}(-[a-z0-9]{2,4})?", path):
        return "entry"
    for role, pat in ROLE_PATTERNS:
        if re.search(pat, path + "/"):
            return role
    # Second pass: the keyword inside a hyphenated slug (/tax-pricing). Runs only after
    # every segment-start match has failed, so /blog/how-to-book stays content.
    for role, pat in ROLE_PATTERNS:
        if re.search(pat.replace("/(", "[-_](", 1), path + "/"):
            return role
    a = (anchor or "").lower()
    for role, pat in ANCHOR_HINTS:
        if re.search(pat, a):
            return role
    return "other"

# ── Trust / friction vocabulary ───────────────────────────────────────────────

TRUST_TERMS = {
    "social_proof":  [r"testimonial", r"review", r"rated", r"stars?\b", r"trusted by",
                      r"customers?\b", r"clients?\b", r"case stud", r"as seen (in|on)"],
    "risk_reversal": [r"money.?back", r"guarantee", r"refund", r"no risk", r"cancel any ?time",
                      r"free trial", r"no credit card", r"free returns?"],
    "security":      [r"\bssl\b", r"secure checkout", r"encrypted", r"\bgdpr\b", r"privacy policy",
                      r"\bpci\b", r"norton|mcafee|trustpilot|verisign"],
    "authority":     [r"award", r"certified", r"accredited", r"\biso ?\d", r"patent",
                      r"featured in", r"partner"],
    "urgency":       [r"limited time", r"only \d+ left", r"ends (today|soon)", r"hurry",
                      r"last chance", r"\d+ (hours?|days?) left"],
}

NUMERIC_PROOF = re.compile(
    r"(\d[\d,\.]*\s*(?:k|m|\+)?\s*(?:customers?|clients?|users?|companies|businesses|"
    r"downloads?|reviews?|projects?|countries|years?))|"
    r"(\d\.\d\s*/\s*5)|(\b\d{1,3}%\s*(?:increase|growth|more|faster|satisfaction))",
    re.I)

ANALYTICS_MARKERS = {
    "google_analytics": r"gtag\(|google-analytics\.com|googletagmanager\.com/gtag",
    "gtm":              r"googletagmanager\.com/gtm",
    "meta_pixel":       r"connect\.facebook\.net|fbq\(",
    "hotjar":           r"static\.hotjar\.com|hj\(",
    "clarity":          r"clarity\.ms",
    "linkedin":         r"snap\.licdn\.com",
    "hubspot":          r"js\.hs-scripts\.com|hs-analytics",
    "segment":          r"cdn\.segment\.com",
    "posthog":          r"posthog",
}

CHAT_MARKERS = r"intercom|drift\.com|tawk\.to|crisp\.chat|zendesk|livechat|tidio|olark"

# Third-party booking and form tools, matched against iframe and script srcs.
EMBED_MARKERS = {
    "booking": r"calendar\.google\.com/calendar/appointments|calendly\.com|acuityscheduling\.com|"
               r"squareup\.com/appointments|square\.site|(^|[/.])cal\.com/|tidycal\.com|"
               r"meetings\.hubspot\.com|youcanbook\.me|setmore\.com|zcal\.co|savvycal\.com",
    "form":    r"typeform\.com|jotform\.com|docs\.google\.com/forms|forms\.gle|"
               r"share\.hsforms\.com|js\.hsforms\.net|tally\.so|formstack\.com|cognitoforms\.com",
}

CTA_VERBS = re.compile(
    # English
    r"\b(get|start|buy|book|order|sign ?up|subscribe|try|request|contact|call|"
    r"download|claim|join|apply|schedule|demo|quote|add to (cart|bag)|checkout|"
    r"shop|reserve|register|talk to|speak)\b|"
    # Spanish -- imperative and infinitive forms
    r"(empez|empieza|comenz|comienza|cont[aá]ct|habl|solicit|reserv|agend|compr|"
    r"descarg|[uú]nete|unirse|prueba|probar|cotiz|llam|suscrib|env[ií]a|obt[eé]n|"
    r"consigue|ver planes|m[aá]s informaci[oó]n)", re.I)

GENERIC_CTA = re.compile(
    r"^(click here|learn more|read more|more|submit|send|go|here|continue|next|"
    r"see more|find out more|discover|explore)$", re.I)

# ── HTML parsing ──────────────────────────────────────────────────────────────

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}
NAV_TAGS = {"nav", "header", "footer"}

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self.meta = {}
        self.canonical = None
        self.lang = None
        self.headings = {"h1": [], "h2": [], "h3": []}
        self._heading_stack = []
        self.text_parts = []
        self.links = []          # {text, href, index, in_nav, in_form, tag}
        self.buttons = []
        self.forms = []
        self._form = None
        self._pending_label = None
        self.images = {"count": 0, "missing_alt": 0, "lazy": 0}
        self.iframes = 0
        self.iframe_srcs = []
        self.videos = 0
        self.scripts = {"total": 0, "external": 0, "head_blocking": 0,
                        "async_defer": 0, "inline_bytes": 0}
        self._in_script = False
        self._script_inline = False
        self.script_srcs = []
        self.stylesheets = 0
        self.inline_style_bytes = 0
        self._in_style = False
        self._skip_depth = 0
        self._nav_depth = 0
        self._in_head = True
        self._el_index = 0
        self._cur_text_sink = None

    # -- helpers ------------------------------------------------------------
    def _attr(self, attrs, name):
        for k, v in attrs:
            if k.lower() == name:
                return v or ""
        return None

    def _has(self, attrs, name):
        return any(k.lower() == name for k, v in attrs)

    # -- tags ---------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self._el_index += 1

        if tag == "html":
            self.lang = self._attr(attrs, "lang")
        if tag == "body":
            self._in_head = False
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        if tag in NAV_TAGS:
            self._nav_depth += 1

        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (self._attr(attrs, "name") or self._attr(attrs, "property") or "").lower()
            if name:
                self.meta[name] = self._attr(attrs, "content") or ""
        elif tag == "link":
            rel = (self._attr(attrs, "rel") or "").lower()
            if "canonical" in rel:
                self.canonical = self._attr(attrs, "href")
            if "stylesheet" in rel:
                self.stylesheets += 1
        elif tag == "script":
            self._in_script = True
            src = self._attr(attrs, "src")
            self.scripts["total"] += 1
            if src:
                self.scripts["external"] += 1
                self.script_srcs.append(src)
                if self._has(attrs, "async") or self._has(attrs, "defer"):
                    self.scripts["async_defer"] += 1
                elif self._in_head:
                    self.scripts["head_blocking"] += 1
                self._script_inline = False
            else:
                self._script_inline = True
        elif tag == "style":
            self._in_style = True
        elif tag in ("h1", "h2", "h3"):
            self._heading_stack.append((tag, []))
        elif tag == "img":
            self.images["count"] += 1
            alt = self._attr(attrs, "alt")
            if alt is None or not alt.strip():
                self.images["missing_alt"] += 1
            if (self._attr(attrs, "loading") or "").lower() == "lazy":
                self.images["lazy"] += 1
        elif tag == "iframe":
            self.iframes += 1
            src = (self._attr(attrs, "src") or "").lower()
            if src:
                self.iframe_srcs.append(src)
            if "youtube" in src or "vimeo" in src or "wistia" in src:
                self.videos += 1
        elif tag == "video":
            self.videos += 1
        elif tag == "form":
            self._form = {
                "action": self._attr(attrs, "action") or "",
                "method": (self._attr(attrs, "method") or "get").lower(),
                "fields": [], "submit_text": None,
                "index": self._el_index,
            }
        elif tag in ("input", "select", "textarea"):
            ftype = (self._attr(attrs, "type") or
                     ("select" if tag == "select" else "textarea" if tag == "textarea" else "text")).lower()
            name = self._attr(attrs, "name") or self._attr(attrs, "id") or ""
            if ftype in ("submit", "button", "image"):
                val = self._attr(attrs, "value") or ""
                if self._form is not None and val:
                    self._form["submit_text"] = val.strip()
                if val:
                    self.buttons.append({"text": val.strip(), "index": self._el_index,
                                         "in_nav": self._nav_depth > 0, "tag": "input"})
            elif ftype != "hidden":
                field = {
                    "name": name, "type": ftype,
                    "required": self._has(attrs, "required"),
                    "placeholder": self._attr(attrs, "placeholder") or None,
                    "label": self._pending_label,
                }
                if self._form is not None:
                    self._form["fields"].append(field)
                self._pending_label = None
        elif tag == "label":
            self._cur_text_sink = "label"
            self._pending_label = ""
        elif tag == "a":
            href = self._attr(attrs, "href") or ""
            self.links.append({"text": "", "href": href, "index": self._el_index,
                               "in_nav": self._nav_depth > 0,
                               "in_form": self._form is not None,
                               "classes": (self._attr(attrs, "class") or "").lower(),
                               "tag": "a"})
            self._cur_text_sink = "link"
        elif tag == "button":
            self.buttons.append({"text": "", "index": self._el_index,
                                 "in_nav": self._nav_depth > 0,
                                 "classes": (self._attr(attrs, "class") or "").lower(),
                                 "tag": "button"})
            self._cur_text_sink = "button"

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TEXT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in NAV_TAGS and self._nav_depth > 0:
            self._nav_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_script = False
        if tag == "style":
            self._in_style = False
        if tag in ("h1", "h2", "h3") and self._heading_stack:
            htag, parts = self._heading_stack.pop()
            txt = norm(" ".join(parts))
            if txt:
                self.headings[htag].append(txt)
        if tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None
        if tag in ("a", "button", "label"):
            self._cur_text_sink = None

    def handle_data(self, data):
        if self._in_title:
            self.title = norm((self.title or "") + data)
            return
        if self._in_script:
            if self._script_inline:
                self.scripts["inline_bytes"] += len(data)
            return
        if self._in_style:
            self.inline_style_bytes += len(data)
            return
        if self._skip_depth > 0:
            return

        if self._heading_stack:
            self._heading_stack[-1][1].append(data)

        sink = self._cur_text_sink
        if sink == "link" and self.links:
            self.links[-1]["text"] = norm(self.links[-1]["text"] + " " + data)
        elif sink == "button" and self.buttons:
            self.buttons[-1]["text"] = norm(self.buttons[-1]["text"] + " " + data)
        elif sink == "label":
            self._pending_label = norm((self._pending_label or "") + " " + data)

        if self._nav_depth == 0:
            self.text_parts.append(data)

def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

# ── Fetching ──────────────────────────────────────────────────────────────────

def http_get(url, timeout=TIMEOUT):
    """Returns (status, final_url, body_text, headers, elapsed_ms, error)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
            raw = r.read(MAX_BYTES)
            if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            enc = "utf-8"
            ctype = r.headers.get("Content-Type") or ""
            m = re.search(r"charset=([\w\-]+)", ctype, re.I)
            if m:
                enc = m.group(1)
            body = raw.decode(enc, errors="replace")
            ms = int((time.time() - t0) * 1000)
            return r.status, r.geturl(), body, dict(r.headers), ms, None
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        try:
            body = e.read(MAX_BYTES).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, url, body, dict(e.headers or {}), ms, f"HTTP {e.code}"
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        return None, url, "", {}, ms, f"{type(e).__name__}: {e}"

# ── Rendering (opt-in, for sites built in JavaScript) ─────────────────────────

RENDER_TIMEOUT = 45          # seconds per page, hard cap
RENDER_BUDGET_MS = 8000      # virtual time Chrome gives the page's scripts to settle

def find_chrome():
    """Path to a Chrome/Chromium binary, or None. CHROME_PATH, when set, is the only answer."""
    env = os.environ.get("CHROME_PATH")
    if env:
        return env if os.path.isfile(env) and os.access(env, os.X_OK) else None
    for path in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium"):
        if os.access(path, os.X_OK):
            return path
    cached = glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"))
    if cached:
        def build(path):
            m = re.search(r"chromium-(\d+)", path)
            return int(m.group(1)) if m else 0
        return max(cached, key=build)
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    return None

def _complete_dom(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 64))
            return f.read().rstrip().lower().endswith(b"</html>")
    except OSError:
        return False

def render_get(url, chrome=None, timeout=RENDER_TIMEOUT):
    """Loads url in headless Chrome. Returns (rendered_html, elapsed_ms, error)."""
    chrome = chrome or find_chrome()
    if not chrome:
        return "", 0, "no Chrome found"
    work = tempfile.mkdtemp(prefix="cro-render-")
    out_path = os.path.join(work, "dom.html")
    t0 = time.time()
    proc = None
    try:
        with open(out_path, "wb") as out:
            # Output goes to a file, never a pipe: Chrome's helper processes can hold a pipe
            # open long after the page is done.
            proc = subprocess.Popen(
                [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                 "--no-default-browser-check", "--disable-extensions",
                 "--user-data-dir=" + os.path.join(work, "profile"),
                 "--user-agent=" + UA,
                 "--virtual-time-budget=%d" % RENDER_BUDGET_MS,
                 "--dump-dom", url],
                stdout=out, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                start_new_session=True)
            # Chrome can write the finished DOM and then never exit, so "done" is judged on
            # the output as well as on the process.
            last_size, steady = -1, 0
            while proc.poll() is None:
                if time.time() - t0 > timeout:
                    return "", int((time.time() - t0) * 1000), \
                        "render timed out after %ds" % timeout
                size = os.path.getsize(out_path)
                steady = steady + 1 if size and size == last_size else 0
                last_size = size
                if steady >= 3 and _complete_dom(out_path):
                    break
                time.sleep(0.25)
        ms = int((time.time() - t0) * 1000)
        with open(out_path, encoding="utf-8", errors="replace") as f:
            body = f.read()
        if not body.rstrip().lower().endswith("</html>"):
            rc = proc.poll()
            return "", ms, ("Chrome exited with code %s without a page" % rc if rc
                            else "Chrome returned an incomplete page")
        return body, ms, None
    except OSError as e:
        return "", int((time.time() - t0) * 1000), "could not start Chrome: %s" % e
    finally:
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        shutil.rmtree(work, ignore_errors=True)

# ── Signal extraction ─────────────────────────────────────────────────────────

def same_host(a, b):
    ha = urllib.parse.urlparse(a).netloc.lower().replace("www.", "")
    hb = urllib.parse.urlparse(b).netloc.lower().replace("www.", "")
    return ha == hb

def extract(url, role, label, status, final_url, body, headers, ms):
    p = PageParser()
    try:
        p.feed(body)
    except Exception:
        pass

    text = norm(" ".join(p.text_parts))
    words = len(text.split())
    low = body.lower()

    # CTAs: links that look like actions + every button
    ctas = []
    for l in p.links:
        txt = norm(l["text"])
        if not txt or len(txt) > 60:
            continue
        href = l["href"] or ""
        # Skip links and other same-page anchors are not CTAs. They also resolve to the
        # current URL, which on an offer page would otherwise look like a CTA into it.
        if href.startswith("#"):
            continue
        abs_href = urllib.parse.urljoin(final_url, href) if href else ""
        if abs_href and urllib.parse.urldefrag(abs_href)[0].rstrip("/") == \
                urllib.parse.urldefrag(final_url)[0].rstrip("/"):
            continue
        is_action = bool(CTA_VERBS.search(txt))
        looks_btn = bool(re.search(r"\bbtn\b|button|cta", l.get("classes", "")))
        # Language-agnostic backstop: a link INTO the conversion or offer stage is a
        # CTA no matter what language it is written in.
        points_at_conversion = bool(abs_href) and same_host(abs_href, final_url) and \
            guess_role(abs_href) in ("conversion", "offer")
        # A vague CTA ("Learn more") is a finding in its own right and still
        # competes for the click, so capture it rather than dropping it.
        if is_action or looks_btn or points_at_conversion or GENERIC_CTA.match(txt):
            ctas.append({
                "text": txt, "href": abs_href, "kind": "link",
                "dom_index": l["index"], "in_nav": l["in_nav"],
                "generic": bool(GENERIC_CTA.match(txt)),
                "external": bool(abs_href) and not same_host(abs_href, final_url),
            })
    for b in p.buttons:
        txt = norm(b["text"])
        if not txt:
            continue
        ctas.append({
            "text": txt, "href": None, "kind": "button",
            "dom_index": b["index"], "in_nav": b.get("in_nav", False),
            "generic": bool(GENERIC_CTA.match(txt)), "external": False,
        })
    ctas.sort(key=lambda c: c["dom_index"])

    body_ctas = [c for c in ctas if not c["in_nav"]]
    distinct_dest = sorted({c["href"] for c in body_ctas if c["href"]})

    # Forms
    forms = []
    for f in p.forms:
        fields = f["fields"]
        # Honeypots are anti-spam decoys the human never sees. Counting them as friction
        # would penalise a site for doing the right thing.
        for fl in fields:
            fl["honeypot"] = bool(
                fl["type"] in ("text", "email", "url", "tel")
                and not fl["required"] and not fl["label"] and not fl["placeholder"]
                and re.fullmatch(r"(website|url|fax|honey.?pot|hp|bot.?field|leave.?blank|"
                                 r"comment.?url|nickname)", (fl["name"] or "").lower()))
        real = [fl for fl in fields if not fl["honeypot"]]
        # search boxes and newsletter signups are not lead forms -- flag, don't drop
        names = " ".join((fl.get("name") or "") + " " + (fl.get("placeholder") or "")
                         for fl in real).lower()
        blob = (names + " " + (f["submit_text"] or "") + " " + (f["action"] or "")).lower()
        field_types = {fl["type"] for fl in real}
        # Asking for a name and an email on a contact page is a lead form, not a
        # newsletter. Only demote when the form says so, or when email is all it wants.
        if ("search" in field_types or re.search(r"\b(search|query)\b", blob)
                or (len(real) == 1 and re.search(r"\bq\b", names))):
            kind = "search"
        elif (re.search(r"subscribe|newsletter|mailing list|insight", blob)
                or (len(real) == 1 and "email" in names)):
            kind = "newsletter"
        else:
            kind = "lead"
        forms.append({
            "action": urllib.parse.urljoin(final_url, f["action"]) if f["action"] else final_url,
            "method": f["method"],
            "kind": kind,
            "field_count": len(real),
            "honeypot_count": len(fields) - len(real),
            "required_count": sum(1 for fl in real if fl["required"]),
            "unlabelled_count": sum(1 for fl in real
                                    if not fl["label"] and not fl["placeholder"]),
            "submit_text": f["submit_text"],
            "fields": fields,
            "dom_index": f["index"],
        })

    # Trust vocabulary
    trust = {}
    for cat, pats in TRUST_TERMS.items():
        hits = 0
        for pat in pats:
            hits += len(re.findall(pat, text, re.I))
        trust[cat] = hits
    proof_claims = [norm(m.group(0)) for m in NUMERIC_PROOF.finditer(text)][:15]

    # Third-party stack
    joined_srcs = " ".join(p.script_srcs) + " " + low
    analytics = sorted([k for k, pat in ANALYTICS_MARKERS.items()
                        if re.search(pat, joined_srcs, re.I)])
    has_chat = bool(re.search(CHAT_MARKERS, joined_srcs, re.I))

    # A booking calendar or form embedded from another site is out of reach, but its presence
    # IS the conversion mechanism -- without this, a page whose only way to book is an
    # embedded calendar reads as a dead end.
    def host_of(s):
        return urllib.parse.urlparse(urllib.parse.urljoin(final_url, s)).netloc.lower()
    embed_srcs = p.iframe_srcs + p.script_srcs
    embeds = {"iframe_hosts": sorted({host_of(s) for s in p.iframe_srcs} - {""})}
    for kind, pat in EMBED_MARKERS.items():
        providers = sorted({host_of(s) for s in embed_srcs if re.search(pat, s, re.I)} - {""})
        embeds[kind] = bool(providers)
        embeds[kind + "_providers"] = providers

    third_party = sorted({urllib.parse.urlparse(
        s if s.startswith("http") else urllib.parse.urljoin(final_url, s)).netloc
        for s in p.script_srcs})
    third_party = [d for d in third_party if d and not same_host("http://" + d, final_url)]

    html_bytes = len(body.encode("utf-8", errors="ignore"))
    # A client-rendered shell is betrayed by missing STRUCTURE, not by brevity:
    # a short page that still ships its headings rendered fine on the server.
    headings_total = len(p.headings["h1"]) + len(p.headings["h2"])
    render_risk = (words < 150 and p.scripts["total"] >= 3 and headings_total <= 1
                   and not forms and len(body_ctas) < 3)
    viewport = p.meta.get("viewport")

    contact = {
        "phone": bool(re.search(r"(tel:|\+\d[\d\s\-\(\)]{7,})", body)),
        "email": bool(re.search(r"mailto:|[\w\.\-]+@[\w\-]+\.\w{2,}", body)),
        "address_hint": bool(re.search(
            r"\b\d{1,5}\s+\w+\s+(street|st|road|rd|avenue|ave|lane|ln|blvd|way)\b", text, re.I)),
    }

    return {
        "url": url,
        "final_url": final_url,
        "role": role,
        "label": label or (p.title or url),
        "http": {
            "status": status,
            "redirected": final_url.rstrip("/") != url.rstrip("/"),
            "elapsed_ms": ms,
            "html_bytes": html_bytes,
            "server": headers.get("Server"),
            "cache_control": headers.get("Cache-Control"),
        },
        "head": {
            "title": p.title,
            "title_len": len(p.title or ""),
            "meta_description": p.meta.get("description"),
            "meta_description_len": len(p.meta.get("description") or ""),
            "canonical": p.canonical,
            "lang": p.lang,
            "viewport": viewport,
            "has_viewport": bool(viewport),
            "og_title": p.meta.get("og:title"),
            "og_image": p.meta.get("og:image"),
            "robots": p.meta.get("robots"),
        },
        "structure": {
            "h1": p.headings["h1"],
            "h1_count": len(p.headings["h1"]),
            "h2": p.headings["h2"][:25],
            "h3": p.headings["h3"][:25],
            "word_count": words,
            "text_sample": text[:2500],
        },
        "ctas": {
            "total": len(ctas),
            "body_total": len(body_ctas),
            "nav_total": len(ctas) - len(body_ctas),
            "distinct_destinations": len(distinct_dest),
            "generic_count": sum(1 for c in ctas if c["generic"]),
            "first_body_cta_index": body_ctas[0]["dom_index"] if body_ctas else None,
            "items": ctas[:40],
        },
        "forms": forms,
        "form_summary": {
            "count": len(forms),
            "lead_forms": sum(1 for f in forms if f["kind"] == "lead"),
            "max_fields": max([f["field_count"] for f in forms], default=0),
            "total_required": sum(f["required_count"] for f in forms),
        },
        "media": {
            "images": p.images["count"],
            "images_missing_alt": p.images["missing_alt"],
            "images_lazy": p.images["lazy"],
            "videos": p.videos,
            "iframes": p.iframes,
        },
        "trust": trust,
        "proof_claims": proof_claims,
        "stack": {
            "analytics": analytics,
            "has_analytics": bool(analytics),
            "has_live_chat": has_chat,
            "third_party_script_domains": third_party[:25],
            "third_party_count": len(third_party),
        },
        "weight": {
            "scripts_total": p.scripts["total"],
            "scripts_external": p.scripts["external"],
            "scripts_head_blocking": p.scripts["head_blocking"],
            "scripts_async_defer": p.scripts["async_defer"],
            "inline_script_bytes": p.scripts["inline_bytes"],
            "stylesheets": p.stylesheets,
            "inline_style_bytes": p.inline_style_bytes,
        },
        "contact": contact,
        "embeds": embeds,
        "render_risk": render_risk,
        "render_risk_note": (
            "Only %d words of text were present in the raw HTML alongside %d script tags. "
            "This page is likely client-rendered; the extracted signals understate it. "
            "Paste the rendered copy manually or audit this page by hand."
            % (words, p.scripts["total"]) if render_risk else None),
        "error": None,
    }

# ── Discovery ─────────────────────────────────────────────────────────────────

def discover(site, render=False):
    site = site if site.startswith("http") else "https://" + site
    out = {"site": site, "fetched": [], "homepage": None, "candidates": [], "notes": []}

    status, final_url, body, headers, ms, err = http_get(site)
    out["fetched"].append({"url": site, "status": status, "ms": ms, "error": err})
    # Same test as run_fetch: an error page still has a body, so judge on the status.
    if bool(err) or status is None or status >= 400:
        out["homepage"] = {"status": status, "final_url": final_url, "failed": True}
        if status is not None and status >= 400:
            reason = "Homepage returned HTTP %s" % status
        else:
            reason = "Homepage fetch failed: %s" % (err or "no response")
        out["notes"].append("%s -- the site is down or blocking requests. Nothing to audit."
                            % reason)
        return out

    render_info = {"rendered": False}
    if render:
        rbody, rms, rerr = render_get(final_url)
        if rerr:
            out["homepage"] = {"status": status, "final_url": final_url, "failed": True,
                               "rendered": True}
            out["notes"].append("Homepage loaded (HTTP %s) but rendering it in Chrome failed: "
                                "%s. Nothing to audit." % (status, rerr))
            return out
        render_info = {"rendered": True, "render_ms": rms,
                       "raw_html_bytes": len(body.encode("utf-8", errors="ignore"))}
        body = rbody

    base = final_url
    p = PageParser()
    try:
        p.feed(body)
    except Exception:
        pass

    home_sig = extract(site, "entry", "Home", status, final_url, body, headers, ms)
    out["homepage"] = {
        "status": status,
        "final_url": final_url,
        "failed": False,
        "render_risk": home_sig["render_risk"],
        "word_count": home_sig["structure"]["word_count"],
        "scripts_total": home_sig["weight"]["scripts_total"],
        "links_found": len(p.links),
        **render_info,
    }
    if home_sig["render_risk"] and render_info["rendered"]:
        out["notes"].append(
            "Even rendered in Chrome, the homepage has %d words and %d links. It may need a "
            "login, block headless browsers, or load its content later than Chrome waited."
            % (out["homepage"]["word_count"], out["homepage"]["links_found"]))
    elif home_sig["render_risk"]:
        out["notes"].append(
            "Homepage looks client-rendered (%d words, %d scripts, %d links in raw HTML). "
            "Pages will likely come back empty -- re-run discover with --render."
            % (out["homepage"]["word_count"], out["homepage"]["scripts_total"],
               out["homepage"]["links_found"]))

    seen = {}
    for l in p.links:
        href = (l["href"] or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absu = urllib.parse.urljoin(base, href)
        absu, _ = urllib.parse.urldefrag(absu)
        if not absu.startswith("http") or not same_host(absu, base):
            continue
        if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|mp4|webp|css|js)$", absu, re.I):
            continue
        absu = absu.rstrip("/") or absu
        rec = seen.setdefault(absu, {"url": absu, "anchors": [], "count": 0,
                                     "in_nav": False})
        rec["count"] += 1
        if l["in_nav"]:
            rec["in_nav"] = True
        t = norm(l["text"])
        if t and t not in rec["anchors"]:
            rec["anchors"].append(t[:60])

    # sitemap, via robots.txt then the conventional path
    sitemap_urls = []
    rstat, _, rbody, _, rms, rerr = http_get(urllib.parse.urljoin(base, "/robots.txt"))
    out["fetched"].append({"url": "/robots.txt", "status": rstat, "ms": rms, "error": rerr})
    if rbody:
        sitemap_urls += re.findall(r"(?i)^\s*sitemap:\s*(\S+)", rbody, re.M)
    if not sitemap_urls:
        sitemap_urls = [urllib.parse.urljoin(base, "/sitemap.xml")]

    for sm in sitemap_urls[:2]:
        sstat, _, sbody, _, sms, serr = http_get(sm)
        out["fetched"].append({"url": sm, "status": sstat, "ms": sms, "error": serr})
        if not sbody:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sbody, re.I)
        for u in locs[:400]:
            u, _ = urllib.parse.urldefrag(u)
            if not same_host(u, base):
                continue
            if re.search(r"\.(xml|pdf|jpg|png)$", u, re.I):
                continue
            u = u.rstrip("/") or u
            rec = seen.setdefault(u, {"url": u, "anchors": [], "count": 0, "in_nav": False})
            rec.setdefault("in_sitemap", True)
            rec["in_sitemap"] = True

    home = base.rstrip("/")
    seen.setdefault(home, {"url": home, "anchors": ["Home"], "count": 1, "in_nav": True})

    for u, rec in seen.items():
        rec["role"] = guess_role(u, " ".join(rec["anchors"]))
        rec["in_sitemap"] = rec.get("in_sitemap", False)
        out["candidates"].append(rec)

    order = {"entry": 0, "value": 1, "proof": 2, "offer": 3, "conversion": 4,
             "trust": 5, "support": 6, "content": 7, "other": 8}
    out["candidates"].sort(key=lambda r: (order.get(r["role"], 9), -r["count"], r["url"]))
    out["notes"].append("%d internal URLs found. Confirm the shortlist before fetching."
                        % len(out["candidates"]))
    return out

# ── Fetch run ─────────────────────────────────────────────────────────────────

def run_fetch(plan):
    site = plan.get("site") or ""
    pages_in = plan.get("pages") or []
    delay = float(plan.get("delay_seconds", 1.0))
    render = bool(plan.get("render"))
    chrome = find_chrome() if render else None
    if render and not chrome:
        raise RuntimeError("render requested but no Chrome found")
    results, errors = [], []

    for i, spec in enumerate(pages_in):
        url = spec["url"] if isinstance(spec, dict) else spec
        role = spec.get("role") if isinstance(spec, dict) else None
        label = spec.get("label") if isinstance(spec, dict) else None
        if not url.startswith("http"):
            url = "https://" + url
        role = role or guess_role(url)

        status, final_url, body, headers, ms, err = http_get(url)
        # An error page still has a body -- judge on the status code, or a 404 gets
        # audited as though it were a real page.
        failed = bool(err) or status is None or status >= 400
        reason = (err or "HTTP %s" % status) if failed else None
        rendered = {"rendered": False}
        if not failed and render:
            # The raw fetch above still owns status, headers and redirects; Chrome only
            # supplies the page as a visitor sees it. A failed render is an error, never a
            # silent fall back to the empty shell.
            rbody, rms, rerr = render_get(final_url, chrome)
            if rerr:
                failed, reason = True, "render failed: %s" % rerr
            else:
                rendered = {"rendered": True, "render_ms": rms,
                            "raw_html_bytes": len(body.encode("utf-8", errors="ignore"))}
                body = rbody
        if failed:
            errors.append({"url": url, "status": status, "error": reason})
            results.append({"url": url, "role": role, "label": label,
                            "http": {"status": status, "elapsed_ms": ms},
                            "error": reason, "render_risk": False})
        else:
            rec = extract(url, role, label, status, final_url, body, headers, ms)
            rec["http"].update(rendered)
            results.append(rec)
        if i < len(pages_in) - 1 and delay:
            time.sleep(delay)

    return {
        "site": site,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "rendered": render,
        "page_count": len(results),
        "ok_count": sum(1 for r in results if not r.get("error")),
        "render_risk_count": sum(1 for r in results if r.get("render_risk")),
        "errors": errors,
        "pages": results,
    }

# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    mode, target = argv[1], argv[2]
    out_path = None
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]

    render = "--render" in argv
    if mode == "fetch":
        with open(target, encoding="utf-8") as f:
            plan = json.load(f)
        render = render or bool(plan.get("render"))
        plan["render"] = render
    if render and mode in ("discover", "fetch") and not find_chrome():
        print("--render needs Chrome and none was found. Install Google Chrome, or set "
              "CHROME_PATH to a Chrome or Chromium binary.")
        return 3

    if mode == "discover":
        data = discover(target, render=render)
        out_path = out_path or "candidates.json"
    elif mode == "fetch":
        data = run_fetch(plan)
        out_path = out_path or "pages.json"
    else:
        print("Unknown mode: %s (use discover|fetch)" % mode)
        return 1

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Wrote %s" % out_path)
    if mode == "fetch":
        print("  %d/%d pages fetched%s, %d at render risk"
              % (data["ok_count"], data["page_count"],
                 " (rendered in Chrome)" if data["rendered"] else "", data["render_risk_count"]))
        for e in data["errors"]:
            print("  ! %s -- %s" % (e["url"], e["error"]))
    else:
        home = data.get("homepage") or {}
        if home.get("failed"):
            print("  ! %s" % data["notes"][0])
            return 2
        print("  %d candidate URLs" % len(data["candidates"]))
        if home.get("render_risk"):
            print("  ! %s" % data["notes"][0])
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
