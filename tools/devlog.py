"""Build the devlog under public/devlog/ from the posts in devlog/.

A post is a folder, devlog/<slug>/, holding post.md and whatever it shows. The
slug is the post's address, yasno.games/devlog/<slug>, so it never changes once
published. post.md opens with its fields between --- lines:

    ---
    title: Rivers that run along the troughs
    date: 2026-10-20
    author: Reed
    summary: One sentence, the text of the link preview and the feed.
    image: ridge.png
    ---

`image` is optional: the link preview, 1200 x 630 reads best; without it the
studio's own preview stands in. The body is Markdown, raw HTML allowed (a
<video> needs it); a relative link or image names a file in the post's folder.

A standing page is a folder, pages/<slug>/, holding page.md and its files,
served at yasno.games/<slug>/. It opens with title, summary and an optional
image, no date or author, and sits in neither the index nor the feed.

public/devlog/ and each page's public/<slug>/ are this script's alone: each
run deletes them and writes them again — the index, a page per post with its
files beside it, an Atom feed, and the standing pages — so a post or page
taken out of its folder leaves the site too.

    python -I tools/devlog.py
"""
import datetime
import html
import pathlib
import re
import shutil

from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "devlog"
PAGES = ROOT / "pages"
OUT = ROOT / "public" / "devlog"
SITE = "https://yasno.games"
FIELDS = {"title", "date", "author", "summary", "image"}
REQUIRED = FIELDS - {"image"}
PAGE_FIELDS = {"title", "summary", "image"}
# public/ folders that are not a page's to delete.
RESERVED = {"devlog", "brand"}


class Post:
    def __init__(self, folder):
        self.slug = folder.name
        self.folder = folder
        fields, body = front_matter((folder / "post.md").read_text(encoding="utf-8"), folder)
        self.title = fields["title"]
        self.date = datetime.date.fromisoformat(fields["date"])
        self.author = fields["author"]
        self.summary = fields["summary"]
        self.image = fields.get("image")
        if self.image and not (folder / self.image).is_file():
            raise SystemExit(f"{folder.name}: image {self.image} is not in the post's folder")
        self.path = f"/devlog/{self.slug}/"
        self.body = render(body, self.path)

    def preview(self):
        return f"{self.path}{self.image}" if self.image else "/og.png"


class Page:
    def __init__(self, folder):
        self.slug = folder.name
        if self.slug in RESERVED:
            raise SystemExit(f"{self.slug}: public/{self.slug}/ is not a page's to overwrite")
        self.folder = folder
        fields, body = front_matter((folder / "page.md").read_text(encoding="utf-8"), folder, PAGE_FIELDS, {"title", "summary"})
        self.title = fields["title"]
        self.summary = fields["summary"]
        self.image = fields.get("image")
        if self.image and not (folder / self.image).is_file():
            raise SystemExit(f"{folder.name}: image {self.image} is not in the page's folder")
        self.path = f"/{self.slug}/"
        self.body = render(body, self.path)

    preview = Post.preview


def front_matter(text, folder, known=FIELDS, required=REQUIRED):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in (l.strip() for l in lines[1:]):
        raise SystemExit(f"{folder.name}: the file must open with its fields between --- lines")
    end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if not sep or key.strip() not in known:
            raise SystemExit(f"{folder.name}: unknown field line {line!r}")
        fields[key.strip()] = value.strip()
    missing = required - fields.keys()
    if missing:
        raise SystemExit(f"{folder.name}: missing {', '.join(sorted(missing))}")
    return fields, "\n".join(lines[end + 1:])


def render(markdown, base):
    """The body as HTML, its relative links and images made absolute paths:
    a page served without its trailing slash would resolve them a level up."""
    md = MarkdownIt("commonmark", {"html": True, "typographer": False})
    return RELATIVE.sub(lambda m: f'{m[1]}="{base}', md.render(markdown))


# A src, href or poster that names no scheme, root or fragment, in Markdown's
# output and raw HTML alike.
RELATIVE = re.compile(r'\b(src|href|poster)="(?![a-z][a-z0-9+.-]*:|/|#)')


def absolute(body):
    """Root-relative URLs made absolute, for a feed read off the site."""
    return body.replace('src="/', f'src="{SITE}/').replace('href="/', f'href="{SITE}/')


def when(date):
    return f"{date.day} {date:%b %Y}"


STYLE = """
:root {
  --ground: #F5F5F2;
  --ink: #121417;
  --muted: #4A4F57;
  --link: #1F57D6;
  --link-hover: #12399A;
  --rule: #D6D7D2;
  --card: #FBFBF9;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ground: #121417;
    --ink: #F5F5F2;
    --muted: #B4B9C0;
    --link: #8FB0FF;
    --link-hover: #C2D4FF;
    --rule: #2A2E33;
    --card: #181B1F;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 18px;
  line-height: 1.6;
}
header, main, footer { max-width: 720px; margin: 0 auto; padding: 0 16px; }
header { display: flex; align-items: baseline; gap: 14px; padding-top: 28px; padding-bottom: 8px; }
header img { display: block; width: 120px; height: auto; }
.mono, header .section, footer {
  font-family: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas, monospace;
}
header .section { font-size: 15px; color: var(--muted); }
main { padding-top: 32px; padding-bottom: 48px; }
h1 { font-size: clamp(28px, 6vw, 40px); line-height: 1.15; margin: 0 0 8px; }
h2 { font-size: 24px; line-height: 1.25; margin: 40px 0 0; }
h3 { font-size: 20px; margin: 32px 0 0; }
.meta { font-size: 14px; color: var(--muted); margin: 0 0 32px; }
article img, article video { display: block; max-width: 100%; height: auto; margin: 28px auto; border-radius: 4px; }
article pre { overflow-x: auto; padding: 14px 16px; border: 1px solid var(--rule); border-radius: 4px; font-size: 15px; }
article code { font-size: 0.9em; }
article blockquote { margin: 24px 0; padding: 0 0 0 18px; border-left: 3px solid var(--rule); color: var(--muted); }
article hr { border: 0; border-top: 1px solid var(--rule); margin: 40px 0; }
a { color: var(--link); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { color: var(--link-hover); }
ol.posts { list-style: none; margin: 28px 0 0; padding: 0; display: grid; gap: 32px; }
.card {
  display: block; color: inherit; text-decoration: none;
  border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; background: var(--card);
}
.card:focus-visible { outline: 2px solid var(--link); outline-offset: 3px; }
.cover { position: relative; aspect-ratio: 1200 / 630; background: #2A2E33; }
.cover img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
/* The title sits on the picture; the scrim keeps it legible on any of them. */
.cover::after {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(12, 14, 17, 0.85), rgba(12, 14, 17, 0.35) 45%, rgba(12, 14, 17, 0) 72%);
}
.cover .head { position: absolute; left: 0; right: 0; bottom: 0; z-index: 1; padding: 18px 20px; color: #F5F5F2; }
.cover .meta { margin: 0 0 4px; color: rgba(245, 245, 242, 0.82); }
.cover h2 { margin: 0; font-size: clamp(22px, 5vw, 30px); }
.card:hover h2 { text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 4px; }
.brief { margin: 0; padding: 16px 20px 18px; }
footer {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px;
  padding-top: 20px; padding-bottom: 28px;
  border-top: 1px solid var(--rule);
  font-size: 13px; color: var(--muted);
}
"""


def page(title, description, url, image, kind, content, section=("devlog", "/devlog/")):
    e = html.escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{SITE}{url}">
<link rel="alternate" type="application/atom+xml" title="Yasno Games devlog" href="/devlog/feed.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#F5F5F2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121417" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="Yasno Games">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}{url}">
<meta property="og:image" content="{SITE}{image}">
<meta name="twitter:card" content="summary_large_image">
<style>{STYLE}</style>
</head>
<body>
<header>
  <a href="/"><picture>
    <source srcset="/brand/yasno-wordmark-reversed.svg" media="(prefers-color-scheme: dark)">
    <img src="/brand/yasno-wordmark.svg" alt="Yasno" width="120" height="23">
  </picture></a>
  <a class="section" href="{section[1]}">{e(section[0])}</a>
</header>
<main>
{content}
</main>
<footer><span>© 2026 Yasno Games</span><a href="/devlog/feed.xml">feed</a></footer>
</body>
</html>
"""


def post_page(post):
    e = html.escape
    content = f"""<article>
<h1>{e(post.title)}</h1>
<p class="meta mono"><time datetime="{post.date}">{when(post.date)}</time> · {e(post.author)}</p>
{post.body}</article>"""
    return page(f"{post.title} · Yasno Games", post.summary, post.path, post.preview(), "article", content)


def standing_page(pg):
    content = f"<article>\n<h1>{html.escape(pg.title)}</h1>\n{pg.body}</article>"
    return page(f"{pg.title} · Yasno Games", pg.summary, pg.path, pg.preview(), "website", content, (pg.slug, pg.path))


def index_page(posts):
    e = html.escape
    items = "\n".join(
        f"""<li><a class="card" href="{p.path}">
<div class="cover">
<img src="{p.preview()}" alt="" loading="lazy">
<div class="head">
<p class="meta mono"><time datetime="{p.date}">{when(p.date)}</time> · {e(p.author)}</p>
<h2>{e(p.title)}</h2>
</div>
</div>
<p class="brief">{e(p.summary)}</p>
</a></li>"""
        for p in posts
    )
    content = f'<h1>Devlog</h1>\n<ol class="posts">\n{items}\n</ol>' if posts else "<h1>Devlog</h1>\n<p>Nothing posted yet.</p>"
    return page("Devlog · Yasno Games", "What we are making, and how.", "/devlog/", "/og.png", "website", content)


def feed(posts):
    e = html.escape
    updated = f"{posts[0].date}T00:00:00Z" if posts else "2026-01-01T00:00:00Z"
    entries = "\n".join(
        f"""<entry>
<title>{e(p.title)}</title>
<link href="{SITE}{p.path}"/>
<id>{SITE}{p.path}</id>
<published>{p.date}T00:00:00Z</published>
<updated>{p.date}T00:00:00Z</updated>
<author><name>{e(p.author)}</name></author>
<summary>{e(p.summary)}</summary>
<content type="html">{e(absolute(p.body))}</content>
</entry>"""
        for p in posts
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Yasno Games devlog</title>
<link href="{SITE}/devlog/"/>
<link rel="self" href="{SITE}/devlog/feed.xml"/>
<id>{SITE}/devlog/</id>
<updated>{updated}</updated>
<icon>{SITE}/favicon.svg</icon>
{entries}
</feed>
"""


def main():
    folders = sorted(f for f in POSTS.iterdir() if f.is_dir()) if POSTS.is_dir() else []
    posts = sorted((Post(f) for f in folders), key=lambda p: (p.date, p.slug), reverse=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for post in posts:
        out = OUT / post.slug
        shutil.copytree(post.folder, out, ignore=shutil.ignore_patterns("post.md"))
        (out / "index.html").write_text(post_page(post), encoding="utf-8")
    (OUT / "index.html").write_text(index_page(posts), encoding="utf-8")
    (OUT / "feed.xml").write_text(feed(posts), encoding="utf-8")
    print(f"{len(posts)} post(s) -> {OUT.relative_to(ROOT)}")
    pages = [Page(f) for f in sorted(PAGES.iterdir()) if f.is_dir()] if PAGES.is_dir() else []
    for pg in pages:
        out = ROOT / "public" / pg.slug
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(pg.folder, out, ignore=shutil.ignore_patterns("page.md"))
        (out / "index.html").write_text(standing_page(pg), encoding="utf-8")
        print(f"page {pg.slug} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
