# Changelog

**English** · [Deutsch](CHANGELOG.de.md)

All notable changes to this project are documented here.

The project follows SemVer: `MAJOR.MINOR.PATCH`.

## Unreleased

### Fixed

- **The update notice named the wrong version — or never appeared.** Three causes:
  - GitHub returns releases **alphabetically by tag name**, where `rc9` sorts above
    `rc10`. The code took the **first** match in that list; the actually newest release
    sat at position 9. Users were therefore told the second-newest version was "new".
    It now looks for the **highest** version rather than the first.
  - It only checked **once a day**. Anyone starting the program a second time saw
    nothing. Now hourly — so effectively on every start.
  - There was **no way to check manually**. The "What's new" window now has a button;
    it turns into the answer itself rather than rebuilding the window.

## v2.0.0-rc10 - 2026-08-24

### Fixed

- **"English — original texts from the game" did nothing.** The option was offered but
  only checked whether an English `global.ini` already existed — and if it did not (the
  normal case), it reported an error. In practice this tied blueprint markup to one of
  the two third-party sources.
  - It now actually fetches the file: `scbp/spieltexte.py` reads it from the player's
    `Data.p4k`. **10 MB in 0.3 seconds** out of a 144 GB archive — only the central
    directory and a single block are read.
  - Blueprint details therefore work **without any third-party project**, using only
    files already on the machine.
  - An **existing** `global.ini` is left alone: it may hold another project's translation.
- **The third button was invisible.** Three choice buttons side by side did not fit the
  settings window — the last one sat outside it, and you had to widen the window to
  suspect it existed. They are stacked vertically now.

## v2.0.0-rc9 - 2026-08-24

Both from tester feedback.

### Added

- **Where the contract is available.** Until now it said where a blueprint *comes
  from*, but not where to *find* the mission — leaving you to look the mission name up
  elsewhere. Now the line is there: "Available in Stanton: Hurston, Crusader, ArcCorp,
  microTech and 12 more".
  - Planets and moons first, everything else after. A planet name is an answer you can
    act on; "HUR L2" only helps if you already know where you are.
- **Search by class, manufacturer and grade.** `military`, `stealth`, `civilian`,
  `industrial`, `energy`, `ballistic` — the class is shown on every row but could not
  be searched. Manufacturer names (`aegis`) and `grade a` to `grade d` as well.
  - Grade is stored as a **number** and displayed as a letter. Anyone searching
    "Grade A" types the letter — without conversion the search never matched.

## v2.0.0-rc8 - 2026-08-24

### Added

- **Text source can also be switched from the settings window** — the same three
  options as in the wizard. Changing your mind later (say from a German to an English
  client) should not mean hunting for the setup wizard.

### Fixed

- **Two close buttons stacked on top of each other.** The blueprint list, settings and
  "What's new" all have an ordinary system title bar — with an ✕ in it. A second,
  hand-drawn one next to it looks like a bug, and you have to guess which does what.
  This affected Windows just the same; the title bar comes from the window manager
  there too. The frameless overlay keeps its own ✕: it has no system bar.

## v2.0.0-rc7 - 2026-08-24

### Fixed

- **The save button in the settings window was invisible.** Once the content grew
  taller than the window, it simply pushed the button out — visible only after
  resizing the window by hand. Nothing hinted that something was missing below, so
  users would have discarded their changes without noticing.
  - The content now scrolls (scrollbar and mouse wheel) while **header and footer stay
    put**. The footer is placed before the content, so no amount of future settings
    can ever push it out again.

## v2.0.0-rc6 - 2026-08-24

### Added

- **Adjustable overlay opacity** (30–100 %, still 93 % by default). With a **single**
  screen the window inevitably sits on top of the game — you need to see through it.
  The slider in the settings window updates the window **immediately**: opacity is
  something you judge by eye, not by a number that only takes effect after saving.

## v2.0.0-rc5 - 2026-08-24

Blueprint details now show up **in the game** — inside the mission text, with tick
boxes for the ones you already own.

### Added

- **Blueprint details in mission texts** (`scbp/injektion.py`). Every contract that
  awards blueprints gets the list — ticked for what is in your collection, empty for
  what is missing. Plus a marker in the title (`[BP 2/3]`), so you can see it in the
  contract list without opening each one. **668 text spots.**
  - Along with the figures that matter before accepting: blueprint chance, minimum and
    maximum reputation, payout, reputation gain, cooldown, shareable yes/no.
  - Attached to the **text key**, not the mission name. That key is identical in every
    language — the same markup works for German, English and the game's nine others.
  - **Undo is byte-exact.** Everything inserted sits between markers; `entfernen()`
    restores the original file character for character.
- **Blueprint data comes from the SCDL team.** The translation project publishes its
  prepared contract data openly — **813 contracts**, German **and** English, with
  details available nowhere else (region, danger rating, cooldown in words). scmdb
  alone yields 349.
  - The division of labour is the sensible one: the SCDL team maintains what it
    maintains anyway. This tool adds the one thing only it can — the **tick box**. In
    the raw data blueprints are listed neutrally as `- Name`; that becomes `[x]` or `[  ]`.
  - Fetched at runtime from the original address, with attribution in the inserted
    text. If the data is unreachable, the tool's own scmdb-based layout takes over.
- **Fetching and updating text sources** (`scbp/uebersetzung.py`): the German
  translation from `rjcncpt/StarCitizen-Deutsch-INI`, StarStrings from
  `MrKraken/StarStrings`, or the English originals from your own `Data.p4k`. With an
  update check, because every translation update overwrites the blueprint notes.
  - **None of it is bundled.** Both third-party projects keep their rights; everything
    is fetched at runtime from their own pages, at the user's request.
  - StarStrings users keep it: its markup stays, ours goes after it — filling its gaps.
- **A step in the setup wizard** that asks. Nothing is preselected: clicking past it
  leaves your installation untouched. It is the only place where this tool changes
  anything about the game.
- **A section in the settings window**: state, refresh, remove, check for updates.

### Fixed

- **The SC Deutsch Launcher was not found on dual-boot systems.** Only Wine prefixes
  were searched — but for players who moved over, the data sits on the **Windows
  drive**, usually mounted under Linux. An entire blueprint collection went unused
  while sitting two folders away.
- **A configured launcher path now stands on its own.** Previously, if the folder did
  not exist, the program quietly fell back to searching and might use a different
  collection than the one specified.

## v2.0.0-rc4 - 2026-08-24

The first real blueprint drop on an **English** client — and what it turned up.

### Added

- **A settings window** (`scbp/einstellungsfenster.py`), reachable via ⚙ in the title bar.
  All five fields in one place: language, Star Citizen folder, launcher folder, check
  interval and sound — each with one line of explanation below it.
  - Previously only language and game folder could be changed, and only through the
    **setup wizard**. The other three required editing `einstellungen.json` by hand.
    Reported as "I can't find the settings button at all" — rightly so, there wasn't one.
  - **The wizard stays.** Two paths on purpose: it walks you through first-time setup for
    anyone who does not know how this works, while the gear is the direct grip for anyone
    who knows exactly what they want to change.
  - Language switches **immediately**, not on save — if you pick a language you want to
    see whether it is the right one.
  - A folder that does not exist is **not** saved. Otherwise the watcher would look in a
    place the player believes is correct, and report nothing.

### Fixed

- **No sound on Linux.** The watcher called `tkinter.bell()` — that is the **X11 system
  bell**, which is off almost everywhere on modern desktops and effectively gone under
  Wayland. The code explicitly considered this "not a fault". On the first real drop it
  stayed silent, and that made it one: a sound that fails exactly when it is needed is
  worse than none, because you rely on it and miss the blueprint.
  - `scbp/ton.py` now plays a **system sound** via `canberra-gtk-play`, `paplay` or
    `pw-play` — all common on Linux, none a new dependency. `bell()` remains the last
    fallback.
  - `aplay` is deliberately absent: it cannot play Ogg and would fail silently.
- **The watchlist star was too small** to hit. It is the one glyph in a row you click
  rather than read — now noticeably larger, with a wider click area.

### Changed

- ⭐ **The English blueprint message has been measured.** Until now five guessed wordings
  sat side by side, none confirmed against a real English client. The client writes:

        Added notification "Received Blueprint: Aves Shrike Helmet: "

  `Received Blueprint` now comes first. The four remaining candidates stay as a fallback —
  they cost nothing, and should CIG change the wording, one of them might fit.

## v2.0.0-rc3 - 2026-08-24

The blueprint list, sharpened up by actually using it.

### Added

- **Sections you can show and hide** — four buttons above the list: ship parts,
  FPS weapons, armor & clothing, other. Looking for armor? Hide the ship and 714
  rows become 316. Individual buttons for all 25 categories would not have helped;
  that is a second list on top of the list.
  - The **last** visible section cannot be hidden as well. An empty list with no
    visible reason is not a setting, it is a riddle.
  - Hidden sections are dimmed, not removed — you need to see that you clicked
    something away yourself.
- **A ✕ in the search box.** It only appears once there is something to clear: a
  clear icon on an empty field is just an icon that does nothing.
- **German search terms for the English category names.** Four categories are
  deliberately English because that is what the game calls them — "Cooler",
  "Power Plant", "Quantum Drive", "Radar". Anyone thinking in German types
  "Kühler" and found nothing. Now both work, without changing the wording players
  know from the game.

### Changed

- **A sensible order instead of the alphabet.** Ship parts first, then FPS
  weapons, then armor and clothing. Alphabetically "Docking collar" came first
  and armor sat in the middle — 25 categories in letter order are not an
  overview. Within a section it stays alphabetical: that is predictable, and
  everyone would order the ship parts differently in their head.

## v2.0.0-rc2 - 2026-08-24

Both found during the first run against a real Linux installation.

### Added

- **Hover explanations for the icons** (`scbp/hinweis.py`). The title bar is seven
  symbols — ⟳ ⓘ ☰ ⏻ 🗑 ✕ and the resize grip ◢. Anyone who did not build it had to
  guess, and trying things out is a poor idea with ✕ and 🗑. Labels next to them are
  out of the question: the overlay is deliberately narrow and sits on top of the game.
  - The ones with a **state** say what the click will do, not just what the symbol
    means: ⏻ depending on autostart, ⓘ depending on whether a new version is waiting,
    the star depending on whether the blueprint is already being watched.
  - The blueprint list's ✕ explicitly says "the watcher keeps running" — it looks
    exactly like the overlay's ✕, which quits the program.
  - `merken` and `nicht_mehr_merken` had been in the language module since
    v2.0.0-rc1 without either ever being wired up.

### Fixed

- **Search looked like it found nothing.** Anyone who had scrolled down the
  blueprint list and then typed something was left staring at **empty space** —
  the view kept its old scroll position while 714 rows turned into five. The
  matches were there, just far above. Search and filters now jump back to the
  top; ticking off, watching and expanding keep the position, where jumping
  would only lose your place.
  - Reported as "typing *xl* leaves the list empty" — `XL-1` had been in the
    results the whole time.
- **The blueprint catalogue was never fetched.** The function existed, but nothing
  ever called it — `katalog.laden()` quietly returned an empty catalogue when the
  file was missing. As a result the blueprint list stayed empty for **every** user,
  while the notice inside it promised the catalogue would be fetched on startup.
  Found during the first run against a real Linux installation.
  - The catalogue is now fetched **before** the game language is worked out, if it is
    missing entirely. That ordering matters: `phrasen.selbst_finden()` needs the
    blueprint names to derive this client's wording from the logs, and the backlog
    scan needs that wording. Without a catalogue both came up empty on the very first
    run — on an English client that meant not a single blueprint found, with no
    visible reason why.
  - After that a separate background thread keeps it current. Roughly 12 MB must not
    stall the watcher loop — log detection is the core job.
  - If the fetch fails (no network), it is retried after 5 minutes instead of 6 hours.
    A brief hiccup at startup should not linger all day.

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
