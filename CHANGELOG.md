# Changelog

**English** · [Deutsch](CHANGELOG.de.md)

All notable changes to this project are documented here.

The project follows SemVer: `MAJOR.MINOR.PATCH`.

## Unreleased

> Collects until the next release day (Saturdays).

## v3.0.0 - 2026-08-29

> **One window for everything.** The blueprint list and the settings used to live in
> two separate windows, and you had to know which one held what. They are now together —
> tabs on the left, a visible folder for your files, and an installer instead of
> dragging a file somewhere by hand.

### The short version

- **An installer for Windows** — download, run, done. No more moving files around.
- **One window instead of two**, with tabs on the left. Plus a tray icon to bring
  it back whenever you need it.
- **The overlay can step aside** and only appears when something is found — a
  narrow green strip stays at the edge, and the mouse brings it back.
- **Self-update now works on Linux too.** It used to fail there **every single
  time**; anyone on the AppImage had to fetch each version by hand.
- **Star Citizen can be launched from the tool**, and a diagnostic report collects
  everything a bug report needs at the press of a button — no names, no paths.

### Upgrading from v2.0.0

- **Your blueprint collection moves along by itself.** It used to sit hidden in
  `%APPDATA%`, now it lives visibly in `Documents\SC BP Watcher`. On the first
  start it is **copied**, not moved — the old folder stays untouched in case
  something is missing after all.
- **For this one update, use the setup rather than the button in the program.**
  The button works, but it still runs v2.0.0's update path — and on Windows
  that leaves a console window sitting there until you quit the program. A bug
  in the update path cannot fix itself; from v3.0.0 on it is sorted and the
  button is enough.
- **If you put the `.exe` somewhere by hand, delete it after installing.** The
  setup places the program in `%LOCALAPPDATA%\Programs\SC BP Watcher`. The old
  file would otherwise stay behind, and one day you would start the old version
  by accident.
- **On Linux there is nothing to do** — the AppImage replaces itself.

### Added

- **A button for „just give me the latest".** Until now you first had to
  understand what a channel is and pick the right one of the two boxes — anyone
  choosing the wrong one was offered nothing at all. There is now a full-width
  button above them that immediately fetches whatever is available, including a
  test build. It changes nothing about the setting below. Suggested by der Autor
  after Morkhan got stuck at exactly this point.

- **Star Citizen can be launched from the tool.** The „In-game details" page
  has a button that starts the game the way you already do: the RSI Launcher on
  Windows, `lug-helper` on Linux. If neither is found the button does not appear
  at all — anyone using a different route (Lutris, Heroic) sets `spielstarter`
  in the settings file. Suggested by Morkhan.

- **The mouse brings the overlay back.** In pop-up mode just move to where it sits — it
  reappears by itself and stays as long as the pointer is on it. Previously you had to
  restart the program for that, which no other overlay asks of you.

- **Restart right after an update.** It used to say „the new version runs on next start" —
  you had to quit and start it yourself. The fetch button now turns into **„⟳ Restart now"**
  once the download is done. The single-instance guard is closed first, otherwise the new
  copy would think it is the second one and quit immediately.

- **Start trace in the problem report.** A crash ends the program instantly — no report gets
  written, and all that remains is „it crashes". Every startup step is now written straight
  to disk; the last line in the report shows how far it got.

- **Get a release straight from the window.** Under each of the two cards („Stable
  releases only" / „Test builds too") there is a full-width button that downloads and
  installs the latest release of that channel — including going back from a test build to
  the last stable one.

- **Application menu entry (Linux).** The wizard offers it at the end, the settings any
  time. On Windows the installer handles this — on Linux the AppImage sat in the downloads
  folder and appeared in no menu. You can also put a keyboard shortcut on the entry to
  bring the overlay back.
- **Notification area icon (Windows).** Left click brings the window back, right click
  opens a small menu. The switch for it was already in the settings; the icon itself never
  existed.

- **The overlay can hold back.** Now selectable: permanently visible as before, or only
  popping up briefly when a blueprint actually arrives. You bring it back by starting the
  program again — you can put a system keyboard shortcut on the shortcut. Suggested by
  Haldjas (pr0citizen): „when I get into the overlay with my mouse during combat, that
  will be unpleasant."
- **Mouse clicks can be passed through to the game.** The overlay stays visible but no
  longer catches clicks. On Windows via `WS_EX_TRANSPARENT`, on Linux via the XShape
  extension; under native Wayland it is not possible, and the setting says so instead of
  showing a switch that does nothing.
- **Starting the program a second time no longer opens a second copy** — it brings the
  running one to the front.

- **One window with tabs.** Blueprints on top, settings below, and everything only
  advanced users need collapsed at the bottom. The overlay stays as small as before; this
  window is what opens behind it.
- **An installer for Windows.** Start menu entry, optional desktop icon, optional
  autostart — and a proper uninstall. If you would rather not install anything, the plain
  `.exe` is still in the release.
- **Your files are now visible** under `Documents\SC BP Watcher`, split into blueprints,
  exports, settings and diagnostics. They used to sit hidden in the system — nobody looks
  there for their blueprint inventory. On first start they are **copied**, the old folder
  stays as a way back.
- **Import an existing inventory** — from the KRT Profit Basetool, from scmdb.net, from
  the launcher file or from your own backup. The format is recognised by its content, you
  just pick a file. Merged, never replaced.
- **Report a problem with one click.** "Report a problem" opens a pre-filled form; all
  you add is what happened. The report contains no names and no paths with your user name.
- **Test versions on request.** If you want to help checking, turn them on under *About*
  and get new versions before everyone else — through the same update notice.
- **Text size in four steps**, affecting text, icons and buttons alike.
- **Where blueprints without a contract come from.** 55 blueprints are not handed out by
  any regular contract — they come from named pools such as XenoThreat, RDC-Boss or
  RedWind. Instead of a question mark the source is shown, and you can filter by it.
- **What's new** as its own tab, split into new, improved and fixed.
- **Starter blueprints** are detected and entered — the eight everyone has from the
  start, marked with ◆.
- **Export your inventory** in three formats: KRT Profit Basetool, scmdb.net and a full
  backup.

### Changed

- **„No release known yet" sounded like an error.** The button did not say what
  to do — it now reads „Press ‚Check now' above first". And the „Finished
  versions only" box is marked „recommended", so nobody has to guess what to
  pick. Both came up during Morkhan's test.

- **The tab is now called „Update & About".** Nobody looking for an update finds
  it under „About" — not even the author looked there.

- **The „launch Star Citizen" button sat where nobody would look for it.** It
  was on the „In-game details" page, which is about mission text — even the
  author could not find it again. It now sits as a green „▶" in the overlay's
  top bar with the other icons: anyone who wants to start the game does not have
  the main window open anyway. Hovering it explains what the click does.

- **You are asked before a translation is installed.** „German" and
  „StarStrings" replace the game’s text file completely — after that the whole
  game is in that language, not just the blueprint details. That was documented
  nowhere; now the help text says so, and a prompt appears before the first
  install. Confirmed once, it does not ask again. „Original" does not ask,
  because it does not change the language.

- **In pop-up mode the overlay leaves a narrow green strip behind.** Hover it and the
  overlay is back. The first attempt polled the mouse position — which cannot work under
  Wayland: measured, Tk reported the same coordinates twelve times in a row while the mouse
  moved across the screen. An application only learns the pointer position there while it is
  over one of **its own** windows. The strip is such a window — and it is more honest than
  an invisible magic zone: you can see where the overlay is waiting.

- **The problem report says which version an error came from** — and marks those from an
  older one. The store keeps the last ten across restarts; after an update it listed errors
  that had long been fixed, making the report look like nothing worked.

- **Up to twelve sources per blueprint** instead of three. Measured: more than half of
  all blueprints had sources cut off before. The easiest route is still shown first, the
  rest unfolds.
- **The source details appear on click** and can be closed again — in a small window they
  used to eat a third of the list.
- **Filter by type, class, size, grade and source**, on top of search and the
  "watched / owned / still missing" lists.
- **Collapse the overlay** (▾): it folds into its title bar.
- **No more save button** — changes take effect right away.

### Fixed

- **The overlay stayed German when you switched to English.** Changing the
  language gave you an English window and a German status bar:
  „8 Baupläne · Log ✓ · ohne Launcher · geprüft", plus the waiting message and
  the autostart text. English versions of those strings had existed all along —
  nobody used them, the code kept assembling the German ones. On top of that
  the overlay never heard about a language change at all; only the settings
  window relabelled itself. Reported by der Autor.

- **The hint on the ▶ launch button overwrote the status bar.** It was the only
  one of the ten icons without a tooltip; instead it wrote into the status bar
  and afterwards restored a value that was never kept up to date — so a
  blueprint message was gone after the mouse passed over the icon.
  Reported by der Autor.

- **The logo was missing from the finished build.** On „Update & About" the
  program loaded `assets/xharig.png`, but the build never packed that file — it
  never showed when starting from source, where the file is present. Reported by
  der Autor, who spotted it in a tester's screenshot.

- **The „ⓘ" on the overlay opened a separate window with its own update logic** —
  and that one had no restart button. Anyone going that way downloaded the new
  version and was then left with a sentence instead of a button. It now opens the
  main window on „What's new", with the „Update & About" tab right beside it.
  **One route instead of two.** Reported by Morkhan.
- **Stretched buttons only filled half the width.** Mostly affected the buttons
  below the two update boxes. Reported by Morkhan.

- **Updating through the info window never arrived.** Anyone using the green
  „ⓘ" on the overlay instead of the settings page only got the line „the new
  version runs on next start" — **and no button for it**. On Windows that line
  is not even true: a helper script only swaps the file once the program has
  quit, and gives up after two minutes. Anyone who kept playing ended up with no
  update at all. The same „⟳ Restart now" button as in the settings is now
  there. Reported by Morkhan.
- **A console window flashed up briefly during updates.** The helper script has
  run invisibly since v3.0.0 — the `taskkill` before it, which clears away an
  already running script, was overlooked. Reported by Morkhan.

- **Five failures used to happen silently.** If the settings, the watchlist, the
  „new" markers, the autostart entry or a saved report could not be written,
  nothing happened at all — the setting was simply back to its old value after a
  restart, and the error report said nothing. Those places now report.

- **The error report left the game language empty.** It showed only a dash even
  though detection worked perfectly — the query returned two values, the report
  expected one, and the error was swallowed silently. It now states what is being
  searched for in the log **and where the wording comes from**: the game's
  `global.ini` or the built-in table. That is the first question whenever someone
  says „it doesn't detect my blueprints".
- **Truncated descriptions in three places.** On a narrow window a few pixels
  were missing and the last characters fell off. Affected were the update
  channels, „Write details into mission text" and „How often to look".

- **The setup wizard did not remember the chosen text source.** It fetched and
  installed the texts but never stored the choice — afterwards none of the three
  sources was selected under „In-game details". Reported by Haldjas.
- **Updating on Windows spawned console windows.** The helper script that
  swaps the running `.exe` looped forever while the file was locked — and it
  stays locked until the program quits. Every further click on „get" started
  another window. It now gives up after two minutes, stays invisible, and an
  already running helper is stopped first.
- **„Check now" did not check.** The button showed „Looking for a new version …" and did
  nothing else. Anyone with a stale cache could not get out of it — one tester was still
  offered rc12 while running rc18. It now really asks, reports the result and updates the
  display.
- **Self-update took the Windows path on Linux** and reported „[Errno 2] No such file or
  directory: 'cmd'". The guard against foreign programs compared our own code against
  `APPDIR` — but PyInstaller extracts into a directory of its own, so the comparison always
  failed. The filename decides now.
- **Self-update could have overwritten other programs.** It treated any file the `APPIMAGE`
  environment variable pointed at as its own — and that variable is set in **every** program
  started from an AppImage. Now our own code must come from the matching `APPDIR`, and a
  second guard rejects any target whose filename does not belong to this program.
- **Self-update always failed on Linux.** The download went to `/tmp` and was installed
  with `os.replace()` — and on virtually every Linux `/tmp` is a separate filesystem.
  `os.replace` cannot move across filesystems; it ends in „[Errno 18] Invalid cross-device
  link". The comment in the code always promised „next to the running program" — now the
  code does too, and installing became atomic along the way.
- **Crash on the very first start** (`SIGSEGV`), reported by Bomb20. The wizard created its
  **own** Tk instance and destroyed it at the end; the overlay then created a second one.
  After the first is destroyed, fonts, images and pending callbacks live on pointing at a
  dead interpreter — whether that goes well is a matter of timing. His „it ran fine with
  debugging on" is the fingerprint of exactly that. There is now only **one** Tk instance in
  the whole program.
- **The `[SCBPW]` markers were visible in game.** The contract title read „Security
  Patrol**[SCBPW]** [BP 3/6]**[/SCBPW]**". They made sure inserted text could be removed
  exactly — but nobody wants to read that in their game. There is no marker in the text at
  all now: the **wording before the insertion** is remembered, and removing restores it.
  That is more precise than before. Verified with `tools/injektion_pruefen.py` against the
  real file: inserting and removing leaves all 743 passages character-for-character as they
  were.
- **In game only the number showed, not which blueprints.** A contract has one title but
  often a dozen descriptions — one for „to the ruin station", one for „to the distribution
  centre" and so on. The contract data names only **one** of them; the rest stayed empty.
  The title said „[BP 0/12]", and anyone opening the description to see *which* twelve
  found nothing. Measured: 51 Covalex descriptions in the game, 7 of them with details.
  They are now filled via the shared key prefix.
- **„Personal weapon" and „FPS weapon" were two groups for the same thing** — 87 under one
  key, two under the other.
- **„Rows in the overlay" had no effect.** The setting was saved and never read; the
  overlay used a fixed 200. The configured value now applies, with 20 as the default — no
  one collects 200 blueprints in one session anyway.
- **„Browse" opened no dialog** — neither for the Star Citizen folder nor for your own
  files. Both do now, and on Linux with the system's dialog instead of Tk's grey one.
- **The last blueprints in the list overlapped.** X11 uses 16-bit window coordinates; all
  722 in one frame come to about 33000 pixels, putting 16 rows past the limit. The list is
  now shown in blocks when needed — nothing is hidden.
- **The scrollbar could not be grabbed.** The handle was drawn with a minimum height but
  tested against the calculated one — hitting its lower half counted as „beside it".
- **The window started off-screen.** With no remembered position Tk placed it at `+0+0`;
  with a portrait monitor on the left there is no picture there. Startup and „Reset window
  position" now centre it on the main screen.
- **Autostart was out of sync between overlay and settings.** Both read their state only
  when drawn.
- **The window icon was missing from every finished build** — on both systems. The file
  was not shipped with the program at all.

### Thanks

This release owes a great deal to two testers who took the trouble not just to
notice problems, but to describe them precisely enough to be found:

- **Haldjas** (pr0citizen) — the pop-up mode suggestion; plus the setup that
  failed on the running file, the console windows during updates, the missing
  tray icon, the crash after restarting, the font size that never reached the
  overlay, the text source the wizard forgot — and the observation that
  explained everything: „it stays on rc25".
- **Bomb20** (SC4M) — the crash on the very first start (a bug only new users
  would ever have hit), the „check now" button that did nothing, and the note
  that the „German" text source translates the entire game.
- **Morkhan** (KRT) — the suggestion to launch Star Citizen straight from
  the tool.

The blueprint details are based on the openly published contract data of the
**SC Deutsch Launcher team** and on **scmdb.net**.

## v2.0.0 - 2026-08-24

**The Windows overlay has become a standalone tool for Windows and Linux — and on
request it writes blueprint details straight into the game.**

The SC Deutsch Launcher is no longer required. Verified against a real Star Citizen
installation, with both a German **and** an English client.

### Without the launcher

- **`Game.log` is the source.** Your collection is maintained by the tool itself; on
  first start the stored session logs are read. If a gap remains, the tool says so
  instead of presenting an incomplete list as complete.
- **The game language works itself out.** The in-game blueprint message is localised;
  the tool derives the wording from your own logs — it knows over 700 blueprint names,
  and where one appears in a log line, the text before it is the phrase. German and
  English are measured; other languages it figures out by itself.
- **If the launcher is present it is still used** — including when it sits on a mounted
  Windows drive, which is the normal case on dual-boot systems.

### Blueprint list

- **Every blueprint to look up**, with search, filters and progress. Search covers name,
  category, class (`military`, `stealth`, `civilian`, …), manufacturer and grade.
- **Where each blueprint comes from** — faction, contract, required standing, payout
  **and where the contract can be picked up**.
- **Four sections** to show and hide: ship parts, FPS weapons, armor & clothing, other.
  Ordered by section rather than alphabetically.
- **Watchlist by click.** When a watched blueprint shows up the tool says so loudly —
  and removes the fulfilled wish by itself.

### Blueprint details in game

- **Every contract that awards blueprints** gets the list inside its mission text — with
  tick boxes: ticked for what you own, empty for what you lack. Plus a marker in the
  title (`[BP 2/3]`), visible in the contract list itself. **681 text spots**, German and
  English.
- **Three ways to get the base text:** the German translation by
  [rjcncpt](https://github.com/rjcncpt/StarCitizen-Deutsch-INI),
  [StarStrings](https://github.com/MrKraken/StarStrings) by MrKraken — or the English
  originals from your own `Data.p4k`, with no download at all.
- **Undo is byte-exact.** StarStrings users keep it: its markup stays, ours is added.
- You are **asked**, never surprised. Nothing is preselected.
- **It stays current by itself.** On startup and every six hours after, the tool checks
  for a newer translation, newer blueprint data — or a `global.ini` that a game patch
  has replaced. All three are re-applied automatically.
  - **Why this is not a nicety:** every translation update and every patch rewrites the
    file, so the details are simply **gone** — and after a patch, contracts award
    different blueprints. Neither is noticeable, because the game runs fine either way.
    Without this check you eventually play on wrong data.
  - Only what the player set up themselves is ever touched.

### Using it

- **Setup wizard** in five steps, repeatable at any time — and a **settings window** for
  everything at once.
- **German and English**, switchable, effective immediately.
- Hover explanations on every icon, adjustable opacity (which matters with a single
  screen), sound, autostart.
- **Update notice with a version history** — including releases you skipped.

### Distribution

- **Ready-made files for both systems**, built by GitHub on every version tag. The
  AppImage is built in an Ubuntu 22.04 container so it starts on common systems.
- ⚠️ **Important for Arch, Fedora and openSUSE:** that same container was also a trap.
  The bundled Python looked for its certificate store under the Ubuntu path
  `/usr/lib/ssl`, which does not exist there — **every** HTTPS connection failed
  silently. No blueprint catalogue, no translation, no update notice; the program
  started but could load nothing. The launcher now looks for the store in all the usual
  places. On Ubuntu and Debian this never showed up.
- **Nothing third-party is bundled.** The blueprint catalogue (scmdb), the translation
  and StarStrings are fetched at runtime, from their own addresses, on your machine.

### Thanks

The in-game blueprint details build on the openly published contract data of the
**SC Deutsch Launcher team** (813 contracts, German and English) and on **scmdb.net**.
Without either, this release would not exist.

## v2.0.0-rc1 - 2026-08-24

> **A pre-release for testing.** Feature-complete and thoroughly tested, but never
> yet run against a real Star Citizen installation other than the author's — that
> is what testers help with. Feedback welcome as an [issue](../../issues).

**The Windows overlay has become a standalone tool for Windows and Linux.** The
SC Deutsch Launcher is no longer required, the blueprint inventory is kept by the
tool itself, and for most blueprints it now says where to get them.

### Added

- **Runs on Linux.** One codebase for both systems, not a second branch. Where files live is decided in one place (`scbp/pfade.py`): `%APPDATA%` and `C:\Program Files` on Windows, `~/.config` and the Wine prefix on Linux (searched where lug-helper, Lutris, Bottles and Heroic put their installations).
- **Its own blueprint inventory** (`bestand.json`), with a note where each entry came from. Written via a temporary file and a rename, so a crash mid-write cannot corrupt it; the previous state is kept as a backup.
- **Catch-up on start.** The stored logs of earlier sessions are read and quietly added — nothing is lost if you played without the watcher running. On the very first start the *current* log is read from the beginning too, otherwise the session in progress would be the one gap.
- **An honest gap notice.** If the stored logs do not reach back to the last known state, the watcher says so as its own line (ℹ) instead of passing off an incomplete list as your inventory. That is what the tick-off list is for.
- **Blueprint catalogue with origins** (`scbp/katalog.py`). 714 blueprints; for 655 of them it lists faction, contract, required standing with reputation points, payout in aUEC and reputation gain — sorted by the easiest route, at most three sources each. The 12 MB source dump is not kept but boiled down to 347 KB, fetched once per game version with retries.
- **Management window** (`scbp/bestandsfenster.py`): searchable list grouped by type, filters *all / owned / missing*, progress count, tick entries with a click, expand origins with a click.
- **Watchlist by click** (`scbp/merkliste.py`). The star turns any entry into a wish — when it appears the watcher announces it in gold. **Fulfilled wishes remove themselves** once the blueprint reaches your inventory. Externally added patterns keep working.
- **Setup wizard** (`scbp/assistent.py`) — four steps, **repeatable at any time** from the title bar. Language, finding Star Citizen (with a browse button and validation *as you type* — any level works, even the `Game.log` itself), collecting past blueprints, done. Repeatability is deliberate: someone who is not comfortable with computers should be able to redo something without knowing which menu it hides in.
- **German and English, switchable** (`scbp/sprache.py`). The default follows the system, but the `sprache` field in `einstellungen.json` overrides it — running an English system and still wanting to read German is a legitimate choice. Switching takes effect immediately.
- **The tool works out the in-game language by itself.** The blueprint message in the log is localised; only the German wording had ever been measured, the English ones were guesses and other languages were not covered at all. It now derives the phrase from your own logs: it knows over 700 blueprint names — if a log line contains one, the text in front of it is the phrase. Two distinct matches are required so coincidence is ruled out. Verified against an invented French build.
- **Update notice and version history** (`scbp/aktualisierung.py`, `scbp/versionsfenster.py`). The tool checks at most once a day; when something new exists, ⓘ in the title bar turns green. Behind it is the version history — **including older releases**, so you can read what you skipped. Downloads come from `github.com` only; anything else is refused.
- **Ready-made files for both systems, built by GitHub** on every version tag. The Linux build runs in an Ubuntu 22.04 container (glibc 2.35) — built against a newer glibc it would not start on common systems at all. The build aborts if the tag and `__version__` disagree.
- **Own paths can be entered** (`einstellungen.json`), and the file is created automatically with the searched locations listed next to each field. Check interval and sound are configurable too.
- **Start script for Linux** (`SC-BP-Watcher starten.sh`), which checks for `tkinter` first and names the right package per distribution.
- **Self-test** (`tools/selbsttest.py`) that reconstructs an installation in a throwaway folder and works through the known pitfalls.
- **Project page in English and German** — English is the default page, German is one click away at the top.

### Fixed

- **The watcher would have crashed on start under Linux.** The `size_nw_se` mouse cursor on the resize handle only exists on Windows; elsewhere Tk raises an error before the window ever appears.
- **Window position from someone else's machine.** The remembered position was applied unchecked. On a machine with a different monitor setup the window sat outside every screen — invisible, and on macOS it took the program down with it. It is now checked for plausibility, and the built-in default carries **no position at all**, only a size. Where the overlay belongs is something everyone drags into place themselves.
- **Endless loop without the launcher.** On start the watcher waited until the launcher file became readable — without a launcher, forever. Under Linux it would never have come up.
- **The catalogue watch did nothing without the launcher.** "What became newly craftable" depended on a launcher file. Without it, the scmdb data now takes over.
- **Sound without `winsound`.** That module does not exist on Linux; tkinter rings the bell there instead.

### Changed

- **The status line shows your own inventory**, not the launcher's count, and whether it is working with or without the launcher. Reason: the launcher demonstrably counts too low — the P4-AR Rifle is missing from it although the Fabricator lists it as owned. Starter blueprints were never "received" and appear in no log. Its number is a lower bound, not an inventory.
- **The SC Deutsch Launcher is optional.** If present it still confirms finds (🟡 → 🟢) and supplies its maintained catalogue. Without it only that falls away — the log is the actual source either way.
- **Starting no longer requires the launcher file**, only that Star Citizen itself is found. If it is not, the wizard **asks** — instead of showing a message and quitting, which would have meant editing a JSON file by hand and restarting. Nobody does that.
- **Brand colour** moved to `#9ce430`; the overlay was still running on the pre-logo-change green.

### Removed

- **The "build the EXE yourself" script.** Since GitHub builds the files, nobody needs it — and it had already gone stale: built without `--add-data`, the resulting executable would have had neither the changelog nor the catalogue data.

## v1.5.0 - 2026-08-11

### Added

- **Value fallback via scmdb.net.** When the launcher catalogue does not know an item, the watcher now takes type, size, grade, class and manufacturer from scmdb's crafting data (`versions.json` → `crafting_items-<version>.json`). Blueprints missing from the catalogue finally get a tag too — QuadraCell, FR-66 and the skin variants among them. Plain `urllib` from the standard library, no extra package.
  - Cached locally; refetched only when a **new game version** appears (checked every 6 hours).
  - Without a connection the last state applies, without a cache everything behaves as before v1.5.0 — the watcher never aborts over it.
  - Can be switched off with `SC_BP_NO_NET=1`.
- **Start with Windows — voluntarily.** New `⏻` switch in the title bar (green = on, grey = off). It adds or removes an entry under `HKCU\…\CurrentVersion\Run`. Nothing is enabled without asking, and the state lives only in the registry — there is no second source of truth to drift apart from.
  - Started from source it registers `pythonw.exe`, not `python.exe`: otherwise a console window would sit open after every login and steal focus from the game.
- **New app icon.** Dark round emblem in Xharig green: segmented scanner ring, blueprint sheet with a cube, horizontal scan beam. Built from two artworks — a detailed one from 40 pixels up and a **simplified one for 16–32 pixels** (solid cube instead of wireframe, no corner brackets). A single motif across all sizes would have turned to mush when small.

### Worth knowing

- **Order of precedence:** `bp-overrides.json` → launcher catalogue / game data → scmdb. scmdb only fills gaps and never overrides. Reason: a comparison against 56 messages from the game log produced **55 exact matches** on size, grade and class — but for the *Elsen* cooler scmdb says grade A while both the game log *and* `components.ini` agree on B (the manufacturer is wrong there too). An excellent source, but not an infallible one.
- **The scmdb data is deliberately NOT bundled.** It is fetched on the user's machine directly from scmdb.net, the way a browser would. scmdb is licensed CC BY-NC-ND 4.0; shipping a copy would be redistribution and would conflict with that licence as well as this project's GPL. Requests carry an honest identifier so the operator can see who is asking.
- **Armour and FPS weapons still get no tag.** scmdb assigns `size` and `grade` to every item, helmets included — taken at face value, every piece of armour would carry an invented "Grade A, Size 1". Class and grade are therefore only used when scmdb lists a `componentClass` (actual ship components); ship weapons get size only.

## v1.4.0 - 2026-08-02

### Changed

- **Licence changed from MIT to GNU GPL v3.0** (version 3 only, `SPDX-License-Identifier: GPL-3.0-only`). The source is being opened: a single public repository instead of the planned split into a private source and a public distribution repository. The GPL lets anyone use and modify the code, but requires the source to come along under the same licence when distributed.
- `README.md`: new **"Star Citizen Fan Content"** section with the wording required by RSI and a link to the official page — a prerequisite for public distribution.

### Fixed

- **Hard-coded local path removed.** `OVERRIDES_FILE` pointed at a directory that only exists on the developer's machine — for everybody else it led nowhere, and opening the source would have made the path public. The optional overrides file is now looked for in the user's own folder; a different location can be given via `SC_BP_OVERRIDES`. With neither, the launcher catalogue applies unchanged.

## v1.3.0 - 2026-07-31

### Added

- **Catalogue watch — reports what became NEWLY craftable in the game.** Until now the watcher only reported what *you* unlocked. It now also keeps an eye on `bp_item_types.json`, the list of everything that has a blueprint at all. The SC Deutsch Launcher refreshes it with each patch; when something is added it appears as 🔵 **newly craftable**. That way you notice when CIG adds an item that simply had no blueprint before.
- **Watchlist for wanted items:** if `watchlist.json` exists, matches from it are announced prominently in gold with ⭐ and their own sound (`<title> — now craftable!`). Format: `{"eintraege": [{"titel": "…", "muster": ["substring", …]}]}`, patterns lowercase, matched as substrings. Without the file the watcher simply reports every addition.
- The comparison state lives in `catalog-seen.json` and **survives restarts** — otherwise half the catalogue would arrive as "new" after every start. The very first start only establishes the baseline and reports nothing.

### Fixed

- **Widening the window did nothing:** the list width was hard-coded at `312` pixels. Dragging the window wider still gave you the same narrow content — long blueprint names stayed cut off. The list now follows every resize; long subtitles wrap instead of disappearing off the edge.
- **Default size** raised from `341x1098` to `440x1098` (the right edge stays put) so the longer catalogue-watch messages fit without wrapping.

### Notes

- The catalogue file is read only **once a minute**, and even then only if its timestamp changed — it only ever changes with patches.
- Catalogue lines are notifications only: they are never confirmed to 🟢, because they have nothing to do with your own unlocks.
- The watcher keeps its catalogue state in a **separate** file — so a second tool working on the same data cannot steal its notification.

## v1.2.0 - 2026-07-30

### Added

- **Instant reporting from `Game.log`:** the watcher now reads Star Citizen's log itself and shows a new blueprint **within seconds** instead of waiting for the launcher's export. Background: the SC Deutsch Launcher rewrites `sc_bp_erledigt.json` only every few minutes — measured on 2026-07-30, **2.5 minutes** passed between the unlock in game (21:23:49) and the launcher export (21:26:24). Reading the log closes exactly that gap.
- **Two-stage display:** blueprints freshly read from the log appear as 🟡 **provisional**; once the launcher catches up, the line is confirmed to 🟢 and refreshed with its data. The launcher file remains the authoritative source — type, size, grade and class still come from its catalogue.
- **Name matching between log and launcher:** ship components appear in the log with a suffix (`7CA 'Nargun' (Civ/3/A)`) and without it in the launcher — the suffix is stripped (and doubles as a fallback for the `M/A/1` tag if an item is not yet in the catalogue after a patch). Genuine name brackets such as `(30 cap)` or `Singe Cannon (S2)` are left alone. Where translations differ (seen: `(12 Schuss)` in the log versus `(12 cap)` in the launcher), a fallback match without the bracket applies — but only when it is unambiguous. Verified against all 127 stored log backups: 148 blueprint messages, 147 exact matches, the remaining one via the fallback.
- **Automatic log discovery** and detection of a game restart (rotated log).
- **Status line** now also shows whether the log is being read.

### Fixed

- **"Newest on top" never worked:** new lines were inserted using `winfo_children()` — that is the order of *creation*, not the order in the window. From the third entry on, every new arrival ended up **below** the older ones. `pack_slaves()` is used now.
- **`MAX_ROWS` had no effect:** the setting was documented in the README but never applied in the code — the list grew without limit. The oldest lines beyond `MAX_ROWS` (default 200) are now dropped.
- **Type lookup refreshes itself:** if a just-unlocked item is not yet in `bp_item_types.json`, the file is reloaded once instead of immediately showing `—`.

### Notes

- Log reading recognises the **German** in-game message. With another game language it does not apply — the tool then behaves as before. *(Resolved in v2.0.0: the wording is now worked out automatically.)*
- Still read-only: `Game.log` is only ever read, never modified.

## v1.1.0 - 2026-07-19

### Added

- **Size / grade / class per blueprint** as a compact `class/grade/size` tag, e.g. `M/A/1` (Military · Grade A · Size 1). Letters: **M** Military, **S** Stealth, **I** Industrial, **C** Civilian, **K** Competition. Ship weapons only have a size → `–/–/2`; FPS weapons and armour have none of it → no tag. Data from the launcher catalogue plus manual corrections from `bp-overrides.json` (which take precedence).
- **The window remembers position and size:** on moving, resizing and closing, the geometry is saved and restored on the next start.

### Changed

- **Default start position** is now the upper monitor rather than the gaming monitor, so you no longer tab out of Star Citizen by accident. *(Removed again in v2.0.0 — a fixed position from someone else's setup is invisible on yours.)*

## v1.0.3 - 2026-06-29

### Added

- **GitHub release** with the finished `SC-BP-Watcher.exe` attached — download, double-click, done (no Python, no building it yourself)

### Changed

- README: "download the ready-made `.exe`" is now the **recommended** way to start

## v1.0.2 - 2026-06-29

### Added

- **App icon** in the Xharig style (dark background, Xharig green, scope ring with a "new" dot) — `icon.ico` for the executable, `assets/icon.png` as a preview
- The executable is now built with the icon
- The window and taskbar icon is also set when starting from source
- Reproducible icon generator (needs Pillow, which the tool itself does not)

## v1.0.1 - 2026-06-29

### Added

- **Thanks and credits** to the SC Deutsch Launcher (the tool's data source at the time), including a note that SC BP Watcher is an independent, unofficial companion tool
- Official link to the **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)**

### Changed

- The mandatory prerequisite (SC Deutsch Launcher) highlighted at the top of the README

## v1.0.0 - 2026-06-29

First release.

### Added

- Live overlay (borderless, always on top, translucent) showing new Star Citizen blueprints in real time
- Background monitoring of `sc_bp_erledigt.json` (3-second interval, its own thread)
- Per arrival: 🟢 name · type · time, newest on top
- Sound on every new blueprint
- Window movable (title bar) and resizable (◢ handle), clear the list (🗑), close (✕)
- Type shown in whichever language the source provides
- Automatic path discovery
- Start via a batch file (no console window) or as a standalone executable
