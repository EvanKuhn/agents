---
name: journal-entry
description: Create a new, empty journal entry for today in the journal/ directory, from the standard template. Use when the user asks to start, create or add a journal entry.
---

# Creating a journal entry

Each journal entry is its own file in `journal/` at the repository root, named for the day it's
created: `journal/<yyyymmdd>.md`, e.g. `journal/20260923.md`.

## Steps

1. Get today's date from the system clock. Don't rely on your own sense of the date, which can be
   wrong:

   ```bash
   date +%Y%m%d    # for the filename, e.g. 20260923
   date +%Y-%m-%d  # for the file's date line, e.g. 2026-09-23
   ```

2. If `journal/<yyyymmdd>.md` already exists, don't overwrite or change it. Tell the user today's
   entry already exists and give its path.
3. Otherwise, create the `journal/` directory if needed, and write the file with exactly this
   template, filling in the date:

   ```markdown
   # Title
   _yyyy-mm-dd_

   lorem ipsum

   ## Progress
   lorem ipsum

   ## Learnings
   lorem ipsum
   ```

   If the user gave a title for the entry, use it in place of `Title`. Otherwise leave `Title` as
   a placeholder for them to fill in.
4. Don't write any other content. The entry is the user's to write. Reply with the path of the
   new file.
