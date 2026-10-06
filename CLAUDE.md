# Research pipeline: YouTube → NotebookLM

This repo hosts two project skills:

- `.claude/skills/yt-research/` searches YouTube with yt-dlp and returns video metadata.
- `.claude/skills/notebooklm/` is the official skill shipped by
  [notebooklm-py](https://github.com/teng-lin/notebooklm-py) (installed with
  `notebooklm skill install --scope project --target claude`). Don't hand-edit it; reinstall to
  update it.

Dependencies (`requirements.txt`) are installed by the SessionStart hook in `.claude/hooks/`.

## Topic rule

If the user asks for research without a concrete topic (no topic, or a placeholder like
`[YOUR TOPIC]`), **ask what topic they want before running anything**.

## End-to-end flow

When asked to find videos and send them to NotebookLM for analysis/deliverables:

1. **Search**: run `yt-research` (for "latest trending", use `--sort views --period week`). Save
   the results to `research/<slug>-videos.json` and show the table.
2. **Notebook**: `notebooklm create "YT Research: <topic> (<date>)" --json` → keep `.notebook.id`.
3. **Sources**: for each URL, run
   `notebooklm source add <url> --type youtube -n <nb> --json` and keep every `.source.id`. Then
   run `notebooklm source wait <src> -n <nb> --timeout 600`. Report any source that ends in `error`
   (e.g. no captions or age-restricted) and continue with the ready ones.
4. **Analysis**: `notebooklm ask "<analysis prompt>" -n <nb> --json`. Relay the answer with its
   citations mapped back to video titles. Save it to `research/<slug>-analysis.md`.
5. **Deliverables**: `notebooklm generate <type> "<description>" -n <nb> --json` → `.task_id`, then
   `notebooklm artifact wait <id> -n <nb> --timeout 1200`, then
   `notebooklm download <type> research/<file> -a <id> -n <nb>`.
   - Infographic: there is no "chalkboard" preset. For a handwritten or chalkboard look, use
     `--style sketch-note` and write the look into the description, e.g. "hand-drawn chalk on a
     dark green chalkboard, handwritten lettering, chalk doodles".
   - Slide deck: `generate slide-deck` (`--format detailed|presenter`), download as PDF or PPTX.
   - Flashcards: `generate flashcards` (`--quantity`, `--difficulty`).

A single request for this whole flow authorizes its waits, its generation steps and its downloads
into `research/`.

## Auth

`notebooklm login` opens a browser, so it must be run by the user on a machine with a browser.
Check with `notebooklm auth check --test --passive --json`. Never print or commit
`~/.notebooklm/**` or any `storage_state.json` / `master_token.json`.
