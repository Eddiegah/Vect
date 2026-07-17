# How to Record the Demo GIF

The script `scripts/record_demo.py` runs a full simulated REPL session
automatically — all you have to do is record the terminal window.

## Option A — Windows built-in (Xbox Game Bar)

1. Open a terminal in the Vect project folder
2. Make the window a good size: ~90 columns × 40 rows, dark theme
3. Press **Win+G** → click Record button (or Win+Alt+R to start/stop)
4. Run the demo:
   ```
   venv\Scripts\python scripts\record_demo.py
   ```
5. Stop recording when it finishes
6. Convert the `.mp4` to GIF at https://cloudconvert.com/mp4-to-gif
   - Width: 800px, FPS: 12 is enough for terminal content
7. Save as `docs/demo.gif`

## Option B — Terminalizer (best quality)

```powershell
npm install -g terminalizer
terminalizer record docs/demo --skip-sharing
# (runs the demo script manually in the terminal — type: python scripts/record_demo.py)
# Press Ctrl+D when done
terminalizer render docs/demo -o docs/demo.gif
```

## Option C — ScreenToGif (Windows, free)

Download from https://www.screentogif.com
1. Open ScreenToGif → Recorder
2. Position the frame over your terminal
3. Run: `venv\Scripts\python scripts\record_demo.py`
4. Stop recording → Export as GIF → save to `docs/demo.gif`

## After you have demo.gif

Add it to the README right after the badges section:

```markdown
<div align="center">
<img src="docs/demo.gif" alt="Vect REPL demo" width="700"/>
</div>
```

Then commit and push:
```
git add docs/demo.gif README.md
git commit -m "docs: add demo GIF"
git push origin main
```
