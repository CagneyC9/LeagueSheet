
LeagueSheet — Windows EXE build instructions

Overview
- LeagueSheet is a small Tkinter desktop app that looks up champion cooldowns from Riot's Data Dragon and provides instant autocomplete using a local champion cache.

Goals for packaging
- Produce a single Windows `.exe` (onefile) using PyInstaller so users can download and run without installing Python.
- Ensure the app can update its local champion cache after packaging: the cache is stored in a per-user data folder (`%LOCALAPPDATA%\\LeagueSheet\\champions.txt`) so the bundled EXE remains read-only.

Requirements
- Python 3.8+ (for development)
- Installed packages: see `requirements.txt` (currently only `requests`).
- PyInstaller installed for building the `.exe`.

Quick build (Windows PowerShell)
1. From your development environment, install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

2. Build a single-file windowed exe. This command bundles `champions.txt` (so first-run has an instant local cache):

```powershell
pyinstaller --noconfirm --onefile --windowed --add-data "champions.txt;." LeagueSheet.py
```

**Releasing an Alpha**

- **Local quick build:** run the included PowerShell script from the repo root:

```powershell
.\build.ps1
# or to clean previous artifacts first:
.\build.ps1 -Clean
```

- **Create a GitHub release (automated):** tag a commit with a `vX.Y.Z` tag and push it. A GitHub Actions workflow will run (on Windows), build the exe, and upload `dist\LeagueSheet.exe` as a release asset.

- **Notes:** The build script bundles `champions.txt` from the repo root into the bundle root (so the packaged app can copy it into the per-user cache on first run). You can still build using the older `data/` form (`--add-data "data\\champions.txt;data"`) if your CI or tooling expects that layout.


Notes about the `--add-data` argument
- `--add-data "SRC;DEST"` tells PyInstaller to copy `SRC` into the bundled app at `DEST`.
- On Windows use semicolon `;` as the separator inside the string. The example above bundles the file into the `data` subfolder inside the bundle so the app can copy it to the user data directory on first run.

Where to find the exe
- After the build completes, the single-file exe will be in `dist\\LeagueSheet.exe`.

Preparing a GitHub release (so users can download the exe)
1. Create a GitHub release (tag the commit in your repo).
2. Upload `dist\\LeagueSheet.exe` as a release asset.
3. Update the release notes with the version, OS (Windows), and any usage notes.

Running the exe
- Double-click `LeagueSheet.exe` and the app should start. On first run it copies a bundled `champions.txt` to the user's data directory and uses that for instant autocomplete. The app will also update the champion list from Data Dragon in the background and update the cached file.

Packaging tips to avoid runtime issues
- Keep writable data in the user data dir (the code already uses `%LOCALAPPDATA%\\LeagueSheet\\champions.txt`).
- If you sign the exe (recommended for distribution), sign the generated `LeagueSheet.exe` after building.
- Add a CI workflow (GitHub Actions) to produce builds on tags/releases so you don't have to build locally every time.

If you want, I can also:
- Add a small `build.ps1` script to automate the PyInstaller command.
- Add a GitHub Actions workflow that builds the exe on push/tag and uploads it as a release artifact.
