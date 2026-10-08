# yasno.games

The studio's site: one static page on Firebase Hosting, served from `public/`.

## Deploy

`.github/workflows/deploy.yml` deploys: a push to `main` goes live, a push to
any other branch gets a preview channel for a week, and a run started by hand
puts any commit, branch or tag live. It signs in through Workload Identity
Federation, so no key exists to leak.

By hand, as the studio's Google account, never a personal one:

```bash
npx firebase-tools@latest deploy --only hosting --project yasno-games --account reed@yasno.games
```

## Brand kit

`public/brand/` holds the logo as SVG outlines and PNG renders, served at
`https://yasno.games/brand/` for press and storefronts. `public/favicon.svg`,
`public/apple-touch-icon.png` and `public/og.png` (the link preview) come from
the same source. They are generated once and committed; to change them, edit
`tools/brand.py`, never the files, and run it:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r tools/requirements.txt
.venv/Scripts/python -I tools/brand.py
```

`public/intro.js` is the page's mark: the round monogram, breathing, that turns
into the wordmark and types the tagline once it is hovered or pressed. It is
built from the same outlines by `tools/intro.py`; edit that, never the script,
and run it the same way. Without JavaScript the page shows the wordmark as is.

The typefaces are Unbounded (marks) and JetBrains Mono (tagline), both under
the SIL Open Font License; their licences sit beside them in `tools/fonts/`.

| Token | Hex |
|-------|-----|
| Ink | `#121417` |
| Paper | `#F5F5F2` |
| Accent | `#2B6CF6` |
| Accent on dark | `#5B8DFF` |
