"""
Offline regression test for fetch_pages.extract(). No network, no API, no cost.
Run: python3 scripts/tests/test_extract.py
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fetch_pages as fp

def check(name, actual, expected):
    ok = actual == expected
    print(("  ok   " if ok else "  FAIL ") + name +
          ("" if ok else "  expected %r, got %r" % (expected, actual)))
    return ok

def check_true(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + ("" if cond else "  " + detail))
    return bool(cond)

def main():
    html = open(os.path.join(HERE, "fixture_landing.html"), encoding="utf-8").read()
    page = fp.extract("https://acme.test/", "entry", "Home", 200,
                      "https://acme.test/", html, {"Server": "test"}, 120)

    results = []
    print("head / structure")
    results.append(check("title", page["head"]["title"],
                         "Acme Books — Bookkeeping for tradespeople"))
    results.append(check("has_viewport", page["head"]["has_viewport"], True))
    results.append(check("canonical", page["head"]["canonical"], "https://acme.test/"))
    results.append(check("h1_count", page["structure"]["h1_count"], 1))
    results.append(check("h1 text", page["structure"]["h1"][0],
                         "Bookkeeping that stays out of your way"))
    results.append(check("h2 count", len(page["structure"]["h2"]), 2))
    results.append(check_true("nav text excluded from body copy",
                              "Home Pricing About" not in page["structure"]["text_sample"],
                              page["structure"]["text_sample"][:80]))

    print("ctas")
    ctas = page["ctas"]
    texts = [c["text"] for c in ctas["items"]]
    results.append(check_true("nav CTA detected", "Get started" in texts, str(texts)))
    results.append(check_true("body CTA detected", "Start free trial" in texts, str(texts)))
    results.append(check_true("button element captured", "Request a callback" in texts, str(texts)))
    results.append(check_true("nav/body split", ctas["nav_total"] >= 1 and ctas["body_total"] >= 3,
                              json.dumps({k: ctas[k] for k in ("nav_total", "body_total")})))
    results.append(check_true("generic CTA flagged", ctas["generic_count"] >= 1,
                              str([c["text"] for c in ctas["items"] if c["generic"]])))
    results.append(check_true("external CTA flagged",
                              any(c["external"] for c in ctas["items"]),
                              str([c["text"] for c in ctas["items"] if c["external"]])))
    results.append(check_true("competing destinations counted",
                              ctas["distinct_destinations"] >= 3,
                              str(ctas["distinct_destinations"])))

    print("forms")
    f = page["forms"][0]
    results.append(check("form kind", f["kind"], "lead"))
    results.append(check("visible field count (hidden excluded)", f["field_count"], 7))
    results.append(check("required count", f["required_count"], 6))
    results.append(check("submit text", f["submit_text"], "Submit"))
    # company, vat_number, trade, notes carry neither a <label> nor a placeholder
    results.append(check_true("unlabelled fields counted", f["unlabelled_count"] == 4,
                              str(f["unlabelled_count"])))
    results.append(check("label bound to first field", f["fields"][0]["label"], "Full name"))
    results.append(check("form_summary max_fields", page["form_summary"]["max_fields"], 7))

    print("trust / proof")
    results.append(check_true("social proof terms", page["trust"]["social_proof"] >= 3,
                              str(page["trust"])))
    results.append(check_true("risk reversal terms", page["trust"]["risk_reversal"] >= 2,
                              str(page["trust"])))
    results.append(check_true("security terms", page["trust"]["security"] >= 2, str(page["trust"])))
    results.append(check_true("authority terms", page["trust"]["authority"] >= 2, str(page["trust"])))
    results.append(check_true("numeric claims extracted", len(page["proof_claims"]) >= 2,
                              str(page["proof_claims"])))

    print("media / stack / weight")
    results.append(check("images", page["media"]["images"], 2))
    results.append(check("images missing alt", page["media"]["images_missing_alt"], 1))
    results.append(check_true("analytics detected",
                              "google_analytics" in page["stack"]["analytics"],
                              str(page["stack"]["analytics"])))
    results.append(check("head blocking scripts", page["weight"]["scripts_head_blocking"], 2))
    results.append(check("stylesheets", page["weight"]["stylesheets"], 1))
    results.append(check_true("phone found", page["contact"]["phone"]))

    print("render risk")
    results.append(check("content-rich page is not flagged", page["render_risk"], False))
    spa = fp.extract("https://spa.test/", "entry", "SPA", 200, "https://spa.test/",
                     '<html><head><script src="/a.js"></script><script src="/b.js"></script>'
                     '<script src="/c.js"></script></head><body><div id="root"></div></body></html>',
                     {}, 90)
    results.append(check("empty SPA shell is flagged", spa["render_risk"], True))
    results.append(check_true("render risk carries a note", bool(spa["render_risk_note"])))

    print("bilingual CTAs")
    es_html = """<html lang="es"><head><title>Servicios</title></head><body>
      <a href="#main-content">Saltar al contenido principal</a>
      <header><nav><a href="/es">Inicio</a><a href="/es/contact">Contacto</a></nav></header>
      <main><h1>Lanza. Crece. Escala.</h1><h2>Paquetes</h2>
      <p>Servicios organizados seg\u00fan d\u00f3nde est\u00e1 tu negocio hoy.</p>
      <a href="/es/contact?package=launch">Empezar</a>
      <a href="/es/contact">Cont\u00e1ctanos</a>
      <a href="/es/contact">Hablemos</a>
      <a href="/es/products">Nuestra plataforma</a>
      <a href="/es/insights">Leer el blog</a></main></body></html>"""
    es = fp.extract("https://a.test/es/services", "value", "Servicios", 200,
                    "https://a.test/es/services", es_html, {}, 100)
    es_texts = [c["text"] for c in es["ctas"]["items"]]
    results.append(check_true("Spanish verb CTA detected", "Empezar" in es_texts, str(es_texts)))
    results.append(check_true("Spanish contact CTA detected",
                              "Cont\u00e1ctanos" in es_texts, str(es_texts)))
    results.append(check_true("Spanish 'Hablemos' detected", "Hablemos" in es_texts, str(es_texts)))
    results.append(check_true("link into offer stage counts as a CTA regardless of wording",
                              "Nuestra plataforma" in es_texts, str(es_texts)))
    results.append(check_true("a plain content link is NOT a CTA",
                              "Leer el blog" not in es_texts, str(es_texts)))
    results.append(check_true("package-tagged destinations counted separately",
                              es["ctas"]["distinct_destinations"] >= 3,
                              str(es["ctas"]["distinct_destinations"])))

    results.append(check_true("skip link is not a CTA",
                              not any(c["text"].startswith("Saltar") for c in es["ctas"]["items"]),
                              str(es_texts)))

    print("render risk guards")
    short_with_form = """<html><head><title>Contacto</title>
      <script src="/a.js"></script><script src="/b.js"></script><script src="/c.js"></script>
      </head><body><h1>Start a Conversation</h1>
      <form action="/lead" method="post"><label for="n">Name</label>
      <input id="n" name="name" required><input type="email" name="email" required>
      <input type="submit" value="Send Message"></form></body></html>"""
    swf = fp.extract("https://a.test/contact", "conversion", "Contact", 200,
                     "https://a.test/contact", short_with_form, {}, 100)
    results.append(check("a short page that shipped a form is not render risk",
                         swf["render_risk"], False))
    results.append(check("its form is still classed as a lead form",
                         swf["forms"][0]["kind"], "lead"))

    print("embeds")
    booking_page = """<!doctype html><html><head><title>Book</title></head><body>
      <h1>Book a consultation</h1>
      <iframe src="https://calendar.google.com/calendar/appointments/schedules/AbC?gv=true"></iframe>
      <iframe src="https://www.youtube.com/embed/xyz"></iframe></body></html>"""
    bk = fp.extract("https://a.test/book", "conversion", "Book", 200,
                    "https://a.test/book", booking_page, {}, 100)
    results.append(check("google calendar appointments iframe is a booking embed",
                         bk["embeds"]["booking"], True))
    results.append(check("booking provider host recorded",
                         bk["embeds"]["booking_providers"], ["calendar.google.com"]))
    results.append(check("every iframe host recorded",
                         bk["embeds"]["iframe_hosts"], ["calendar.google.com", "www.youtube.com"]))
    results.append(check("no form embed on the booking page", bk["embeds"]["form"], False))
    video_page = """<html><body><h1>Watch</h1>
      <iframe src="https://www.youtube.com/embed/xyz"></iframe></body></html>"""
    vd = fp.extract("https://a.test/watch", "value", "Watch", 200,
                    "https://a.test/watch", video_page, {}, 100)
    results.append(check("a video iframe is not a booking embed", vd["embeds"]["booking"], False))
    typeform_page = """<html><body><h1>Tell us about you</h1>
      <div data-tf-widget="abc"></div><script src="//embed.typeform.com/next/embed.js"></script>
      </body></html>"""
    tf = fp.extract("https://a.test/apply", "conversion", "Apply", 200,
                    "https://a.test/apply", typeform_page, {}, 100)
    results.append(check("an embedded Typeform script is a form embed", tf["embeds"]["form"], True))

    print("role guessing")
    results.append(check("home", fp.guess_role("https://a.test/"), "entry"))
    results.append(check("pricing", fp.guess_role("https://a.test/pricing"), "offer"))
    results.append(check("contact", fp.guess_role("https://a.test/contact-us"), "conversion"))
    results.append(check("case studies", fp.guess_role("https://a.test/case-studies/acme"), "proof"))
    results.append(check("features", fp.guess_role("https://a.test/features"), "value"))
    results.append(check("blog", fp.guess_role("https://a.test/blog/post-1"), "content"))
    results.append(check("anchor fallback",
                         fp.guess_role("https://a.test/xyz", "Book a demo"), "conversion"))
    results.append(check("locale root is the homepage",
                         fp.guess_role("https://a.test/en"), "entry"))
    results.append(check("locale root with trailing slash",
                         fp.guess_role("https://a.test/es/"), "entry"))
    results.append(check("locale-region root",
                         fp.guess_role("https://a.test/en-us"), "entry"))
    results.append(check("locale prefix does not swallow the path",
                         fp.guess_role("https://a.test/en/pricing"), "offer"))
    results.append(check("keyword inside a hyphenated slug: pricing",
                         fp.guess_role("https://a.test/tax-pricing"), "offer"))
    results.append(check("keyword inside a hyphenated slug: services",
                         fp.guess_role("https://a.test/south-florida-tax-services"), "value"))
    results.append(check("keyword inside a hyphenated slug: guide",
                         fp.guess_role("https://a.test/tax-guide"), "content"))
    results.append(check("keyword inside a hyphenated slug: resources",
                         fp.guess_role("https://a.test/tax-resources"), "content"))
    results.append(check("segment-start keyword with a hyphenated tail",
                         fp.guess_role("https://a.test/book-appointment"), "conversion"))
    results.append(check("segment-start match beats a keyword later in the slug",
                         fp.guess_role("https://a.test/blog/how-to-book-a-flight"), "content"))

    passed, total = sum(1 for r in results if r), len(results)
    print("\n%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
