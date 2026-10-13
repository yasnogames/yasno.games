# AGENTS.md

The studio's site, its brand kit and its devlog. How each is built and
deployed is in `README.md`.

How the devlog and the studio's replies are written (posts from facts, the
tells to strip, the rules on AI) is `../internal/studio/devlog.md`, and the
research behind it is `../internal/studio/devlog-community-2026-10.md`. Read
the first before drafting a post or a reply. It binds every draft.

## A post goes out

1. The developer gives the facts the post is written from.
2. Claude drafts `devlog/<slug>/post.md` from them and checks it against
   `devlog.md` before showing it.
3. The developer edits it and adds what only they know. Every post's `author`
   is Yasno Games.
4. `python -I tools/devlog.py`, commit the post with `public/devlog/`, push.
