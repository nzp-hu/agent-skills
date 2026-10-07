---
name: eol-lookup
description: Look up end-of-life and release dates for software products
  offline, from a cached snapshot of endoflife.date. Use for EOL dates,
  support timelines, version lifecycles, and "is X still supported" questions.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/eol.py *)
---

## Workflow

1. Run `python scripts/eol.py list --grep <term>` (term = the user's product
   name, or a keyword from it). Output is JSON lines: slug, title, aliases.
2. Match the user's product to a slug using title and aliases. If multiple
   candidates match, ask the user to pick; never guess.
3. Run `python scripts/eol.py get <slug>` — it prints the product's raw
   YAML frontmatter (release cycles with `releaseDate`, `latest`, `eol`).
   Add `--full` to include the prose body, which often states the release
   policy. Present a readable table to the user.
4. Interpret the data:
   - `eol: false` = the cycle is still supported (no fixed EOL date).
   - `eol: true` = explicitly EOL with no known date.
   - Some products have rolling policies (e.g. Apache Maven maintains the
     two last minor versions): the newest cycles have no fixed EOL; a cycle's
     EOL is typically the release date of the next minor.

## Scripts

- `python scripts/eol.py list --grep PATTERN [--limit N] [--offset N]`
- `python scripts/eol.py get <slug> [--full]`

## Refreshing data

Only when the user explicitly asks for the most up-to-date data.
Fetch the latest `products/*.md` from the endoflife.date repo —
tarball: `https://codeload.github.com/endoflife-date/endoflife.date/tar.gz/refs/heads/master`
— and replace the `products/` directory inside the skill's `assets/`
(the directory containing this SKILL.md; in Claude Code,
`${CLAUDE_SKILL_DIR}/assets/products/`). Untar into `assets/`, never
into `assets/products/` (that nests it as `products/products/`):

    tar -xzf eol.tar.gz -C assets --strip-components=1 endoflife.date-master/products

Check that `assets/products/*.md` exist. Never fetch unprompted.

## Exit codes

- `0` success
- `2` invalid arguments
- `3` slug not found (close candidates listed on stderr) — re-run `list --grep`
- `4` cache empty — run the fetch procedure above, then retry
- `5` frontmatter conventions drifted — `list` is unreliable; fall back to
  raw reads for matching, `get` answers remain valid

stdout carries JSON lines; stderr carries diagnostics.
