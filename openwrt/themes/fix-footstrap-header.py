#!/usr/bin/env python3
"""Inject the content-header layout fix into footstrap's header template.

Why: footstrap ships `header { display: flex; position: sticky; top: 0 }` as an
element selector. It is meant for the top bar, but it also matches <header>
elements that page code renders inside the content area -- luci-app-unisoc-ota
builds `<header class="mud-ota-heading">` with a kicker span, an h2 and a note,
and all three end up laid out in one flex row, stuck to the top of the page,
which reads as overlapping headings.

The fix is a small inline <style> that returns those headers to normal block
flow. It goes into the theme template (not a static CSS file) so it ships with
the page HTML and is not subject to browser caching of cascade.css.

Usage:
    fix-footstrap-header.py <path/to/header.ut> <path/to/footstrap-header-fix.html>

Idempotent: a template that already carries the marker is left untouched.
"""

import sys

MARKER = 'id="E5-HEADER-FIX"'
ANCHOR = "{% include('themes/footstrap/partials/head', { boardinfo, fs_defaults }) %}"


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    template_path, snippet_path = argv[1], argv[2]

    with open(template_path, encoding='utf-8') as handle:
        template = handle.read()
    if MARKER in template:
        print('footstrap header.ut: layout fix already present')
        return 0
    if ANCHOR not in template:
        print('footstrap header.ut: head include not found, skipped', file=sys.stderr)
        return 1

    with open(snippet_path, encoding='utf-8') as handle:
        snippet = handle.read()

    template = template.replace(ANCHOR, ANCHOR + '\n' + snippet, 1)
    with open(template_path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(template)
    print('footstrap header.ut: injected content-header layout fix')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
