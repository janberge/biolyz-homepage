"""Fold an Illustrator SVG's <style> classes into inline style attributes.

Two Illustrator exports inlined into one HTML document collide hard: an SVG
<style> block is document-global, and both of these declare .st0/.st1/.st2 with
different colours, plus a duplicate id="Layer_1". Removing the stylesheet
entirely and pushing each rule onto the element that used it makes each mark
self-contained, which is the only way two of them can share a page.
"""
import re


def clean(path, prefix, viewbox=None, drop=None, recolor=False):
    """viewbox: replace/insert one (these marks need tight ink bounds so three
    wordmarks of different proportions can be sized against each other).
    drop: a literal substring to remove first, e.g. a full-canvas background.
    recolor: force every fill to currentColor, so a one-colour mark can follow
    the ground it sits on instead of needing a second file."""
    s = open(path, encoding="utf-8").read()
    if drop:
        assert drop in s, "drop target not found in " + path
        s = s.replace(drop, "")
    s = re.sub(r'<\?xml.*?\?>', '', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)

    # 1. Harvest the stylesheet, then drop it.
    rules = {}
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', s, re.S):
        for cls, body in re.findall(r'\.([A-Za-z0-9_\\x-]+)\s*\{([^}]*)\}', m.group(1)):
            rules[cls.replace('\\', '')] = ' '.join(body.split())
    s = re.sub(r'<style[^>]*>.*?</style>', '', s, flags=re.S)

    # 2. Every class becomes the declarations it stood for. A rule with no
    #    `fill` leaves the element at the SVG default of black, which is
    #    exactly what the stylesheet meant.
    def sub_class(m):
        names = m.group(1).split()
        decls = '; '.join(rules[n] for n in names if n in rules)
        return 'style="%s"' % decls if decls else ''
    s = re.sub(r'class="([^"]+)"', sub_class, s)

    # 3. Namespace whatever ids survive, so two marks never share one.
    ids = set(re.findall(r'\sid="([^"]+)"', s))
    for i in sorted(ids, key=len, reverse=True):
        s = s.replace('id="%s"' % i, 'id="%s-%s"' % (prefix, i))
        s = s.replace('url(#%s)' % i, 'url(#%s-%s)' % (prefix, i))
        s = s.replace('xlink:href="#%s"' % i, 'xlink:href="#%s-%s"' % (prefix, i))

    # 4. Strip Illustrator's positioning cruft and empty groups.
    s = re.sub(r'\s(?:x|y)="0px"', '', s)
    s = re.sub(r'\sstyle="enable-background:[^"]*"', '', s)
    s = re.sub(r'<g[^>]*>\s*</g>', '', s)

    # 4a. One-colour marks follow their surroundings.
    if recolor:
        s = re.sub(r'fill="(?!none)[^"]*"', 'fill="currentColor"', s)
        # Step 2 above folds Illustrator's <style> classes into inline style=,
        # so a one-colour mark's colour usually ends up THERE and never in a
        # fill attribute — which is how a navy wordmark shipped through a
        # recolor that only ever looked at attributes. "fill:" does not match
        # "fill-rule:", so the rule survives.
        s = re.sub(r'fill:\s*(?!none)[^;"]+', 'fill: currentColor', s)

    # 4b. A tight viewBox, and never width/height attributes — CSS sizes these.
    if viewbox:
        if re.search(r'\sviewBox="[^"]*"', s):
            s = re.sub(r'\sviewBox="[^"]*"', ' viewBox="%s"' % viewbox, s, count=1)
        else:
            s = s.replace('<svg ', '<svg viewBox="%s" ' % viewbox, 1)
    s = re.sub(r'<svg([^>]*?)\s(?:width|height)="[^"]*"', r'<svg\1', s)
    s = re.sub(r'<svg([^>]*?)\s(?:width|height)="[^"]*"', r'<svg\1', s)

    # 5. The element sizes from CSS; it is decoration with a text label beside it.
    # A literal '<svg ' only matches a single-space export (Illustrator); an
    # Inkscape file opens with '<svg\n  ' instead, so this needs to match on
    # *any* whitespace after the tag name, not one exact character.
    s = re.sub(r'<svg(?=\s)', '<svg class="logo-svg" aria-hidden="true" focusable="false"', s, count=1)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


if __name__ == '__main__':
    import sys
    print(clean(sys.argv[1], sys.argv[2]))
