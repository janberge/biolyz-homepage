"""Client pages: one password-protected page per prospective customer.

    python3 build.py            # seals every client and copies them to serve/c/

A client lives in clients/<slug>/, which is gitignored because this repository
is public:

    clients/<slug>/page.html    the page body (start from a copy of an existing client)
    clients/<slug>/data.json    calculator data: packages, squad, salaries
    clients/<slug>/pass.txt     the password, one line
    clients/<slug>/files/       downloads and images, each sealed on its own:
                                <a data-file="name"> fetches on click,
                                <img data-img="name"> loads after unlock

build.py calls build() below. Each client is encrypted into
client-pages/<slug>.html, which IS committed: it holds only ciphertext, so the
deploy can serve it without the source or the password. Every build copies
those files to serve/c/<slug>/index.html, so the page lives at /c/<slug>.

Sealing is deterministic (fixed salt per slug, no random nonce), so an
unchanged client produces a byte-identical file and git shows no change.
Each client has its own salt and label, so one password never opens another
client's page. Construction and caveats: see the comment in
tools/client_shell.html.
"""
import base64, hashlib, hmac, json, os, re, shutil, struct, zlib

ITER = 600000


def _key(slug, password):
    salt = hashlib.sha256(b"biolyz-client-salt:" + slug.encode()).digest()[:16]
    return salt, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITER, 32)


def _seal(slug, password, plaintext):
    salt, key = _key(slug, password)
    out = _seal_with(key, slug, plaintext)
    out.update({"slug": slug, "salt": salt.hex(), "iter": ITER,
                "verify": hmac.new(key, b"biolyz-client-verify", hashlib.sha256).hexdigest()})
    return out


def _seal_with(key, name, plaintext):
    label = name.encode()
    body = zlib.compress(plaintext, 9)
    stream, i = bytearray(), 0
    while len(stream) < len(body):
        stream += hmac.new(key, label + b"\x01" + struct.pack(">Q", i), hashlib.sha256).digest()
        i += 1
    ct = bytes(a ^ b for a, b in zip(body, stream))
    return {"c": base64.b64encode(ct).decode(),
            "t": hmac.new(key, label + b"\x02" + ct, hashlib.sha256).hexdigest()}


def build(root, logo_svg):
    src_dir = os.path.join(root, "clients")
    out_dir = os.path.join(root, "client-pages")
    shell = open(os.path.join(root, "tools", "client_shell.html"), encoding="utf-8").read()
    sealed = []
    if os.path.isdir(src_dir):
        os.makedirs(out_dir, exist_ok=True)
        for slug in sorted(os.listdir(src_dir)):
            d = os.path.join(src_dir, slug)
            if slug.startswith(("_", ".")) or not os.path.exists(os.path.join(d, "page.html")):
                continue
            assert re.fullmatch(r"[a-z0-9-]+", slug), "client folder names are URL slugs: %s" % slug
            pw = os.environ.get("BIOLYZ_CLIENT_PASS_" + slug.upper().replace("-", "_")) or \
                open(os.path.join(d, "pass.txt"), encoding="utf-8").read().strip()
            # A short password can be guessed offline against the public file.
            # Allowed only where someone decided so: clients/<slug>/weak-password-ok
            assert len(pw) >= 12 or os.path.exists(os.path.join(d, "weak-password-ok")), \
                "client %s: use a password of 12+ characters" % slug
            page = open(os.path.join(d, "page.html"), encoding="utf-8").read()
            title = re.search(r"<title>(.*?)</title>", page, re.S).group(1).strip()
            page = re.sub(r"<title>.*?</title>\s*", "", page, count=1, flags=re.S)
            dpath = os.path.join(d, "data.json")
            data = json.load(open(dpath, encoding="utf-8")) if os.path.exists(dpath) else None
            # Downloads: each sealed into its own file under an opaque name, so
            # the public repo shows neither the content nor the file names.
            files, fdir = {}, os.path.join(d, "files")
            sealed_dir = os.path.join(out_dir, slug, "files")
            if os.path.isdir(sealed_dir):
                shutil.rmtree(sealed_dir)
            if os.path.isdir(fdir):
                os.makedirs(sealed_dir)
                _, key = _key(slug, pw)
                for fn in sorted(os.listdir(fdir)):
                    if fn.startswith("."):
                        continue
                    opaque = hashlib.sha256(("%s/%s" % (slug, fn)).encode()).hexdigest()[:16] + ".json"
                    blob = open(os.path.join(fdir, fn), "rb").read()
                    json.dump(_seal_with(key, "%s:%s" % (slug, fn), blob),
                              open(os.path.join(sealed_dir, opaque), "w"))
                    ext = fn.lower().rsplit(".", 1)[-1]
                    files[fn] = {"path": opaque, "type": {"pdf": "application/pdf", "jpg": "image/jpeg",
                                 "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
                                 ext, "application/octet-stream")}
                    assert ('data-file="%s"' % fn) in page or ('data-img="%s"' % fn) in page, \
                        "client %s: files/%s is not used in page.html" % (slug, fn)
            payload = json.dumps({"title": title, "html": page, "data": data, "files": files}, ensure_ascii=False)
            html = shell.replace("__LOGO__", logo_svg).replace(
                "__SEALED__", json.dumps(_seal(slug, pw, payload.encode())))
            # Nothing readable may reach the public file. A phrase from the page
            # body that survives would mean the sealing step was skipped.
            probe = re.sub(r"<[^>]+>", " ", page)
            probe = max(re.findall(r"[A-Za-zÄÖÜäöüß]{9,}", probe) or [""], key=len)
            assert not probe or probe not in html, "client %s: plaintext leaked" % slug
            open(os.path.join(out_dir, slug + ".html"), "w", encoding="utf-8").write(html)
            sealed.append(slug)

    served = []
    if os.path.isdir(out_dir):
        for f in sorted(os.listdir(out_dir)):
            if f.endswith(".html"):
                dst = os.path.join(root, "serve", "c", f[:-5])
                os.makedirs(dst, exist_ok=True)
                shutil.copyfile(os.path.join(out_dir, f), os.path.join(dst, "index.html"))
                if os.path.isdir(os.path.join(dst, "files")):
                    shutil.rmtree(os.path.join(dst, "files"))
                if os.path.isdir(os.path.join(out_dir, f[:-5], "files")):
                    shutil.copytree(os.path.join(out_dir, f[:-5], "files"), os.path.join(dst, "files"))
                served.append(f[:-5])
    print("client pages: sealed %s, serving %s"
          % (", ".join(sealed) or "none (no clients/ here)", ", ".join("/c/" + s for s in served) or "none"))
