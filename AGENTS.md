# AGENTS.md

The studio's site, its brand kit and its devlog. How each is built and
deployed is in `README.md`.

How the devlog and the studio's replies are written (the developer's own
words, Claude's part, the tells, the rules on AI) is
`../internal/studio/devlog.md`, and the research behind it is
`../internal/studio/devlog-community-2026-10.md`. Read the first before
working on a post. It binds.

## A post goes out

1. Claude writes `notes/<slug>/facts.md`: the commits and their dates, the
   numbers as measured, what each render shows, what was cut and the commit
   that cut it, each checked against git or the render. `notes/` sits
   outside `devlog/` because `tools/devlog.py` publishes every file beside a
   `post.md`.
2. The developer writes `devlog/<slug>/post.md` in their own words, `author`
   Yasno Games.
3. Claude edits `post.md` in place: a wrong fact, a typo, grammar, a line a
   reader who was not there could not follow. A claim nothing backs goes to
   `notes/<slug>/review.md` as a flag with the line. Claude generates no
   sentence.
4. The developer reads the post aloud and rewrites whatever they would not
   say.
5. `python -I tools/devlog.py`, commit the post with `public/devlog/`, push.
