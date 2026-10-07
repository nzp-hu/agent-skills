# eol-lookup

An agent skill for looking up end-of-life (EOL) and release dates for
software products **offline**, from a cached snapshot of
[endoflife.date](https://endoflife.date). \
Tested with OpenCode and Claude Code.

Your agent will need to grab the data and cache it the first run. (Detailed in the skill.)

## Layout

    SKILL.md            skill definition + agent workflow
    scripts/eol.py      lookup CLI (Python 3.10+, no dependencies)
    assets/products/    cached product data (gitignored — fetched at setup)

## Requirements

- Python 3.10+
- `curl` and `tar` (or equivalent) for the one-time data fetch

## Setup

Ask your agent to set it up for you and give it the URL of this repo. \
If it does not automatically grab the data, ask it to refresh the end of life data.

## Why not just use the API?

I work offline with local agents as well, so I appreciate the lack of network requirement.
