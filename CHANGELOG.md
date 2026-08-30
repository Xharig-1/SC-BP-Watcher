# Changelog

**English** · [Deutsch](CHANGELOG.de.md)

All notable changes to this project are documented here.

The project follows SemVer: `MAJOR.MINOR.PATCH`.

## v3.3.0 - 2026-08-30


### Added

- ⭐⭐ **The workshop — three new pages.** The blueprint used to be where the
  answers stopped: "you have it" or "you are missing it". Now the tool answers
  what comes after that.

  | Page | The question it answers |
  |---|---|
  | **Crafting** | What does this blueprint need — and what comes out? Ingredients, craft time and the stats of the finished item, for **1,597** craftable things |
  | **My stock** | What do I have? Material, amount, quality and location, kept by hand. The recipe then shows what is missing |
  | **Mining** | Where do I get it? Type a resource → where it is found. Type a location → what is found there. **48 locations, 38 ores** |

  **And quality counts.** One slider per ingredient shows what *your* material
  makes of the values — the data carries it for **1,524 of the 1,597**
  blueprints. If you hold quality 900 iron and quality 500 riccite, you see
  exactly what that yields.

- **The author of the German translation is now credited** — with name,
  repository and licence. It is by **rjcncpt**
  ([StarCitizen-Deutsch-INI](https://github.com/rjcncpt/StarCitizen-Deutsch-INI))
  under **CC BY-NC-SA 4.0**, which requires exactly that. Until now only the SC
  Deutsch Launcher was named — the distributor, not the author.

  Shown under **Thanks & Licenses** and in both readmes.

  The watcher does **not bundle** the translation and never passes on a modified
  copy: it only extends the file on your own machine, and the **source note in
  its first line is left untouched** — the author asks for that, so anyone can
  find their way back to the original translation.

- ⭐⭐ **Only things that actually exist in the game can be stored** — resource
  **and** location. The "Add anyway" button is gone.

  The reason is not tidiness: a free text field means somebody can enter slurs,
  religious or political text, take a screenshot and spread it. In the end nobody
  asks who typed it — it stands in this tool.

  | Field | Choice | Source |
  |---|---|---|
  | Resource | **52 names** — 39 minerals, 13 plants | game data |
  | Location | **158 stations, cities and outposts** | UEX Corp |
  | Quality | 0–1000, anything else is rejected | |

  The location stays **optional** — empty is still fine. And if no location list
  has arrived yet (first start without a connection), the field does not block.

- ⭐ **The 13 plants are new** — Flareweed, Heart of the Woods, Sunset Berry,
  Golden Medmon and the rest. The watcher did not know them: they are not listed
  with the minerals but as deposits at the locations. They are hand-harvested and
  can now be stored with a quality.

- ⭐ **Crafting search now finds the ingredient too.** "ric" returned "Lo**ric**a"
  and "Fab**ric**ation" — accidents — and never the 83 blueprints using Riccite.
  And where nothing comes of it, it now says so: **26 of the 52** resources appear
  in no recipe, all plants among them. The search box is therefore labelled
  "Blueprint or resource …" instead of "Search …".

- ⭐ **"Buy or mine?" — the question that follows "you are missing".** Next to
  every missing ingredient it now says what buying it would cost — or that it
  **cannot be bought at all**.

  The finding behind it is the real gain: of the 26 resources used in recipes,
  **seven cannot be bought anywhere** — Aslarite, Lindinium, Ouratite,
  Quantainium, Riccite, Savrilium, Torite. And **five of those are also on the
  dismantle blacklist**: neither purchasable nor recoverable from a dismantled
  item. Those are the real bottlenecks in crafting, and until now nothing said
  so.

  > ⚠ "Cannot be bought" is written exactly that way — never as "0 aUEC".
  > Otherwise somebody hunts a terminal for a bargain that never existed.

  > ⭐ **Goods bought at a terminal are always quality 500** — the base point.
  > An item made from them gets exactly ×1.000 on **every** property. It only
  > gets better with self-mined ore above that. That is why the quality now
  > stands next to the price: without it "buy" reads like an equivalent route
  > that merely costs money instead of time — and it is not.
  >
  > Measured across every recipe in build 4.10.0: **5,025 of 5,219** quality
  > effects have their base point at exactly Q 500.


  Prices come from the [UEX Corp](https://uexcorp.space) API, **at most once a
  day** and in the background. ⚠ They are **not bundled** — the same rule as
  for scmdb. Without a connection the last state stays; with none at all the
  line simply does not appear, and the page looks exactly as before.

  No trade routes, no per-terminal prices, no cargo planning: the watcher
  answers "buy or mine?", not "where do I sell highest?".

- ⭐⭐ **Scan signature — turning the scanner's number into a name.** The mining
  scanner in game shows a value and does not say what is behind it. Type it into
  the mining page and the watcher tells you **which ore** it is and **how many
  rocks** the deposit holds.

  | Input | Meaning |
  |---|---|
  | `8600` | this exact value |
  | `~8600` | ±10 % tolerance |
  | `12000-13000` | anything in between |

  > ⚠ Without the tilde **nothing** is rounded. If you are off, you get "no ore
  > has this signature" rather than a match that sends you to the wrong rock.

  Rarity limits how many rocks a deposit can hold — Quantainium is legendary, so
  at most two. A deposit of three cannot exist, and the tool does not claim one.

- ⭐ **Which refinery gets you the most** — every ore now lists all twenty
  refineries with their bonus, best first, plus the spread. And the spread is no
  rounding error: **Bexalite differs by 18 percentage points** between the best
  and the worst choice, Quartz by 16, Titanium by 15.

  Stations sharing a profile appear on one line (`CRU-L1 +1 others`). Ores where
  it makes no difference say so instead of showing ten zero rows.

- **What dismantling will NOT give back.** Six resources are on CIG's blacklist —
  Lindinium, Quantainium, Riccite, Ouratite, Stileron, Savrilium. Everything else
  returns at half. If a recipe uses one of them it now says so: a part made from
  it is a one-way street.

- **Percentage and range on every quality effect.** `× 0.867` has to be converted
  in your head — `−13.28 %` now stands next to it. And below it, what is
  achievable at all: `Q 0–1000 · ×1.2–0.8 · base 500`. Without that a factor does
  not tell you whether there is much left to gain.

- **Star Citizen Fan Content** — the official "Made by the Community" badge from
  the Fankit is now in the readme, and the full notice per the Fankit Agreement
  is also **inside the program** under "Thanks & Licenses". People who use a tool
  rarely read its readme.

- **One quality slider per material instead of one for all.** There used to be
  a single slider giving every ingredient the same quality — a situation you
  practically never have. Each material now has its own, starting at your
  actual stock value.

  That makes the real question askable: "I have 500 Iron — what do I get with
  900, and what does that change about the Riccite value?" A material that
  raises three properties still has just **one** slider; its three rows move
  together.

- **The stock list shows how a material is mined** — hand, vehicle or ship, as
  its own column.

- **The stock list is searchable** — the search box is always there now, not
  only from five entries on.

- **Delete a single entry** while editing it — a red button next to "Save
  change", with a confirmation naming the entry and amount.

- **Crafting filters by material:** "have the material" or "material missing",
  calculated against your stock. With 1597 blueprints that is 19 against 1573 —
  which is what makes the list usable.

  > ⚠ Calculated from **your list**, not your cargo hold. The watcher does not
  > know the latter.

- **A red "Clear stock" button** — with a confirmation, so nobody loses their
  stock by accident. The question names **how many entries** will go. Your
  stock is handwork that exists nowhere else, and the export button sits right
  next to it.

- ⭐ **Search by contract.** "Retake" used to find nothing although six
  blueprints come from contracts with that word. The search now also covers
  **contract name, faction and contract type** — "nine tails" finds three
  blueprints, "headhunters" 141.

  Above the results an overview answers the actual question: **what does this
  quest hold?** For "retake" that is `Retake Platforms From Nine Tails — 3
  blueprints` and `Need multiple CFP outposts retaken — 3 blueprints`.

  > **And the contracts are clickable.** One click narrows the list to that
  > contract's blueprints only; clicking it again releases the filter.

- ⭐⭐ **Two levels instead of one long list — category and subtype.** The type
  dropdown had thirty entries: "Armour (arms)", "Armour (legs)", "Helmet",
  "Backpack", "Clothing (jacket)" … Assembling a full set of armour meant
  hunting through all of them.

  There are now **seven groups** — ship weapons, ship modules, ship tools, FPS
  weapons, gear, armour, clothing — each with its own subtypes: ship weapons
  split into laser cannon (22), laser repeater (15), ballistic cannon (13),
  ballistic gatling (9), scattergun (6) and the rest; armour into helmet (84),
  torso (70), arms (69), legs (69), undersuit (11).

  > **What cannot be grouped stays on its own** — docking collars and the other
  > one-offs do not vanish into a catch-all.

  **Blueprint list and crafting share one grouping** — same blueprints, so the same way to search.

- **The subtype field now says that it is one**: instead of "All subtypes" it
  reads "12 subtypes — refine here" whenever there is something to pick.

- **Your own watches can be removed** — every row has an ×.

- ⚠ **When a watched item becomes available, you now see it.** The "watching"
  filter only checked clicked names — a match on a search pattern stayed
  invisible, so you watched something and were never told it had arrived. It
  now shows as an ordinary row with its info icon, drop-off and reputation.

- **The watcher now shows which contracts are running** — and keeps them across
  a restart. Until now an accepted contract was only a line in the log view;
  restarting the watcher lost it.

  This works because Star Citizen writes not just the acceptance to its log but
  every ending too. Across the logs of a single machine: 701 acceptances, 303
  completions, 112 withdrawals, 57 failures — each with the same mission id.
  The watcher walks the running log once and keeps score: accepted with no
  ending after it means still open.

  > **Finished ones disappear.** Someone running ten contracts in an evening
  > should not have to look at ten dead lines. Completion, withdrawal and
  > failure remove the contract from the display, immediately and while
  > running.

  **Shared** contracts count as well: if someone in your group passes one to
  you, you see just as clearly whether it holds blueprints for you.

  Two things the log cannot know, so they are not claimed: restarting the
  **game** starts a fresh log, and nothing is asserted about what ran before.
  And if a contract is lost to a bug, the game says nothing — for exactly that
  case every line can be dismissed with a click on the ×.

### Changed

- **Data now comes from the official SCMDB mirror.** Krovax set up a public
  repository for exactly this purpose
  ([KrovaxCode/SCMDB_DATA](https://github.com/KrovaxCode/SCMDB_DATA)) — "for
  programmatic consumers". That is steadier than going through the website,
  which sits behind bot protection. **scmdb.net stays as a fallback** should the
  mirror ever be unavailable. Thanks to Krovax 🙏
- **"Progress" is now "Blueprint progress".** With the new pages the old name
  would have been ambiguous.

### Fixed

- ⚠⚠ **Clicking "read the old logs again" brought back the full setup wizard on
  the next start** — on a tool that had been set up for weeks. And closing that
  wizard left you with nothing at all: the program quit **silently**, no overlay,
  no message, not a line in the problem report.

  Two mistakes in a chain:

  | | |
  |---|---|
  | How "first start" was detected | by the missing **read position** (`logstand.json`) — the very file that button deletes on purpose |
  | What cancelling did | quit the program, **always** — even with the setup complete |

  The tool now records a completed setup itself, and cancelling only quits on a
  **genuine** first start. Someone who dismisses the wizard wants to keep
  working, not to stop.

- ⚠⚠ **"Buy me a coffee" and "Discord" did nothing at all.** Both buttons at the
  bottom left said "opening", and then nothing ever happened — not even a line
  in the problem report.

  The cause sits in the Linux build: inside the AppImage the library paths point
  into our own unpacked bundle. Any system program started from there loads our
  libraries instead of its own and dies immediately. Python's `webbrowser`
  reports success anyway — it only checks that it **started** something, not
  that it survived.

  Half the links in the program already had the countermeasure, the other half
  did not. They all go through one place now: clean environment, `xdg-open`
  first, `webbrowser` only as a fallback — and if it really fails, the address
  appears in the status line instead of the button staying silent. The self-test
  no longer lets a direct `webbrowser` call through.

- ⚠⚠ **`SC_BP_NO_NET=1` did not switch off everything it promised.** The
  catalogue, prices, storage locations, server status and the update check
  honoured it — the **translation sources** and the **contract data** did not.
  Anyone setting that switch does not want half an assurance. Every fetch now
  honours it; the one exception remains the problem report, which only goes out
  on a button press anyway. The self-test no longer lets a module with network
  access pass that does not know the switch.

  The README also names **every** connection individually now, with how often
  it happens — it used to say "two things", and there are five.

- ⚠ **The numbers in the README were a patch old** — "655 of 722 blueprints"
  instead of the actual **670 of 738**. Numbers like that go stale with every
  game patch without anything noticing; the self-test now compares them against
  the real data.

- ⚠ **"Reset inventory" sat under "Report a problem" — nobody looks for it
  there.** It now sits at the end of the **Blueprint inventory** page, right
  below "Read the logs again". Side by side, the difference that matters also
  becomes visible: reading again **adds** what is missing. Resetting **throws
  away** and rebuilds from the logs.

- ⚠ **In a recipe you could no longer tell which range belonged to which
  value.** The lines "Q 0–1000 · ×0.9–1.1" piled up under the last value
  instead of sitting under their own — with three materials that meant three
  near-identical lines with no visible link to anything.

- ⚠ **Backticks showed up in the middle of on-screen text** — "`8600` for an
  exact match" instead of "8600". They come from the markup in the text file;
  Tk simply displays them. Affected were the scanner-reading help text and
  paragraphs under "What's new". The interface check now also trips on
  backticks, not just on asterisks.

- ⚠⚠ **The startup trace in the diagnostic report had become useless.** Instead
  of the startup steps it showed the same line twelve times, "Liste: zeichnen
  beginnt" — and that section is the only thing left after a hard crash: its
  last line says how far the program got.

  Two causes, both fixed:

  | What | Before | Now |
  |---|---|---|
  | Splitting startup ↔ usage | anything not starting with "Seite " counted as a startup step | split at the line that ends the startup |
  | Repetitions | every line on its own | summarised as "(12×)" |

  The old way was a list of prefixes — it broke the moment a new trace entry was
  added anywhere in the program. The new one cannot: whatever happens after
  startup is necessarily behind the boundary line.

- ⚠ **No contract at all was recognised in Swiss German.** The `live-CH`
  edition writes "**Uftrag** angenommen", "Uftrag abgschlosse", "Uftrag
  fehlgschlage" — without the "A". Read straight from the source, not guessed.
  Without those entries the watcher stayed silent there: no message, no skipped
  file, simply no contracts.

- ⚠⚠ **The percentages were cut off** — "× 1.047  +4.(" instead of "+4.70 %".
  The label had a fixed width of nine characters; when the percentage was added,
  Tk truncated it silently. Percentage now has its own column, and the self-test
  measures **every** label in a recipe against the width it gets.

- ⚠ **Same material, same quality, same location is now added up** instead of
  becoming a second row. Adding after every mining run otherwise left ten rows of
  the same pile within a week.

- ⚠ **"Remove" in the stock table was cut off** ("move"). It was packed after the
  columns and only got the leftovers.

- ⚠ **An open dropdown stayed put when switching pages** — opened in Crafting,
  then a click on "My stock", and the list kept floating above the new page. It
  now listens for its field being hidden.

- ⚠ **The scrollbar was practically invisible** — contrast **1.6 : 1** on an open
  list. Now 2.9 : 1 there, 3.6 : 1 on a page, plus a visible track and 10 instead
  of 8 pixels. Applies to every scroll area.

- ⚠ **Dropdown fields were as wide as their longest entry.** Among the 64
  manufacturers stands "Musashi Industrial & Starflight Concern" — the field grew
  to 314 pixels and the fourth filter no longer fitted the row. Now capped; the
  open list stays full width.

- ⚠ **The window left the monitor at large font sizes.** With two stacked
  monitors it ran into the second one. It now stays on its monitor unless you drag
  it. **"Very large" has been removed** as a font size — that step made the window
  taller than a screen.

- ⚠ **The stock amount could not be edited the way people do it.** When editing,
  the amount is already in the field; to add three you append `+3` and end up with
  `1.04+3` — which was rejected. Both work now and give the same result. Next to
  the field it shows what comes out while you type: "makes 4.04 SCU".

- ⚠ **The name suggestion sat 557 pixels below the input field**, down by the
  buttons. Now 15 pixels next to it — both measured.

- ⚠⚠ **In the stock list the amount could not be edited the way people do it.**
  When editing, the current amount is already in the field — to add three you
  append `+3` and end up with `1.04+3`. That was rejected ("enter an amount,
  for example 12.5") because only a **leading** sign counted.

  **Both** now work, and both give the same result: `+3` and `1.04+3` each turn
  1.04 into 4.04. Nobody has to know which form is meant.

- ⚠ **The hint about it was a punishment.** "Overwrite the amount — or type +5
  or -2 to add or subtract" described a mechanism in accountant's language
  without saying where the signs belong.

  The real explanation is no longer text: **next to the field it now shows what
  comes out** while you type — "makes 4.04 SCU", "makes 0 — the entry will be
  removed", "more than you have (1.04 SCU)". The hint shrank to one line with
  an example.

- ⚠ **The name suggestion sat 557 pixels below the input field** — down by the
  buttons while you type at the top. A suggestion you have to hunt for is not
  one. It now stands right next to the field (15 pixels); both measured.

- ⚠⚠ **The entire quality block had vanished** — sliders, effects, even the
  value behind "craft time". Affected rc37 and rc38.

  Cause: while adding the dismantle blacklist a variable was named `_dauer` and
  thereby shadowed the **function** of the same name in that file. A few lines
  later `_dauer(stufe['zeit'])` raised `TypeError: 'int' object is not
  callable`, aborting the build mid-recipe: everything from the craft time
  onwards was simply missing.

  > ⚠ The self-test missed it because it **built** the page but never
  > **expanded** a recipe row — which is where that code runs. It now does, and
  > additionally checks that no local name shadows a function of the same file.
  > Measured against the shipped rc38: both checks fire there, at exactly the
  > right line.

- ⚠ **Swiss German went unrecognised.** There is a separate variant of the
  German translation (`live-CH`) that says "**Bauplan überchoo**" instead of
  "Bauplan erhalten". Without the entry the watcher found **zero blueprints in
  silence** there — no error, no skipped file, just nothing.

  Only affects the fallback: a readable `global.ini` always wins. For a vanilla
  English install, whose text file sits inside `Data.p4k`, that list is all
  there is.

- ⚠ **A reordered translation would have blinded the watcher silently.** Only
  the part **before** the placeholder was taken from the game's text file. For
  "Received Blueprint: %s" that is right. Were CIG ever to reorder it — "%s has
  arrived" — nothing would stand in front, and detection would fall back to the
  bundled list, which then no longer fits. Again without any hint.

  No language phrases it that way today; the branch costs nothing and covers the
  day it happens.

  > ⚠ This is the path every blueprint find runs on. The self-test therefore
  > first proves that without a reordered phrasing the search pattern is
  > **character-identical** to the old one — measured, not claimed.

  Both findings come from the blueprint reader of the **KRT Basetool**
  (GPL-3.0), which reads the same `Game.log`. Thanks for that!

- ⚠⚠ **The ingredient list lied for more than one unit.** Typing 10 into the
  quantity box still showed the requirement for a single unit — "1.16 SCU" and
  "missing 1.16" while 11.6 were needed. The deduction was right, only the
  display was not. It now recalculates as you type and shows where the figure
  comes from: `11.6 SCU (1.16 × 10)`.

- ⚠⚠ **If material is short, NOTHING is deducted any more.** Previously it took
  what it could and reported the rest. Clicking with "quantity 10" while having
  material for three left you with an emptied stock and none of the ten items.

  If an ingredient is missing the item was never craftable — the click was a
  slip or a typo. The **shortfall** is now reported, not just the name, and the
  quantity you typed stays so you can correct it. (Stock could never go
  negative, but "swept to zero" is nearly as bad.)

- ⚠⚠ **Good values were shown in the warning colour.** The display coloured by
  the bare number: green from `× 1.000` up, gold below. For **852 of the 6524**
  quality effects in build 4.10.0 that is exactly backwards — there better
  quality lowers the number, and that is the improvement:

  | Property | Cases |
  |---|---|
  | Recoil Smoothness / Handling / Kick | 245 each |
  | Quantum Fuel Burn | 114 |
  | Damage Mitigation | 3 |

  On the FS-9 LMG the best possible recoil (`× 0.800`) sat in the warning
  colour and the worst (`× 1.200`) in green. The direction is now read **from
  the game data itself** rather than guessed from property names, so it holds
  even where the same property runs both ways. Rows where lower is better now
  say so.

  Cross-check: at quality 0 every value is now gold, at quality 1000 every
  value is green.

- ⚠ **"Power Pips" are not multipliers.** They appeared as `× -1.000` — a
  factor that cannot exist. They are in fact counts from **−3 to +3** in fixed
  quality bands, and they affect every power plant (598 of 6524 effects). They
  now read `-1` and `+3`, with sign. Detected by the value, not the name: a
  multiplier is always above zero.

- ⚠⚠ **The open dropdown lists could not be scrolled** — turning the wheel left
  the list where it was and moved the **page behind it** instead. As the field
  slid away, the list closed. The lower entries were therefore **unreachable**:
  everything past "microTech" among the 48 mining locations, everything past
  "Greycat Industrial" among the manufacturers.

  Cause: the mouse wheel is handled in one place for the whole program and finds
  its scroll area by walking up the parent chain from whatever sits under the
  pointer. The open list is a window of its own, but its parent is the dropdown
  field — which sits inside the scrollable page. So the chain walked out of the
  list and into the page behind it.

  The wheel is now caught at the list window itself and stops there; the page
  never sees it. Measured: against the old build the page moves by 10.3%, against
  the new one by 0.0%, and the list scrolls through to the last entry. Scrolling
  **next to** the list still closes it.

- ⚠ **The open list was too long.** It reached from the field to well below the
  window edge, and was clipped at the screen edge when the window sat low. Until
  now it was only limited by available *space* — which is vast on a large display.

  It now shows at most **15 rows**, anything beyond scrolls. That also makes the
  scrollbar visible, so you can tell there is more. For the 48 mining locations
  that is 497 pixels instead of 1090.

  On top of that a hard ceiling: a dropdown never grows taller than the
  **smallest possible** window (760 pixels). Otherwise enlarging the window
  would produce a list that no longer fits once you shrink it again.

- ⚠ **A completed contract kept showing as "accepted".** Reported on
  2026-08-30 for "Retake Platforms From Nine Tails": accepted in game at 01:18,
  completed at 01:59 — and when the watcher started at 02:22 it announced it as
  freshly accepted.

  Two faults propping each other up:

  1. At startup the watcher reads `Game.log` once, only to learn where it left
     off. In doing so it also collects every contract event. If nothing new had
     been written by the next pass, that collection was **not cleared** — it was
     evaluated a second time.
  2. The evaluation took *all* endings first and *all* acceptances second. In a
     section containing both, the ending therefore hit nothing and the acceptance
     put the contract back afterwards.

  Point 2 hits anyone starting the watcher while the game is already running:
  the first section then catches up on everything since the last run.

  The lists are now cleared before every read, and the events are walked **in log
  order**. Whatever is open at the end is shown. Cancelling a contract and taking
  it again straight away still shows it.

- ⚠ **The contract row in the list could not be dismissed.** The red marker only
  existed in the contract bar, not on the row below it — there was no way to get
  rid of the message.

  The row now belongs to its contract: it carries the same red marker, disappears
  by itself once the game reports the end, and can be dismissed by hand.

- ⚠ **The overlay always started at its smallest size**, however large you had
  dragged it. The size was saved — it was overwritten immediately.

  The cause was the minimum-width check from rc10: shortly after startup Tk
  reports width **1** for a window that is not shown yet, so the comparison
  always matched and the overlay was set to the minimum. It now only acts once
  the window is actually up. Verified: 900×400 stays 900×400, and a window
  remembered too narrow is still widened.

- ⚠ **In the stock list the search box lost the cursor after every keystroke.**
  The field was built **inside** the redraw routine, which clears the whole list
  area on every change — so each typed character destroyed the field itself. It
  is now created once, outside. Anything that can hold a cursor belongs outside
  the redraw.

- ⚠⚠ **"Report a problem" could not be opened without internet** — the window
  froze until a network timeout expired. Precisely the page you need when
  something is wrong. The diagnostic report asked scmdb.net for the current game
  version while being built, on the main thread. It now shows the **stored**
  catalogue version. Measured: **6.1 seconds down to 0.1**.

- ⚠⚠ **The server status page could crash the window** with no internet. The
  fetch runs in the background and calls back into the window; switching pages
  or closing the window meanwhile crashed in a thread where no error hook
  catches it. Every callback is now guarded.

- **Without a connection the status page says so** instead of "nothing fetched
  yet, click Check now" — advice that leads nowhere offline.

- **The dropdown no longer runs off screen.** It limited itself to the display
  but not to the window; with 38 materials and the window low on screen it was
  cut off. It is now at most as tall as the window and scrolls.

- ⚠ **The overlay's resize grip was missing entirely.** It hung on the
  blueprint list — fine while the list got the rest of the window. Since the
  active-contracts bar sits above it, the list can end up **shorter than the
  grip itself**. It now hangs on the window and is present at any height —
  checked at 190, 130 and 110 pixels — while still disappearing when collapsed.

- **The dismiss control on a contract line is now a crossed-out circle**, red
  and clearly larger. A cross means "close the window" everywhere else in the
  program; removing a single line is a different thing.

- ⚠⚠ **The overlay said 405 blueprints, the progress page 382 of 738.** Two
  numbers for the same thing, and neither explained the other.

  The cause was the catalogue on disk: written months ago, when magazines were
  still keyed as `FS-9 Magazine (75 cap)`. The inventory has long used
  `FS-9 Magazine (75)` — matching the quantity wording came later. **23
  magazines and batteries** counted as missing everywhere although they were
  owned.

  Catalogue keys are now rebuilt from the name on load. If everything already
  matches, nothing is touched.

- ⚠ **The open dropdown stayed put while scrolling.** It floats as its own
  window above the page, so scrolling the list underneath left it lying across
  unrelated rows. No focus change happens there, and focus was all it watched.

  It now also closes on **scrolling**, on **moving or resizing the window**, and
  on **Esc**. Scrolling inside the list itself still works.

- ⚠⚠ **"Nothing found" as soon as a category was selected** — now really fixed.
  The filter was right, but **a second place** discarded whole groups in
  advance, comparing catalogue type against the new top-level category. That
  never matches, so every group fell out. The shortcut is gone; the check now
  happens in exactly one place.

- ⭐ **The watcher now notices such cases itself.** If the dropdown says
  "Ship modules (157)" and the list stays empty, that is a contradiction — one
  number comes from the catalogue, the other from the filter. It is written to
  the error log and appears in the diagnostic report, instead of someone having
  to send a screenshot.

- **Mining lists materials first.** It used to show the 48 locations by
  default, but you arrive asking "where do I find titanium?", not "where am I?".

- ⚠⚠ **"Nothing found" as soon as a category was selected.** The list showed
  `0 of 738` although a category and subtype were chosen. The filter itself was
  right — the **drawing** aborted: rebuilding the dropdowns left the old layout
  callback pointing at destroyed widgets (`TclError: bad window path name`).
  Dead elements are now skipped. Found through the error log that recorded the crash while the screen showed only an empty list.

- ⚠ **The subtype could not be selected on the crafting page.** The check
  "does this subtype belong to the chosen category?" compared against a list of
  **pairs** rather than values, so it never matched and the selection was
  cleared immediately.

- **The button row on "Report a problem" now claims the space it needs**
  instead of wrapping — up to the screen width. Two fixed minimum widths had
  failed: how wide a button really gets is only known once it is drawn, and
  that differs per system.

- ⚠⚠ **Watch patterns matched inside words — and reported the wrong item.**
  The pattern `arden backpack` matched *W**arden** Backpack Purgatory Camo*:
  the watcher announced a piece of armour as available that has nothing to do
  with the one being watched.

  Patterns now match at **word boundaries** only — no letter or digit directly
  before or after. Hyphens and spaces count as boundaries, so `abc-mk4 legs
  grey` still matches.

  > **Why this matters here:** a squadron armour set means exactly one item per
  > slot. The colours were tested for months for camouflage; an "almost right"
  > piece is worthless.

  Found while proof-reading the stored watches.

- ⚠ **On "Report a problem" the five buttons stacked vertically.** The window's
  minimum width was 1100 px while the button row needs 869 px in German plus
  sidebar and margins. It is now 1160 px.

- **The armour role filter is gone again** — nobody searches by it.

- ⭐ **Filter by subtype — you can finally tell the weapons apart.** The
  blueprint list lumped all ship weapons together. There is now an extra
  dropdown: for ship weapons **Ballistic (32) · Laser (40) · Distortion (6) ·
  Neutron (6) · Tachyon (3)**, for armour the **roles** (combat, engineer,
  hunter, stealth, miner …).

  > **It only appears when there is something to choose.** Coolers would offer
  > sizes only, and those have their own field.

  This works by joining two sources: the catalogue knows the armour body parts,
  the recipe data knows the weapon type. Joined by name — **738 of 738**
  blueprints match.

- ⭐ **Crafting now has the same filters**: type, subtype or armour role,
  manufacturer, and "blueprint owned / missing". It previously had a search box
  only, and without knowing what to search for you paged through 1597 rows.

- **Mining gets dropdowns** for material and location — 38 and 48 entries you
  previously had to know by heart in order to type them.

  > All three pages use the same controls as the blueprint list: the way you
  > operate this tool should not change from page to page.

- ⚠ **"You are not watching anything" while nine watches were stored.** The
  watchlist holds two kinds: blueprints clicked in the catalogue — and your own
  watches with search patterns. The view showed only the first kind while the
  diagnostic report counted both. Your own watches now appear at the top of the
  view with their patterns.

- **Crafting takes a quantity.** Building ten in a row meant ten clicks — and on
  the eleventh the stock was wrong without anyone noticing. There is now a field
  next to the button: enter the number, click once, done. It resets to 1
  afterwards so the next click does not quietly deduct ten again.

- **The stock list can be exported and loaded back.** As a backup (`.json`),
  which loads again here, or as a spreadsheet (`.csv`) for reading and sharing.

  > Your stock is handwork that exists nowhere else: no log, no data source,
  > only what you typed. Without an export it is gone at the next machine.

- **The "Inventory" tab is now "Blueprint inventory".** With "My stock" next to
  it, one of the two names had to say which is which.

- **Two new pages: "Crafting" and "Mining".** They answer the question that
  comes after the blueprint — *what do I need, and where do I get it?*

  **Crafting** lists all **1,597** craftable items. One click shows the
  ingredients with amounts and the craft time. And because the watcher knows
  your collection, every row says whether you have the blueprint — 403 ticks out
  of 404 blueprints.

  > **Two** rows show a `?` instead of a tick. Three names cover several
  > different items ("BroadSpec" exists in S02 and S03, "Main Powerplant" for
  > Idris and Reclaimer). Your collection only knows the name, not the variant —
  > so we claim nothing.

  **Mining** answers both directions in one search: type a resource and you get
  its locations (Iron: 27). Type a location and you get everything found there
  (Daymar: 14 ores). Each entry says whether it is FPS, vehicle or ship mining.

  **The two are linked:** in a recipe every resource is clickable and jumps
  straight to its locations.

  ⚠ **What the watcher does not say: whether you can craft it.** It knows your
  blueprints, not your cargo hold. "Needs 0.3 SCU Iron" — yes. "You can build
  this now" — never.

  For probabilities and the refinery comparison **scmdb.net** remains the better
  place; the page links there.

- **My stock — and what your material quality makes of the product.**
  Suggested by **Horthy (KRT)** 🙏

  You enter what resources you have: **material, amount, quality, location**.
  Every ingredient in a recipe then shows whether it is there or how much is
  missing — and a button **"Crafting this now"** subtracts the ingredients, so
  you do not have to do the arithmetic.

  **And quality genuinely matters.** The recipes carry how strongly it changes
  the values of the finished item — for **1,524 of the 1,597 blueprints**. So
  the recipe shows what *your* material would produce:

  ```
  With your material
     Damage Mitigation    × 1.044     Ouratite · Q 720
     Min Temp             × 1.088     Aslarite · Q 800
  ```

  If material is on hand but below the required quality, it says so — otherwise
  you would read "missing 0.3" while 12 SCU sit in your stock.

  **When adding, the watcher suggests the materials that actually exist** — 26
  of them, from the recipes. Type "Aslerite" and you are offered "Aslarite",
  instead of silently never getting a match.

  **The stock is a sortable table**: column headers for material, amount,
  quality and location sort on click, and from six entries on a filter appears.
  Two entries of the same material in different places stay cleanly apart.

  **The recipe shows what you already have** — not just what is missing: "have
  0.02 of 0.09 · missing 0.07". Otherwise you set off to fetch 0.09 when 0.07
  would do.

  **And you can try out a quality.** A slider from 0 to 1000 shows what better
  or worse ore would yield — the same question you would otherwise ask by hand
  on scmdb.net, only with your stock as the starting point.

  ⚠ **The stock is kept by hand**, because the game gives nothing away: 17 MB of
  logs contain not one word about resources or crafting. That is why the watcher
  never says "you cannot build this", only "you are missing Iron". A stock that
  lags two entries behind must not become a liar.

- **Your name in the bug report.** On the "Report a problem" page you can enter
  a name that appears at the top of the report, so follow-up questions can be
  matched to you. **Optional** — empty stays empty, and nothing is ever
  pre-filled.

- ⚠ **With many sources for one blueprint you could not scroll to the bottom.**
  Expanding the origins — the "Hart Scraper Module" has twelve — left the lower
  entries out of view and out of reach.

  > Cause: the scroll length is built from **estimated** row heights. That holds
  > while every row is the same height; an expanded blueprint is several times
  > taller, and the estimate knew nothing about it.

  The list now re-measures whenever a built section differs from the estimate,
  shifts the following ones and extends the scroll area. It does this by itself
  rather than relying on someone remembering it at each click site.

- ⚠ **The reset control in the blueprint list could not be found.** It existed —
  as a small grey underlined text at the bottom right, next to the result count.
  It was missed entirely and filters were cleared by hand instead. What you
  cannot find is not there.

  It now sits **at the top**, in the row with "all / owned / new in game", far
  right and set apart, as a framed button with an ×. It still appears only when
  something is actually narrowed down — and now clears **everything**: the
  dropdowns, the search box and the state selection.

- **The blueprint list starts without filters.** Setting "docking collar, size 2,
  grade A" and returning to the tab later showed "Nothing found" — easily
  mistaken for an empty inventory. Filters and search box are cleared on
  reopening.

- ⚠ **"With your material" was shown even when none of it was in stock.** The
  line on the right said "you are missing 1.2", yet a factor was calculated
  below — from the slider default, not from your material. Anyone reading that
  takes the factor for their own result. The heading now says what it shows:
  "What quality 500 would give", whenever a value is being tried or the stock
  holds nothing.

- **The search fields on Crafting and Mining kept their contents.** Searching
  for "titan" and returning to the tab later still showed only titanium — easily
  mistaken for the whole list. They are empty again on reopening.

  > Cause: a page is built **once** and only shown and hidden after that.
  > Anything that should be fresh has to register for it.

- **Both search fields have a × to clear them**, shown only when something is in.

- ⚠ **Buttons cut off their own labels** — one read "e change" instead of "Save
  change", and in the overlay the contract line ended mid-word. That is not
  cosmetic: someone reading half a word goes looking for a bug that does not
  exist.

  Cause: the surface was sized with `measure()` but drawn with whatever font the
  system provides — and under **Wayland** that is only settled once the window
  is shown. Every button now measures itself three times: when built, when first
  shown, and once when idle. If it grows, its frame grows with it. Applies to
  all buttons including filter rows.

- ⚠ **The overlay could be dragged narrower than its own icon bar**, hiding the
  bell and the icons on the right — at 290 px not one of them was visible. It
  now has a minimum width derived from that bar (measured: 520 px for the title
  and ten icons), and a too-small saved size is raised on startup.

  > The first attempt did nothing because it asked the bar for its requested
  > width — but that bar runs with `pack_propagate(False)`, deliberately not
  > passing on its children's size, and reported **1 pixel**. The elements are
  > now added up individually.

 

- **The contract line in the overlay wraps instead of being cut off.**

- ⚠ **An open window would not come to the front under Wayland.** Clicking the
  overlay appeared to do nothing and only restarting helped. Under Wayland a
  window may not raise itself; what the compositor does accept is a window that
  **re-registers** itself, and that is what now happens — only under Wayland,
  and only when the window really is covered. Keyboard focus stays with the game.

- ⚠ **Buttons cut off their own labels.** One button read "e change" instead of
  "Save change". Cause: the surface was sized with `measure()` but drawn with
  whatever font the system actually provides — where those differ, the text
  runs past the edge and is clipped on both sides. Every button now measures
  itself after its text is set. This affected all buttons, not just one.
 

- ⚠ **Stock entries could not be corrected.** After a typo or after handing
  material to someone else, the only option was to delete the entry and retype
  it — which easily created a second name for the same material. Now **clicking
  a row** opens it in the fields above: change amount, quality and storage
  location, save, done.

  > **Add and subtract instead of doing the maths.** With an entry open you can
  > type `+5` or `-2` to add or remove. Handed everything over? Type the full
  > amount with a minus and the entry disappears. You cannot subtract more than
  > you have; the available amount is shown instead.

- ⚠ **A typo in a material name quietly broke your stock.** The suggestions
  could be ignored: enter `Aslerite` and the list looked right — but no recipe
  found the stock, and nobody learned why. Names are now **matched**: case,
  the mining spelling with brackets (`Aslarite (Raw)`), `Aluminium` versus
  `Aluminum` and a close typo are pulled onto the correct name and reported. A
  completely unknown name is **queried** rather than stored — with an "Add
  anyway" button for the case where you really do have something no recipe
  lists.

- **The location field said "Location".** That belongs to mining. This is where
  your material **sits**, so it now says "Storage location" — and stays
  optional, since not everyone uses several places. **Amount and quality are
  required:** without quality the watcher cannot work out what your material
  does to the finished item, which is the whole point of the stock list.

- **Comma and full stop both work for amounts.** Some type `12.5`, others
  `12,5`. The comma used to raise an error.

- **Clicking the overlay now really brings an open window to the front.** It
  used to stay behind the game, and the click seemed to do nothing. Cause:
  `lift()` alone is ignored under **Wayland** — a window may not raise itself
  there. Now "always on top" is set briefly and switched off again, which the
  compositor accepts. A **minimised** window is restored too; it used to stay
  collapsed. Affects the blueprint list, settings and "What's new".

  > **Your game keeps the keyboard.** The window comes forward but does not
  > grab input focus — if you are flying, you keep flying. Click into the
  > window when you want to type in it. Only at startup does it take focus,
  > because you started it yourself.

- ⚠ **The quality slider stuttered because 4 MB were read from disk on every
  mouse move.** The recipe file was re-read on **every** access — 22 ms per
  call, and the slider fires on every pixel. That came to over 600 ms of
  computing per second. The data now stays in memory and is only re-read when
  the file actually changes: **0.33 ms instead of 21.9 ms**. On top of that,
  dragging now only relabels the values instead of rebuilding them, which took
  care of the remaining flicker.

- ⚠ **The new data never arrived for anyone who already had a catalogue.**
  The fetch stopped as soon as the blueprint catalogue was current — which it is
  for every existing user. Crafting, Mining and Stock would have stayed empty
  until the next Star Citizen patch. Both fetches are now **always** checked;
  they carry their own "already current?" test and load nothing twice.
- **The quality scale was shown wrongly.** In the stock the field read
  "Quality %" and values appeared as "720 %". The recipes work with **0 to
  1000**. Anyone reading "72" in game and entering that would have got wrong
  results throughout — their ore would count as unusable when it is good.

- **"Network error" where the site had simply refused the request.** A 403 is a
  refusal, not a loose cable: the tool now says so plainly, keeps working with
  the data it already has — and no longer retries three times (which cost six
  seconds for nothing).

### Thanks

The idea for the resource stock came from **Horthy (KRT)** — and out of it grew the quality calculation that now shows what your own material makes of a blueprint. Thank you 🙏

And **Krovax** (SCMDB), who set up a public data mirror on request so tools like this one have a dependable source.

## v3.2.1 - 2026-08-29

### Fixed

- **Other tools are no longer written over.** Three programs mark blueprint
  contracts in the game, and all three use the same `[BP]` mark: this one,
  **MrKraken's StarStrings** and the **SC Deutsch Launcher** (watcher and
  launcher even draw on the same data source, so they write word-identical
  lists). Until now the watcher did not tell its own marks from anyone else's.
  All counted against the real 29 Aug 2026 release:

  - **17** of MrKraken's marks were **deleted** when details were written — and
    because the watcher then remembered the already-trimmed wording as the
    original, they never came back on reset either.
  - **297** more ended up **twice**.
  - **136** item names got their tag twice:
    `[CS1] Spark-G Missile (CS1)`.
  - Anyone running the **SC Deutsch Launcher** alongside would have read the
    blueprint list twice over on **336** contracts, and lost the launcher's
    state on reset.

  **The new rule is simple: where a mark already stands, no second one is
  added.** And whatever was there before our first insertion belongs to the
  player — it is restored on reset, even when another tool put it there.

  With the launcher the watcher goes one step further: its list **replaces** the
  launcher's instead of sitting next to it. Because it is the same list — only
  with **tick boxes**, the comparison against your own blueprints. Take the
  details back out and the launcher's list is there again, character for
  character.

  If an item name already carries a tag in square brackets, it is left alone.

  **Thanks to MrKraken** for [StarStrings](https://github.com/MrKraken/StarStrings)
  and to the **SC Deutsch Launcher** team — and sorry for writing over your
  work. 🙏

- **The watcher reported "details are in the game" where none of its own were.**
  It recognised the injection by the `[BP]` mark and by the blueprint list
  heading — both of which the other two tools write as well. Now only what is
  unique to the watcher counts: the **tick box**.

- **Tick boxes appeared in front of regions and delivery points.** In the game
  you read `[  ] Stanton System - Danger 4-6/10`, as if a region were something
  you could own. Cause: the blueprint blocks are structured with headings, and
  three of them carry lists — `# Blueprints` (4,379 lines), `# Delivery` (323)
  and `# Region` (239). Every one of them got ticked. Now only what sits under
  **Blueprints** gets a box; that removes **838** wrong boxes from a finished
  file. Same in German (`# Baupläne`, `# Abgabe`).

- **Installing a new base clears the original-wording file.** It belonged to the
  old file and would have written back an outdated state. The same note also
  protects the fresh file: the watcher has never written into something just
  installed, so there is nothing of its own to remove there.

### Changed

- **MrKraken is now credited in the readme.** He had long been on the "Thanks &
  Licences" page in the tool, but was missing from the readme.
- **The licence stated for StarStrings is corrected.** It said "CC BY-NC-SA
  4.0". The project states no licence at all — not in the repository, not in its
  readme. Attributing a licence the author never granted is wrong; it now says
  "no licence stated".

## v3.2.0 - 2026-08-29

### Added

- **When you accept a contract, the watcher now tells you whether blueprints are
  part of it — and which of those you are still missing.** Until now you only
  found out once the blueprint arrived. It appears in the list the moment you
  accept:

  ```
  Contract accepted: Retake Platforms From Nine Tails
    →  3 blueprints · you are missing: H4-PBF Ammo Carrier
  ```

  This is deliberately **not** contract management: no list, no tab, no second
  window. Just a line, like a blueprint find. The tool does not take on a second
  job — it answers its own question earlier.

  **If the catalogue does not know the contract, it stays quiet.** A wrong
  promise about blueprints would be worse than no message at all.

  Acceptance is detected through the key `mobiGlas_ui_MissionEvent_Activated`
  from the game's own files rather than through the wording — in German the
  **sub-objectives** are also called "Neuer Auftrag", so wording alone would fire
  at every step. It works the same way if your game runs in English.

### Changed

- **The thanks to testers no longer sit in the readme.** They belong in the
  changelog and on the "Thanks & Licenses" page inside the tool, where they
  remain in full.

## v3.1.0 - 2026-08-29

### Added

- **Caught-up blueprints are now reported, not just added silently.** When the
  watcher finds something in the logs — on startup or at the push of the button
  — it appears in the list, marked *caught up* so it doesn't look like a fresh
  find.

  Up to ten individually; above that it stays with the summary in the status
  bar. The reason for that limit: on the very first start the catch-up goes
  through **every** stored session — on a well-used machine that is over a
  hundred, and nobody wants to dismiss those one by one. Day to day it is zero
  to three, and those are exactly the ones you want to see.

### Fixed

- **The same blueprint counted twice when the game runs in German.** The SC
  Deutsch Launcher reads the **English** catalogue and writes
  `Ravager-212 Twin Shotgun Magazine (16 cap)`. Re-reading the logs picks up the
  same crate in whatever language Star Citizen runs in — in German
  `… (16 Schuss)`. To the Watcher those were two different blueprints.

  Measured against a real inventory: **405 shown, 403 actually held.** The bug is
  silent — nothing breaks, the number is simply too high.

  The quantity in brackets is now language-neutral: `(16 Schuss)` and `(16 cap)`
  are the same blueprint. **The number stays** — a 40-round and a 60-round
  magazine are different blueprints and must remain so. Brackets that do not
  start with a digit are untouched, so `Singe Cannon (S2)` keeps its name.

  An inventory already on disk is migrated on the next start: duplicates are
  merged into one entry, and the **older** find wins.

- **"Start with the system" never worked on Linux.** The Watcher wrote the
  AppImage's **temporary mount point** (`/tmp/.mount_SC-BP-ji95vH/…`) into the
  autostart file. That path gets a new random name on every launch, so after a
  reboot the entry pointed nowhere and the Watcher did not come up — with no
  error message, because the file looked perfectly fine.

  The cause was the order in the code: an AppImage also counts as "frozen", so
  that branch won and the real AppImage path was never reached. Now reversed.

  Found on 29 Aug 2026 on a machine where the entry had been dead ever since the
  move to Linux.


- **The floating lock sat seven pixels too far right.** The offset for it came
  from a measurement on a **different screen** (5120×1440 instead of 4096×1152)
  — symbols are 24 px wide there instead of 22, and an offset measured in pixels
  applies to exactly the one screen it was measured on.

  Measured again on the running program: without the offset it sits exactly on
  target. It is back to zero.

## v3.0.3 - 2026-08-28

### Fixed

- **Three places showed the key name instead of the text.** Most visibly on the
  rocket icon: its tooltip literally read `s_sp_start`. It now says what was
  meant — "Launch Star Citizen".

  The other two would have surfaced on the next failed download and in the
  version window.

  The cause is a fallback that hides too well: if the language table does not
  know a key, it returns **the key**. That beats crashing — but the fault stays
  invisible until someone sees it in the running program.

  The self-test now checks this: it collects **every** call with a fixed key
  across the program and matches it against the table. With over 600 entries
  that cannot be done by hand — and it was this check, not a person, that found
  all three.

  Reported by **der Autor** on 2026-08-28.

### Changed

- **It said "check daily for new versions", but checked hourly.** The interval
  has always been one hour; the text beside it said otherwise. It only came up
  once the check actually started repeating.

## v3.0.2 - 2026-08-28

### Fixed

- **A running watcher never learned about a new version.** The notice only
  appeared after a restart — anyone leaving the program running for days never
  saw it.

  It looked **exactly once**, two seconds after startup. The hourly interval in
  the check only limits how often it *may* ask; someone still has to ask. That
  now happens every hour.

  Reported by **der Autor** on 2026-08-28: v3.0.1 was out and the running watcher
  stayed quiet — even though it had already fetched it and had it in its cache.

- **An expected error made the problem report useless.** While downloading,
  progress arrives every second; if the window closes during that, every single
  update fails — caught, but logged each time.

  In one report that filled **50 of 50** slots with the same line, all within
  eight seconds. Every real error had been pushed out. This message is now only
  recorded the first time.

## v3.0.1 - 2026-08-28

### Fixed

> [!important]
> **If the watcher was closed while Star Citizen kept running, that session's
> blueprints were lost** — permanently. If that sounds familiar: press the new
> **Read the logs again** button once and they are back.

- **The running `Game.log` was only read on the very first start.** After that
  it counted as done: live reading resumed at the remembered position, and
  everything before it was unreachable. The file only moves to the backup folder
  on the next game start — until then the blueprint was missing with nothing to
  hint at it.

  Measured: the blueprint sat at byte 11,987,664, the read position at
  12,759,872. It would never have been found.

  The running file is now read in full on every start. That costs a fraction of
  a second — the catch-up goes through every stored log anyway — and duplicates
  cannot happen, the inventory checks every name.

  Reported by **der Autor**, hours after v3.0.0.

- **After a game restart the read position jumped to the end of the file instead
  of the start.** When Star Citizen creates a fresh `Game.log`, it is shorter
  than the remembered position. The comment there correctly says "a new game
  session has run" — but the code set the position to the **end** of the new
  file instead of reading from the beginning. Everything the fresh session had
  already reported was skipped.

### Added

- **A "Read the logs again" button** — in the overlay's title bar and in the
  settings under *Inventory*. It goes through every stored session again,
  including the ones already read, and fills in what is missing.

  It also helps when the game language was not yet detected on the first run:
  the logs were then searched with the wrong wording and still marked as read.

### Changed

- **Two texts that were no longer true.** The lock's hint described it as
  sitting "at the top right of the overlay" — it hasn't since v3.0.0. And the
  settings text still pointed to a second program start as the way back, even
  though the lock exists for exactly that.

## v3.0.0 - 2026-08-28

> [!important]
> **On Windows there is now an installer instead of a single `.exe`.** Updating
> therefore opens an installation window once — that is correct and not foreign
> software. The watcher restarts by itself afterwards. On Linux it stays one
> file: the AppImage.
>
> **The SC Deutsch Launcher is no longer required.** Blueprints come from Star
> Citizen's own `Game.log`. With the launcher you keep German names and a few
> extra details — without it (always the case on Linux) nothing essential is
> missing.

A year after the first build, the narrow notification bar has grown into a tool
that fully answers „which blueprint do I have, and where do I get the rest?" —
without leaving the game.

### The main points

- **One window with everything in it.** Blueprint list to search and tick off,
  progress by area, settings, server status, „What's new" — instead of scattered
  little windows.
- **Where each blueprint drops.** One click shows the faction, the contract, the
  standing required and the payout — for **655 of 722** blueprints, sorted by
  the easiest route. „I'm missing X" is half the information; „X drops at
  Foxwell from Veteran" is all of it.
- **New in the game.** A filter shows what the current patch brought, and a
  dropdown next to it every earlier patch. Every blueprint carries the game
  version it first appeared in.
- **Details inside the game.** The watcher writes into contract texts **which**
  blueprints a contract hands out — with `[x]` for the ones you already have.
  And on request class, size and grade onto item names, so the tractor beam
  reads „Glacier (Mil/1/A)" rather than just „Glacier".
- **The overlay gets out of the way.** On request it only pops up briefly when a
  blueprint arrives; mouse clicks can be passed through to the game, and a lock
  in the bar brings it back. It can also fold down to just its title bar.
- **Reporting problems without guesswork.** A red button collects system,
  version, game state and the last errors into one report — no names, no paths.
  That is why the bugs in this changelog are described so precisely.
- **German and English, completely.** Switchable in the program. The blueprint
  message in the log is recognised in **any** game language — the watcher works
  out the wording by itself.
- **Windows and Linux from one codebase**, with autostart, self-update and a
  tray icon on both.

### Thanks

Without these three, v3.0.0 would be markedly worse. They tested on their own
machines and described faults well enough to find them:

- **Bomb20** (pr0) — that the tool could not be kept up to date on Linux, plus
  the crash on the very first start and a morning with four finds that would
  otherwise have hit every user.
- **Haldjas** (pr0) — pop-up mode and click-through go back to him; so does the
  way **there and back** for click-through, the installer that failed on the
  running file, and the console windows during updates.
- **Morkhan** — the item details in game, and the find that
  several reward tiers of one contract were overwriting each other in the
  catalogue: **797 blueprints** nobody had ever seen before.

The complete list of every single change is in the `v3.0.0-rc1` to `v3.0.0-rc99`
sections below.

## v3.0.0-rc99 - 2026-08-28

### Fixed

- **The green lock did not sit exactly on the lock in the bar.** A narrow edge
  of the symbol underneath showed on the right — it looked like two locks
  instead of one changing colour.

  The offset was **measured** from a screenshot, not estimated: the upper lock
  sat at x=1068–1091, of the lower one only x=1094–1098 was visible. At 24 px
  wide the lower one therefore starts at 1075 — **7 px further right**. The
  upper one now moves by exactly that.

  ⚠ The value is measured, its **cause is not known**: in a rebuild with the
  same Tk version and the same symbols, the lock sits exactly right without any
  offset. It is therefore a named constant in one place, and applies only to the
  visible state — pop-up mode calculates differently and is left alone.

## v3.0.0-rc98 - 2026-08-28

### Fixed

- **The lock was more opaque than the overlay beneath it.** With transparency
  turned down, passing clicks through showed two locks of different saturation
  on top of each other — the one in the bar showed through, the one above it did
  not.

  A separate window does **not** inherit the main window's transparency; it has
  to be given its own. Both now carry the same value, and it looks like one lock
  changing colour — as intended.

## v3.0.0-rc97 - 2026-08-28

### Fixed

- **On a second screen, the strip and lock jumped to the wrong monitor.** This
  affected pop-up mode: if the overlay sits on a monitor **above** the main
  screen, the green strip and its lock reappeared at the top edge of the main
  monitor.

  A monitor above the main screen works with **negative** Y values — that is a
  valid position, not a broken one. Remembering the position accounted for it;
  displaying it threw it away again: a `max(0, …)` clamped every height below
  zero to the top edge of the main monitor.

  The strip carried that line from the start; the lock inherited it when it
  moved next to the strip in rc94. Both are rid of it.

## v3.0.0-rc96 - 2026-08-28

### Fixed

- **On hiding, the lock took three seconds to return to its place.** When the
  overlay hides itself in pop-up mode, the lock belongs back at the handle
  strip — instead it stayed where the bar had just been.

  It was **exactly** the ten 300 ms retries from rc92. Those are meant for
  startup, where the bar is about to appear: while it is still being drawn, the
  lock waits instead of jumping to a guessed spot. But that waiting also ran
  when the overlay had **deliberately** gone away — waiting for something that
  is not coming.

  Both cases look the same at the button, but not at the window. Measured:

  | Case | Window | Button |
  |---|---|---|
  | startup, still being drawn | 1 | 0 |
  | deliberately hidden | 0 | 0 |

  The window is now asked. If it is gone, the lock moves at once.

  Reported by **Haldjas (pr0)** on 2026-08-28, including the exact separation
  from the six seconds the overlay itself stays up.

## v3.0.0-rc95 - 2026-08-28

### Changed

> [!important]
> **A found blueprint is green from now on — no more yellow „provisional".**
> Anyone with the SC Deutsch Launcher installed saw every find from the
> `Game.log` in yellow first, until the launcher confirmed it. That confirmation
> no longer exists, and neither does the yellow waiting.

- **The waiting state is gone, not just the colour.** The yellow dot meant „read
  from the Game.log, waiting for the launcher to confirm". Since the `Game.log`
  is the source and the launcher only adds to it, that confirmation can never
  arrive.

  What remained was a state with no way out: with the launcher you saw permanent
  yellow — without it permanent green, at **exactly the same certainty**. Two
  colours for one statement are not information, they are a dead end.

  The whole mechanism went, not just the display: the register of unconfirmed
  rows, the matching of log names to launcher keys, the after-the-fact
  confirming of a row, the word „provisional" — and the yellow dot in the
  documentation, so nobody hunts for a symbol that does not exist.

  The launcher stays what it is: an addition. German names, maintained details
  for type, size and grade, and it reports anything the log missed.

## v3.0.0-rc94 - 2026-08-28

### Improved

- **In pop-up mode the lock now sits by the handle strip.** It sat at the top
  right corner of the remembered overlay position — correctly calculated, but
  on its own: the strip that shows where the overlay is waiting sits centred,
  with the lock a good two hundred pixels further right, where there is nothing
  to see.

  Two markers for the same thing belong together. It now reads as one: this is
  where the overlay waits, and this is the lock.

  Reported by **Haldjas (pr0)** on 2026-08-28.

## v3.0.0-rc93 - 2026-08-28

### Fixed

- **In pop-up mode the lock floated beside the overlay.** The rc92 fix worked
  for everyone who keeps the overlay visible — in „only on a new blueprint"
  mode the old behaviour remained.

  The reason: there the overlay is **hidden** at startup, before it has ever
  been drawn. That leaves no bar for the lock to align with, and the fallback
  used the position of an invisible window — measured, a never-drawn window
  reports width 1 and position 0. The lock ended up somewhere beside the
  overlay.

  It now hangs off the same remembered position as the handle strip, which in
  pop-up mode already shows where the overlay is waiting — and moves onto the
  bar as soon as the overlay pops up.

  Reported by **Haldjas (pr0)** on 2026-08-28. His problem report settled it:
  without the line `overlay_modus=popup` in it, why this hit him and not others
  would still be guesswork.

## v3.0.0-rc92 - 2026-08-28

### Fixed

- **After a restart the lock sat beside the overlay instead of on it.** Anyone
  who had click-through saved as on saw **two** locks after every start: one in
  the wrong place next to the window, one in the title bar. Only the first
  toggle moved it into place — and the next start began the same thing again.

  The cause is an old `tkinter` trap: the state is applied immediately before
  the window loop starts. The bar is already in the tree by then, but Tk has
  drawn nothing yet — neither „is visible" nor the measurements are true at that
  moment. So the lock went to a guessed position.

  It now **waits instead of guessing**: while the bar is not yet drawn, no lock
  is built at all; it retries until the bar is there. A briefly flashing lock in
  the wrong place would only have been half a fix.

  Reported by **Haldjas (pr0)** on 2026-08-28, with the full steps to reproduce.

## v3.0.0-rc91 - 2026-08-28

### Improved

- **One lock instead of two.** The green lock used to sit in the overlay's
  corner while the title bar still showed an open one — two locks, one of them
  stating the opposite of the truth.

  The green lock now sits **exactly on top of** the one in the title bar: same
  place, same size, same component. To the player it is one lock changing
  colour — closed and green means „clicks go to the game", open and grey means
  „the overlay catches them". You unlock where you locked.

  It remains a **separate window**, and that cannot change: passing clicks
  through applies to the whole window — a button in the bar would be just as
  unreachable as the rest. If the bar is collapsed or the overlay hidden in
  pop-up mode, the lock falls back to its old place in the corner.

## v3.0.0-rc90 - 2026-08-28

### Improved

- **The lock now sits permanently in the overlay's title bar.** Passing clicks
  through to the game was only reachable via Settings → Overlay; getting back
  was comfortable, through the lock that appears while it is active.

  A way there and back belongs in the same place. The title bar therefore
  carries an **open** lock — it means „the overlay catches clicks". One click
  closes it, and from then on the floating lock at the top right takes over, as
  before. No more detour through the settings.

  The button only appears where the system can pass clicks through at all —
  under native Wayland it would do nothing. Should it fail against expectation,
  the setting is rolled back rather than storing an „on" that has no effect.

  Suggested by **Haldjas (pr0)** on 2026-08-28.

## v3.0.0-rc89 - 2026-08-28

### Fixed

- **The dropdown promised more than the list showed.** After the patch-history
  fix it read „4.10.0 (24)" — with three rows below it.

  Two causes, both the same kind of mistake:

  **Two sources for one question.** The dropdown counted the history, the
  filter checks the `seit` stamp in the catalogue. But the number in brackets
  is a promise about how many rows will appear. It now counts the catalogue —
  what is not stamped cannot be shown anyway.

  **And the stamp arrived too late.** It was only caught up during the network
  tick, which runs at some point after startup in its own thread. Measured on
  2026-08-28: window built at 10:44:02, catalogue stamped at 10:44:03 — one
  second too late, and the list stayed wrong until the next opening. The window
  now catches the stamp up itself, **before** it reads the catalogue. This hits
  every user on the first start after a build with new history.

## v3.0.0-rc88 - 2026-08-28

### Fixed

- **The patch filter lost almost the entire patch.** The dropdown read
  „4.10.0 (3)" and the list showed three ship weapons. In truth 4.10.0 brought
  **24** blueprints — the 21 shipped ones had vanished from the view.

  Cause: the program layered its own observed history on top of the shipped
  one. For the same game version, the local one won outright. But what the
  program records itself is only ever the **increase since the last run** —
  here three weapons the source added two days later. Read as a complete patch
  list, that is bound to be wrong.

  Both lists are now **merged** rather than replaced, and the earlier date
  wins. The same applied to two local findings in a row: the second erased the
  first. That is fixed as well.

### Improved

- **The diagnostic report now states the patch history.** A new line below the
  catalogue state: which game versions the history holds, and with how many
  blueprints — for example `4.10.0 (24)`.

  The bug above could hide because the report only showed the catalogue state.
  That was perfectly fine; the history below it was not. Anyone reporting „the
  patch filter shows almost nothing" now has the numbers right there, with no
  need to open a file first.

## v3.0.0-rc87 - 2026-08-28

### Improved

- **Confirmation dialogs now look like the rest of the program.** Three
  places still showed Tk's grey system box: a light panel inside a dark window,
  a foreign font — and narrow and tall, turning a longer sentence into a column.

  It is now a dialog of its own, in the same colours and with the same buttons
  as everywhere else, **wide rather than tall** (620 px), centred over the
  window. Enter means yes, Escape means no.

  Affects: switching the text source · sending a problem report · resetting the
  inventory.

  The requirement behind it: the dialog should carry the program's own design —
  and be wide rather than tall.


- **The "In-game text" page now follows the order you read it in.** The text
  source first — where the base text comes from — then what gets written into
  it: blueprint details first, then the details on the item itself. Previously
  the write switch sat above the source it depends on.

### Fixed

- **Dialogs had German text but English buttons.** Switching the text source
  showed "Einsetzen?" above buttons labelled **Yes** and **No**.

  Those buttons do not come from the program's own language file but from Tk's
  own table — which is incomplete on many Linux systems. Measured on
  2026-08-28: Tk's locale was already set correctly to `de_de`, yet the German
  words were simply missing from the installation. On Windows Tk ships them,
  which is why it never showed up there.

  The program now supplies the words itself, and updates them on a language
  switch instead of setting them once at startup.

## v3.0.0-rc86 - 2026-08-28

### Fixed

- **Asterisks showed up as plain text on the "In-game text" page.** The
  explanation of the text source read "after that the `**entire game**` is in
  that language" — asterisks included.

  The `**bold**` markup in the language file is meant for whoever reads that
  file; a Tk label cannot mix formats and simply displays it. The credits page
  already stripped it, the settings rows did not — the same job in two places,
  one of them forgotten. Both now go through the same function.

  Spotted in a screenshot of rc85. The self-test had missed it: it looked for German text in the English interface, not for
  markup. **It now checks for this too** — and the check was verified by
  putting the bug back in.

## v3.0.0-rc85 - 2026-08-28

### Fixed

- **On Linux, description texts were cut off instead of wrapping — pushing the
  switches out of the window.** Every page with body text next to a control was
  affected: "In-game text", "Inventory", "Report a problem". At small window
  sizes sentences ended mid-word, and the switches on the right could not be
  reached at all.

  The cause sits one level deeper than it looks. The function that ties line
  wrapping to the window width asks the label for its own border size. Depending
  on the build, Tk returns such a measurement as a number, as text, **or as a
  Tcl object** — and on the last one `int()` raises a `TypeError`. Only
  `TclError` and `ValueError` were caught, and a `TypeError` is neither. So the
  error escaped and ended the function **before** it could set the wrap width.
  The text stayed on one long line — exactly the state this function exists to
  prevent.

  Why it surfaced only now: the Tk in the Windows build returns these values as
  numbers, the Tk in the Linux AppImage as Tcl objects. The bug could not occur
  on Windows.

  Spotted during the first Linux test round after updating to rc84 — first by
  the cut-off text, then confirmed in the problem report: **50 out of 50** recorded errors came from this single line.

  Measurements are now read with Tk's own converter, which understands all three
  forms. The same trap was present at two further points in the wrapping code
  and was removed there as well.

- **Uninstalling left the autostart entry behind.** The registry kept pointing
  at a file that no longer existed — Windows tried to start it at every sign-in
  and failed silently.

  The reason: the entry is written in **two** places. The installer creates it
  when you tick "Start with Windows" during setup, and it cleans up exactly that
  case. But turning autostart on **inside the program** writes the same value —
  and the uninstaller knew nothing about it.

  Spotted while cleaning up after a test run. It is the same autostart that made the update fail earlier that morning (code 5) —
  it was only half handled at both ends.

  The uninstaller now always removes the value, no matter who set it. Only that
  one value — autostart entries of other programs are left alone.

## v3.0.0-rc84 - 2026-08-28

### Fixed

- **Updating failed when autostart cut in halfway through.**
  Measured while updating rc75 → rc83: the installer got halfway and then stopped with

      An error occurred while trying to replace the existing file:
      DeleteFile failed; code 5. Access is denied.

  The Windows Restart Manager was **not** at fault — it had done its job. The
  setup log shows the whole chain:

      05:43:47  Shutting down applications using our files. (forced)
      05:43:55  << the watcher is running again — parent process explorer.exe >>
      05:44:17  DeleteFile: The existing file appears to be in use (5).

  Eight seconds after the shutdown, **autostart** brought the program back up.
  Windows processes autostart entries with a delay after `explorer.exe` starts;
  if the shell had restarted shortly before (a crash, a fresh sign-in), that
  delay lands right inside the running installation. The proof is the **parent
  process**: `explorer.exe` — had the watcher restarted itself, something else
  would be there.

  Deleting the running program cannot win that race: the installer closes it
  **once**, and it never sees what comes back afterwards. On its own it only
  retries four times, one second apart.

  The installer now follows up immediately before copying and terminates a
  program that has come back — three times in short succession, so it also
  catches an autostart firing at that very moment. Only on **updates**; a fresh
  installation waits no longer than before.

### Changed

- **A switch that says "off" now actually turns things off.** Both switches on
  the "In-game text" page only stored the setting — the text file was left
  untouched until someone pressed "Write now" under "By hand". Anyone who
  turned the details off, restarted the game and found everything unchanged
  concluded the tool was broken.

  The status box above made it worse: it promised "changes take effect the next
  time you start the game" — precisely what was not true.

  Measured while testing: switch off, status line reported "off", and **1,217**
  details were still sitting in the text file. The same trap caught a second
  switch, even though the note sat right next to it — the bold part gets read,
  the smaller one does not. That
  settled it: a note in the small print is not a fix.

  Flipping a switch now takes effect immediately — off means gone, on means
  there. Nothing is lost: the original wording is remembered and restored
  exactly when the details are removed. If something does remain, the status
  box now says so instead of reporting "nothing is being written".


- **"Launch Star Citizen" no longer appears twice.** The "In-game text" page had
  its own section for it — even though the button sits permanently in the
  bottom left of the sidebar, reachable from every page. The section is gone;
  the sidebar button is unchanged.

## v3.0.0-rc83 - 2026-08-28

### Fixed

- **The report now says whether the blueprint notes are in the game.**
  The most common support case is "I can't see your notes in the game any
  more". Behind it is almost always the same thing: a translation update or a
  game patch rewrote the game's text file and silently threw the notes out.
  The tool has no way of noticing.

  Until now the report only said which text source was selected — whether
  anything was actually in place could not be read from it, only guessed. That
  is exactly what happened with **Morkhan** on 28 Aug 2026.

  Two lines are new: whether the notes are in place, whether writing them is
  switched on at all, whether they are refreshed automatically — and which text
  file is meant. Anyone playing on Linux without a translation gets **no**
  warning: there is no such file there, and that is the normal state, not a
  fault.

- **Text was cut off instead of wrapped — everywhere it got tight.**
  It showed up in one place: the English warning line on the Game page ("Every
  translation update and every game patch wipes the details.") stuck out by
  5 pixels and was silently clipped.

  The cause was not the text but a sum with a missing term. The wrap limit
  bounds the **text** only; what a label ends up occupying is text plus border
  plus padding. With the limit set to the full available width, the label
  needed a few pixels more than it was given — and Tk clips an oversized child
  at its parent without an error or any other sign.

  The border is now read from the widget itself rather than guessed, and
  subtracted. This applies to **every** place that wraps automatically,
  including those that just barely fit today and would have tipped over with
  the next longer string. Measured afterwards: nothing is clipped any more,
  across 11 pages × 2 languages × 2 window sizes.

## v3.0.0-rc82 - 2026-08-28

### Fixed

- **A contract with several payout tiers lost nearly all its blueprints.**
  Contracts sharing a text key overwrote each other while the catalogue was
  built — the last one read won, the rest were dropped. Measured against game
  build 4.10.0: **123 of 353** contract keys are shared, **319** contracts were
  dropped, and **797 blueprint entries** were never shown to anyone. The bounty
  contract listed 8 blueprints instead of 25.

  Found by **Morkhan**, who kept pushing: "I still don't get shown which
  blueprints I can get from the beginner contract, only the ones from the
  highest tier." It wasn't the highest tier — it was the last one read. All
  tiers are now merged.

- **A catalogue already on disk would never have picked up this rebuild.** It
  was only refreshed when Star Citizen shipped a new version. It now carries
  its own build number — if its structure changes, it is rebuilt, patch or no
  patch.

### Changed

- **The heading now reads "POSSIBLE BLUEPRINTS FOR THIS MISSION TYPE".** It
  previously said "BLUEPRINTS FROM THIS CONTRACT" — promising more than the data
  can deliver. Read literally, you accept the contract and get nothing. Morkhan
  on 28 Aug 2026: "it's confusing no matter how you turn it." He was right, and
  the confusion sat in the heading, not in the list.

  The SC Deutsch Launcher words it the same way for the same reason — 367 times
  in its data file.


- **The `[BP 3/12]` count in the title is gone; it now reads just `[BP]`.** The
  number looked useful but was not true: a contract's list merges all payout
  tiers, and which of them your own tier grants cannot be resolved — 123 of 353
  contracts share their text key across tiers. "3 of 12" really meant "3 of 12
  that someone, somewhere, can get". The same number is gone from the list
  heading too.

  What remains is the honest part: **ticked means you have it** — regardless of
  whether this tier grants it, or where it came from.

- **Where tiers differ, the required rank is shown behind the blueprint.** For
  example "needs Head Contractor (38,000 XP)" next to plans only available far
  up, while others from the same contract drop from 800 XP. Shown only where it
  actually tells blueprints apart — if they all need the same rank, it is
  already stated above under "Min. reputation".

- **Contracts with tiers that grant nothing now say so.** "Note: 1 of the 3
  tiers of this contract give no blueprints at all."


### Changed

- **The „Diagnostics" tab is now called „Report a problem" and carries red.**
  Nobody looks under „Diagnostics" when something is stuck — least of all
  inside a collapsed menu, where it used to sit.

  The red works in two stages so that it means something: **the word is always
  red**, so the tab can be found. **The icon only turns red when errors have
  actually been recorded** — otherwise the watcher would sit on permanent alert
  while everything is fine, and nobody would take the colour seriously.

### Fixed

- **Revisiting a page left no trace in the report.** It was only written while a
  page was first built; if something went wrong on a later visit, the line was
  missing entirely rather than half — and the report promises that the last line
  without „ready" is where it stopped. It now says „showing", so you can tell
  „died while building" from „died while showing".
- **The error report only scrolled once the page was at the bottom.** The mouse
  wheel went to the page behind instead of the text field under the pointer, so
  you had to push the whole diagnostics page down before anything moved inside
  the report. Now whatever sits under the pointer scrolls, the way browsers do
  it. Reported by **Morkhan**.
- **The send button is red all the time**, not only on hover — a warning button
  you only see once the mouse is on it warns nobody.
- **The second reporting route is now called „GitHub issue"** instead of
  „Report a problem". Two buttons promised the same thing, while one opens the
  browser and needs a GitHub account.

## v3.0.0-rc81 - 2026-08-28

> **One button instead of nine steps: send the error report.**

### Added

- **The diagnostics page now sits in the main sidebar**, right below
  „Server status“ — no longer inside the collapsed „Advanced“ menu. Anyone
  who needs it has a problem, and will not look for it under a heading that
  reads „not for me“.
- **A red „Send error report" button.** If something is stuck, you press it —
  and the report is with the developer. No copying, no hunting for the right
  channel, no „message too long".

  It used to take nine steps: expand, copy, find Discord, paste, discover it is
  too long, save as a file, find that file again, upload, send. Now it takes
  one.

  **You see exactly what goes out beforehand** — the same text shown on the
  page, in a window to read through, and only then are you asked. Names, paths
  and credentials have already been stripped. Nothing happens without your
  yes.

## v3.0.0-rc80 - 2026-08-28

> **Blueprints from the launcher get ticked off again — existing collections migrate themselves.**

### Fixed

- **Blueprints from the launcher or a backup were not ticked off.** Anyone
  bringing their collection over from the SC Deutsch Launcher, the KRT Profit
  Basetool, scmdb.net or their own backup saw empty boxes in the list — even
  though the blueprints were in the collection.

  The reason: names from those sources often carry the class suffix
  (`XL-1 (Mil/2/A)`), but it was only stripped when reading the game logs. So
  `xl-1 (mil/2/a)` and `xl-1` stood there as two separate entries and never
  found each other. That now happens centrally, no matter where a name comes
  from.

  This hit precisely those who have been playing longer and bring their
  collection with them. Found while following up a report from **Morkhan**.

  **Existing collections migrate themselves on first start.** The keys are
  rebuilt once and duplicate entries merged — the older find wins, because when
  a blueprint first turned up is the date that matters. Nothing is lost, nothing
  has to be done by hand.

- **The tool did not say that changes only take effect the next time the game
  starts.** Star Citizen reads the text file **once, while launching**. Anyone
  with the game running would install the details, read „in place (1608
  spots)" — and see nothing in game. The obvious conclusion: broken. The note
  now sits in the success message itself and in the status box under *In-game
  text*.

## v3.0.0-rc79 - 2026-08-28

> **Three finds from Morkhan's questions — one would have silently swallowed blueprints.**

### Fixed

- **Blueprints whose name carries a suffix stopped being ticked off.** Now that
  item details are written in, the game puts the name **including the suffix**
  into its log — `Blueprint received: Spectre (Sth/1/A)`. Only the five faction
  suffixes were stripped; everything new stayed stuck to the name, and the
  blueprint went into the collection under the wrong one. **344 weapons and 62
  missiles** would have been affected — and nobody would have noticed, because
  something was still being displayed. Found while following up a question from
  **Morkhan**.

- **A mission promised „12 blueprints" in its title and showed none below.**
  A mission has **more descriptions** in game than the catalogue knows —
  different destinations and cargo for the same mission. Measured:
  `Covalex_HaulCargo_SingleToMulti` lists three descriptions in the catalogue,
  the game's text file holds **eight**. Anyone hitting one of the other five saw
  the counter and nothing underneath. The route via the SCDL team's contract
  data had long solved this; our own route via the blueprint catalogue had not.
  Reported by **Morkhan**.

### Added

- **An exclamation mark in the contract title when blueprints come with
  conditions.** `[BP 0/19!]` instead of `[BP 0/19]`. In **332 of 818 contracts**
  (41 %) blueprints only drop at certain payout tiers or from a given rank —
  „only for the 256,500 / 264,000 aUEC mission", „only from Master rank". That
  was in the description text, but the contract list only showed the counter,
  and that is what you decide on. Reported by **Morkhan**, who flew a hauling
  mission repeatedly in which none could ever drop.

  ⚠️ Why it cannot be cleaner: all payout tiers of a mission share **one**
  description text in the game. Star Citizen shows the small variant the same
  text as the large one — there is no way to tell them apart.

## v3.0.0-rc78 - 2026-08-28

> **Passing clicks through to the game is no longer a one-way street.**

### Added

- **A lock on the overlay brings you back when clicks pass through to the
  game.** Until now this was a one-way street: turning the setting on made the
  overlay unreachable — no button, no bar, and certainly not the settings
  themselves. The only way back was starting the program a second time. Which
  means leaving the game — exactly what the setting is meant to avoid.

  There is now a small lock at the top right of the overlay, the one thing that
  stays clickable. One click and the overlay catches clicks again. It only
  appears when clicks really do pass through, and disappears by itself — also
  when you switch it over in the settings.

## v3.0.0-rc77 - 2026-08-27

> **„Original texts from the game" now works without a helper program.**

### Fixed

- **Choosing the „Original" text source often ran into a wall.** That source
  takes the English `global.ini` straight from your own `Data.p4k` — no
  download, no third-party translation. CIG compresses that file with **zstd**,
  though, and the bundled Python could not handle it. What was left was a
  message asking you to install 7-Zip — quite something for a tool you just
  download and run.

  The program now brings the decompressor along itself. This mainly affected
  anyone **playing in English who only wants the item details**, without a
  translation: for them this route was the only one.

  If you installed 7-Zip solely for this — you no longer need it.

## v3.0.0-rc76 - 2026-08-27

> **The tractor beam now tells you what you are looking at — and on Windows
> there is only one route left.**

> [!important]
> **Windows: the installer is the only download now.** The standalone
> `SC-BP-Watcher.exe` is no longer attached to releases as of this version.
>
> The reason concerns you, not us: an update used to place the new version
> **beside** the old file instead of replacing it. Anyone clicking their usual
> shortcut afterwards kept using the old version for months without noticing.
> With the installer that cannot happen.
>
> **If you have been using the standalone file:** download
> `SC-BP-Watcher-Setup.exe` once and install over it — your blueprint
> collection stays, it lives elsewhere anyway. You can delete the old file
> afterwards. Nothing changes on Linux.

### Fixed

- **On Windows there is only one download now: the installer.** The standalone
  `SC-BP-Watcher.exe` is gone.

  **What you get out of it:** no more wondering which of the two files is the
  right one. The watcher ends up in your start menu instead of sitting
  somewhere in your downloads folder. Updates genuinely replace the program
  rather than putting a second copy next to it — the most common reason someone
  keeps using an old version for months without noticing. Autostart is a
  checkbox during setup, and *Apps & Features* removes everything cleanly.

  The standalone file dates from the early days: an unsigned program without an
  installer looks less alarming, and the point back then was to earn trust at
  all. That is done — and two routes side by side mean twice as many places
  where something can go wrong. Better one route that works.

  Nothing changes on Linux: the AppImage stays.
- **Anyone still on v2.0.0 comes along anyway.** Their update path picks the
  first file ending in `.exe` — which is now the installer — and starts it
  afterwards. So it runs by itself and sets everything up properly. The
  blueprint collection moves across automatically on first start.
- **An update now installs where the program already is** — instead of putting a
  second copy beside it. v2.0.0 shipped only as a bare `.exe`, so all of its
  users run „portable" without ever choosing to. Without this, the installer
  would have gone to `%LOCALAPPDATA%\Programs` on the update after next and left
  the old file behind — anyone starting it from a shortcut would have kept
  using the old version forever.

### Added

- **Details on the item — class, size and grade now sit next to the name.**
  Aiming at something with the tractor beam used to show just „Glacier". It now
  reads **„Glacier (Mil/1/A)"** — military, size 1, grade A. Missiles are judged
  by something else, so they carry their seeker instead: **„'Arrow' I Missile
  (IR1)"** for infrared, `EM` for electromagnetic, `CS` for cross-section.
  Nobody expands a description mid-fight.

  **856 items** get such a note: 450 with class, size and grade, 344 weapons
  with their class (ballistic, laser, plasma …) and 62 missiles.

  The details come from the game's **own** text file — they have always been
  there, just inside the description you have to open first. The tool merely
  moves them to where you can actually see them.

  Suggested by **Morkhan**.

  Can be switched off under *In-game text → Details on the item*. To undo it,
  use „Remove again" — the original names come back to the character.

## v3.0.0-rc75 - 2026-08-27

> **The startup trace is back in the report.**

### Fixed

- **Usage pushed the startup trace out of the report.** rc74 wrote startup steps
  and page switches into one list, and the report only shows the last twelve
  lines — five clicks were enough to hide the entire startup. Precisely the part
  the trace was built for. Both now appear as **two separate sections**, each
  capped on its own; trimming the file keeps the startup part as well. Found in
  the first rc74 report, fifteen minutes after release.
- **The diagnostics page was the last line of its own report.** The report is
  built while that page is being drawn, so every trace ended with "Page
  diagnostics: building" and looked as if that was where it stopped. Those lines
  are now left out.

## v3.0.0-rc74 - 2026-08-27

> **A crash now leaves a trace.**

### Added

- **Hard crashes are recorded.** Until now the tool only caught Python errors.
  A crash that kills the process mid-instruction (from inside the Tk library,
  say) left **nothing behind**: no entry, no message, nothing to attach. From
  now on a handler writes the call path of every thread to a file, and the next
  diagnostic report shows it under "Hard crash during the previous run".
- **The trace now covers usage, not just startup.** It stopped after the last
  startup step — which page someone opened was recorded nowhere. Every page
  switch now writes two lines. If the second one is missing, it broke while
  building exactly that page. The file is capped so it cannot grow forever.

### Notes

- **The crash Bomb20 reported when opening "What's new" is not fixed by this,
  it is measurable.** It could not be reproduced here, and his report could not
  show it at all — that is the gap rc74 closes. If it happens again, it will be
  in the next report.

### Thanks

- **Bomb20** (pr0) — for a report that turned out to be about something
  bigger than a single crash: the tool was blind at that spot. And for sending
  it even though it looked like a false alarm.
- **Haldjas** (pr0) — for the counter-test on Windows: the
  update from rc71 to rc73 and the interface since rc61, both without findings.

## v3.0.0-rc73 - 2026-08-27

> **The thanks page now says what actually happened today.**

### Changed

- **The "Thanks & licences" page in the tool lists Bomb20's findings from
  today.** It still showed only his contribution from 25 Aug, while over this one
  morning he uncovered three bugs that would have hit **every** user on release
  day: the launch button for Star Citizen, the aborted download, and the restart
  that never came.
  - The thanks were properly recorded in both changelogs — but nobody sees those
    inside the tool. **Anyone missing from the tool has not been thanked.** The
    release checklist now names this third place explicitly.

### Confirmed

- **The restart after an update works** — verified on a second machine (CachyOS),
  from rc71 to rc72, without a single entry in the error log. So it does not
  depend on any quirk of one installation.

### Thanks

- **Bomb20** (pr0) — for a morning in which he sent three reports even
  though he actually had to work, and for his patience while his reports were
  first taken for user error. They never were.


## v3.0.0-rc72 - 2026-08-27

> **The update page now tells the truth** — it checks by itself, and the route to
> the stable version is no longer a dead end.

### Fixed

- **The page showed an outdated version number as long as it stayed open.** It
  asked **once per page build**. Anyone with the page open while a new version
  appeared kept seeing the old number on the button — and assumed they were up to
  date. Reported by **Bomb20** (pr0): "I still get 67 shown", while rc68
  had been published minutes earlier. It now checks every five minutes while the
  page is open.
  - Five minutes is the compromise: often enough that nobody misses a version,
    rare enough for GitHub's limit of 60 requests per hour.
- **The "Stable version" box was a dead end.** Instead of a button it said "First
  press 'Check now' above" — anyone wanting the stable version saw no route, just
  homework.
  - **The cause was too small a query:** the last **20** releases were fetched,
    and among 83 published releases not a single one of those was stable — only
    test versions. Now 100 are fetched (the most GitHub returns in one query),
    and it stays **one** request: the hourly limit counts requests, not entries.
  - Measured: 20 releases → 0 stable, 100 releases → 3.

### Thanks

- **Bomb20** (pr0) — for "I still get 67 shown". It sounded like a
  triviality and pointed at two bugs at once.


## v3.0.0-rc71 - 2026-08-27

> **The restart after an update works** — the cause was entirely different from
> what everyone assumed.

### Fixed

- **After an update the watcher shut down and never came back.** Reported by
  **Bomb20** (pr0) in the morning, reproduced here all through
  the day. Three attempts (rc67, rc68, rc70) failed to solve it, because they
  assumed the new version was crashing.
  - **It was not a crash.** The new version starts, finds the single-instance
    guard still occupied, considers itself the **second** instance and exits as
    designed — with return code 0. A cleanly exited process looks exactly like a
    crashed one afterwards, until someone reads the return code.
  - **Why the port stayed occupied:** the guard is closed with `close()` before
    the restart. But that does not wake the thread waiting in `accept()` — it
    stays blocked, the descriptor stays valid, the port stays taken.
    `shutdown()` aborts the waiting `accept()`; only then does `close()` actually
    release the port.
  - Proven, not assumed: the probe previously failed with `Address already in
    use` and now goes through. Self-test section 24 keeps it that way.

### Thanks

- **Bomb20** (pr0) — for the first report and for not letting go when it
  looked like a user error. He was right, we were not.


## v3.0.0-rc70 - 2026-08-27

> **If the restart fails, the report will now say why.**

### Fixed

- **`'Overlay' object has no attribute '_dx'` when dragging the overlay.** Tk
  does not always deliver a mouse motion after a click on the same window:
  press the button outside and drag into the overlay, and only the motion
  fires — leaving no starting point. Dragging did nothing once, and the error
  landed silently in the log. Reported by **Bomb20** (pr0, 25 Aug 2026 on
  rc18) and again on 27 Aug 2026 on rc69 — never fixed in between, because
  it breaks nothing you can see.

### Changed

- **A failed restart now leaves a trace.** The error output of the freshly
  started version used to go to `/dev/null` — which is why "it shuts down and
  never comes back" could not be diagnosed: the report contained **nothing** about
  it. It is now captured, and if the new version does not come up, its last words
  are attached to the error log and thus to the report.
  - This is not a fix but a measurement. After two attempts that did not solve
    the restart, there will be no third guess.

### Thanks

- **Bomb20** (pr0) — for the drag error that sat in reports for two days
  without anyone taking it seriously.


## v3.0.0-rc69 - 2026-08-27

> **For some, the update was never downloaded at all** — the progress display
> was to blame.

### Fixed

- **Click "get version", and nothing happened.** No progress, no restart, no
  message — after a restart the old version was still running. Reported by
  **Bomb20** (pr0): "I clicked get 68, but nothing came up about restart
  or install."
  - **The cause was the display, not the download.** Downloading runs in its own
    thread that reports progress to the window. That call can throw
    (`RuntimeError: main thread is not in main loop`) — and the exception took
    the **entire thread** with it, on the very first percent step. Bomb20's
    report showed the error three times, once per click.
  - Drawing is incidental, downloading is the point. Every display call in the
    update thread is now wrapped: if it fails, that is recorded and the work
    carries on.
- **"Check for updates" wrongly gave the all-clear.** Bomb20 was told "you have
  the latest, rc67" while rc68 had been published two minutes earlier. GitHub
  allows only **60 requests per hour per address** anonymously; anyone clicking a
  lot in one morning runs into it. The request failed — and was swallowed
  silently, so the old state was used instead.
  - "Nothing new" and "could not check" are opposites and are now kept apart.
    When the hourly limit is reached, the message says so and that it will work
    again within the hour.
  - **A check button that wrongly gives the all-clear is worse than none.**

### Thanks

- **Bomb20** (pr0) — for the third diagnostic report of the morning, sent
  at exactly the right moment. Without it, "nothing came up" could not have been
  told apart from "the download is stuck"; with it, the cause was there in one
  line.


## v3.0.0-rc68 - 2026-08-27

> **The update button is where you look for it** — and "Fassung" is now called
> "Version" throughout the German interface.

### Changed

- **The "Get the latest version" button now sits at the very top**, right below
  the version card. Previously it came after the button row and the daily
  toggle, which put it **below the edge** at the window's minimum size — someone
  who cannot find it will not update.
  - Making the window taller would have been the wrong answer: on a 1366×768
    laptop it would no longer fit at all. The most important button belongs at
    the top, not the window in the sky.
- **Both channel boxes are fully visible at minimum size too** — they hold the
  button that fetches the stable version specifically. The daily toggle moved
  below them; it is a side setting, the boxes are the point of the page.
- **"Finished versions only" is now "Stable version".** "Finished" sounds like
  something that is done — this tool is under continuous development.
- **"rcXX is already there" is now "rcXX is already installed"** — clearer, and
  the English string already said so.

### Thanks



## v3.0.0-rc67 - 2026-08-27

> **The restart after an update works on Linux** — and can no longer fail
> silently.

### Fixed

- **After an update the watcher shut down and never came back.** It downloaded
  the new version, installed it, closed itself — and stayed closed. Reported by
  **Bomb20** (pr0) with the decisive sentence "it does shut down but
  doesn't start", reproduced the same day on a second machine.
  - **The cause:** when starting the new version, only `APPIMAGE`, `APPDIR`,
    `OWD` and `ARGV0` were removed from the environment — `LD_LIBRARY_PATH`,
    `PYTHONHOME` and `PYTHONPATH` stayed. Inside an AppImage those point into the
    **extracted mount of the old version**. Two seconds later the old one exits,
    its mount disappears, and the new one looks for its libraries in a directory
    that no longer exists. It dies before a window appears.
  - The proper cleanup already existed (`saubere_umgebung`); the restart just
    carried its own incomplete copy. Both now live in `scbp/pfade.py` — **one**
    cleanup, used by everyone.
- **And it can no longer fail silently.** The old version only steps aside once
  the new one has survived its first seconds. If it dies, the watcher stays open
  and says so: "The new version did not come up." Previously the old one closed
  dutifully while the new one was already dead — leaving the machine without a
  watcher and without a word of explanation.
  - Same lesson as the launch button in rc65: **starting a program does not mean
    it is running.** `Popen` reports success as soon as the process exists.

### Thanks

- **Bomb20** (pr0) — for sticking with it. His matter-of-fact "it does
  shut down but doesn't start" pinned down the bug after it had first been
  dismissed as a user error. He was right, we were not.

## v3.0.0-rc66 - 2026-08-27

> **The export files keep themselves up to date** — and the file chooser finally
> looks like the system it runs on.

### Added

- **The export folder is updated with every new blueprint.** Until now the three
  files (KRT Profit Basetool, scmdb.net, full backup) were only written on a
  button press — anyone who had clicked once assumed they were current, while
  they stayed frozen at the moment of that click. Writing is now tied to the
  inventory itself: every find in the game, every catch-up at startup, every
  confirmation from the launcher and every import carries the files along.
  - **Fixed file names in the folder.** With a date in the name, three new files
    would appear there every day and nobody would know which one is current. The
    save dialog still suggests a name with a date — saving by hand means
    deliberately preserving a state.
  - **Previously stored dated files move to `Ältere/`** — moved, not deleted.
    Anything else in the folder is left alone.
- **A save button per format**, right next to the format, instead of one shared
  button further down.

### Fixed

- **"Save individually …" always saved the Basetool format.** The format was
  hard-coded; scmdb and the full backup were not reachable through the dialog at
  all.
- **The file chooser on Linux was the old Tk box** — a column list showing every
  hidden folder, no sorting, no preview. It now opens the desktop's own dialog
  (`kdialog` on KDE, otherwise `zenity`), everywhere a file or folder is chosen:
  import inventory, save inventory, game folder, launcher folder, own folder and
  the setup assistant. If neither is present, the Tk dialog remains as a
  fallback — **nothing depends on it.** Nothing changes on Windows and macOS,
  where Tk already passes through the real system dialog.
  - Folders already had this path; files did not. Both now live in one place
    (`scbp/dateiwahl.py`) instead of three.


### Thanks


## v3.0.0-rc65 - 2026-08-27

> **The launch button called the wrong program on Linux.**

### Fixed

- **The "Launch Star Citizen" button started nothing on Linux.** It said
  "Launching Star Citizen …" and then nothing happened — without any error. It
  called `lug-helper`, which **cannot launch the game at all**: it manages the
  Wine prefix, runners and DXVK, and has no launch option. The watcher now uses
  the `sc-launch.sh` launch script the helper creates inside the prefix, and
  finds it via the game folder (one level above `drive_c`) — no matter where
  someone installed it. Reported by **Bomb20** (pr0).
  - No more fallback to `lug-helper`: it would be found, the button would
    appear, and it would do nothing again. Anyone playing through Lutris or
    Heroic still enters their launch command in the `spielstarter` setting.


### Thanks

- **Bomb20** (pr0) — for reporting that Star Citizen could not be launched
  from the tool, and for the patience of sending two diagnostic reports in one
  morning. Without the second one it would not have come out that `lug-helper`
  cannot launch the game at all.

## v3.0.0-rc64 - 2026-08-27

> **The rebuild eats the message** — the same trap three times, in three
> different places.

### Fixed

- **"Check for updates" still reported nothing.** The rc63 crash was gone but no
  answer appeared: the button stayed on "Looking for a new version …".
  `neu_aufbauen()` destroys **every** child of the window — including the footer
  the message lives in. It was set and torn down milliseconds later. It now
  rebuilds first and reports afterwards.

- **Same trap after updating on Linux.** "Ready — restart now" was said at
  `after(0)` and swept away at `after(50)`. Order swapped.

- **At "very large" half the sidebar was missing.** "Launch Star Citizen", "Buy
  me a coffee" and "Discord" dropped out of the window — they are packed from
  the bottom, and whatever does not fit between tabs and footer falls out. The
  window's minimum size depends on the sidebar height, which depends on the
  font. The program always calculated this correctly; the calculation simply
  never ran after a font or language change. It is now part of the rebuild.

- **The two boxes under "What do you want to hear about?" were unequal.**
  `pack(expand=True)` distributes only the **surplus** evenly — whichever has
  more text stays wider. They now sit in a `grid` with `uniform`, the only
  guarantee in Tk that makes two columns truly equal; measured 545 px to
  545 px, same height.

- **At "very large" the buttons were cut off.** A named Tk font applies to every
  text instantly — but the drawn round buttons fix their canvas to the measured
  text width **once**, at build time. Measured on the overlay choice: canvas
  177 px, text 206 px, **29 px short**. Changing the font size now rebuilds the
  interface — as the language switch has always done — so every canvas measures
  anew.

### Notes

- **Self-test section 21.** Checks both halves: that a finished round button
  really does not grow on its own (otherwise the second check would pass
  vacuously), and that the font switch rebuilds **and then** reports.

## v3.0.0-rc63 - 2026-08-27

> **"Check for updates" checks again** — and the notice before an update finally
> shows up.

### Fixed

- **"Check for updates" answered with `name 'datei' is not defined`.** The
  button did not hold the *look* routine but the *fetch* one — download,
  install, step aside — using two variables that never existed in that
  function. Whether a new version was out or not, the status line said it had
  not worked. The button now reports what it finds: the version — or **"You
  have the latest version."** That sentence existed all along; nothing ever
  showed it.

- **The notice before an update never appeared, not once.** Since rc52 the
  watcher is meant to announce that it will close, run the installer and needs
  a double-click afterwards — a program that vanishes without a word looks like
  a crash. The dialog sat in that same dead function. It now runs in the real
  update, before installing, and the installer waits until it has been read.

- **The export folder never opened.** `os.startfile()` in the inventory window
  used an `os` that was never imported there, and the error fell silently into
  an `except Exception`. During the folder migration `t(...)` was used instead
  of `sprache.t(...)`, so the success message went missing. Both found by the
  new check below, not by hand.

### Notes

- **The self-test now looks for names that do not exist** (section 20, via
  `pyflakes`). This class of bug otherwise surfaces only on a **click**: Python
  resolves names at runtime, and when the callback ends in an `except`, nobody
  sees it. The check found three cases straight away. It runs in the build
  pipeline before every release; if `pyflakes` is missing on a dev machine it
  is skipped rather than failing.

### Changed

- **The ⓘ at the right edge of the blueprint list is bigger** — it opens the
  origin panel and was hard to recognise as a control at pure line size. New
  size set `ANTIPPBAR`, one step above the other in-line marks: 16 px instead
  of 14 at "normal", 22 instead of 18 at "very large". The status dots in the
  overlay are unchanged — nobody clicks those.

## v3.0.0-rc62 - 2026-08-27

> **The patch filter shows again what the patch brought.**

### Fixed

- **The patch filter found nothing and "new in game" stayed empty.** Anyone who
  used the Watcher before rc55 has a catalogue without origin stamps — stamping
  only happened on a rebuild, and a rebuild only happens on a new game version.
  So the dropdown showed "4.10.0 (21)" (it reads the history directly) while the
  list below said "Nothing found". The stamps are now filled in at startup, with
  no rebuild and no network needed.
- **The next patch would have been silent.** The comparison baseline
  (`bauplaene-gesehen.json`) also arrived only with rc55. Without it the rule
  "very first catalogue build — nothing is new" kicked in, and the next patch
  would have reported **zero** additions. If the file is missing, the existing
  catalogue is now used as the baseline: whatever is in it was in the game
  before.

### Notes

- **The self-test now covers this case** (section 19, eleven new checks). It paid
  off immediately: the catch-up ran *behind* the `SC_BP_NO_NET` network switch at
  first — anyone starting without a network would never have got a stamp, even
  though both history and catalogue sit on disk.

## v3.0.0-rc61 - 2026-08-27

> **The Discord announcement now says what it is about.**

### Added

- **The Discord release announcement is now a readable card.** Instead of
  `[Repo] New release published: v3.0.0-rc60` it shows the changelog section for
  **this** build — the same text the tool shows under "What's new". Test builds
  in gold with a "less thoroughly tested" note, finished ones in Xharig green,
  plus the program icon. after comparing with the
  StarStrings channel. Without a stored key nothing happens and the build stays
  green — a chat message must never turn a finished release red.

## v3.0.0-rc60 - 2026-08-27

> **What the diagnostics report revealed.** An invisible cross, eight errors per
> page switch — and a new check that finds both in advance from now on.

### Fixed

- **Eight log entries on every page switch.** `invalid command name …!label` —
  callbacks that adjust the line wrapping ran after their label had been
  destroyed. Nothing was visible: the hook in `fehler.py` caught them, they only
  filled up the report and buried what actually mattered. The same trap sat in
  the button row and in the drawn-border entry field; all three now check whether
  their widget still exists. Measured: 39 page switches, **0** errors.

- **The cross that closes the source box was invisible.** In the blueprint list
  it left an empty gap: the `schliessen` symbol only existed at button size while
  it was used at row size. `zeichen.bild()` silently returns `None` for a missing
  file — deliberately, so a missing symbol never halts the program, which is
  exactly what hid the bug. `tools/oberflaeche_pruefen.py` now checks for it.

## v3.0.0-rc59 - 2026-08-27

> **The readme is accurate again.** All screenshots redone, a separate set
> per language, and every symbol in them comes from the program's own set.

### Added

- **The coloured dots were still emoji in the running text.** The symbol key
  already showed the real images while the description below it kept using
  `🟢 🟡 🔵 ⭐` — two different renderings of the same symbol on one page.

- **The English readme now shows the English interface.** Until now it presented
  German screenshots — with eleven images, and a tool whose Linux users mostly
  run the English client, that is not a detail. `tools/sprachen_pruefen.py` now
  checks for it: it only counted sections and never looked at images.

- **Every screenshot in the readme is new.** The old ones were from v3.0.0-rc11
  and showed not just the replaced symbols but a build without the server status
  tab and without the patch filter. Two pages got their first screenshot at all:
  **Server status** and **Thanks & Licenses**.

- **The feature table in the readme used emoji instead of the real symbols.**
  `⚡ 📋 🧭 ⭐ 🔔 …` have nothing to do with the program's icon set and look
  different on every system. All sixteen now come from the same set as the
  interface.

- **A screenshot exposed the author's home path.** `screenshot-pfade.png` had
  been in the repo since v3.0.0-rc11, showing `/home/<user>/` three times — the
  very thing `pfade.kuerzen()` strips from error reports. Removed; the folder
  page gets no screenshot at all, since it necessarily shows paths. The server
  status tab took its place.

### Fixed

- **The filter buttons on "What's new" stayed German in English.** "Alles / Neu /
  Verbessert / Behoben" were hard-coded instead of living in `sprache.py` — right
  next to a properly translated changelog. Spotted on a screenshot of the English
  interface.

## v3.0.0-rc58 - 2026-08-27

> **What belongs to whom — in one place.** A new "Thanks & Licenses" tab that
> brings the licences and the people together. Plus names and symbols that
> finally match what they do.

### Added

- **The "Mission text" tab is now "In-game text".** The old name did not say
  **where** those texts appear.
- **The program icon now sits next to the version on "Update & About".** The page
  had no image at all after the author block moved to "Thanks & Licenses".

- **The readme showed symbols the tool no longer has.** The button legend in
  both readmes listed `☰`, `ⓘ`, `⟳`, `⏻` and `🗑` — two of them are long gone,
  the others look different now. It now shows the **actual image files** from
  `assets/symbole/`, so it can no longer go stale: swapping a symbol updates the
  readme picture by itself. Same for the message symbol key.
- **"Who built this" suddenly appeared twice.** The block naming the author,
  scmdb, the SC Deutsch Launcher and StarStrings sat on "Update & About" — and
  the new "Thanks & Licenses" page listed the same projects again. It now lives
  only on "Thanks & Licenses", with the author **at the top**: a page listing
  other people's work has to name its own first.

- **The donation link was nowhere to be seen on GitHub.** The "Buy me a coffee"
  button has been in the tool for a long time — but the project page itself had
  nothing: no sponsor button, no mention in the readme. Anyone who had not
  installed the tool yet could not find it at all. Both are there now.

- **New "Thanks & Licenses" tab** under *Info*. Until now the program showed
  **no licence information at all** — neither its own (GPL-3.0) nor that of the
  bundled symbols, and third-party projects were only mentioned in passing where
  they happened to be used. There is now one place stating what belongs to whom:
  the program itself, the Lucide symbols, the scmdb data, StarStrings and the SC
  Deutsch Launcher — each with its licence and a clickable link. Plus thanks to
  the people whose feedback turned into something.

## v3.0.0-rc57 - 2026-08-27

> **One icon set instead of fourteen glyphs.** The symbols in the notification
> bar had different sizes, mixed styles, and looked different on every operating
> system. Replaced with rendered images from a single, consistently drawn set.

### Changed

- **All symbols are the same size now — and come from one set.** The glyphs in
  the notification bar had different sizes, the bell being the largest. Three
  causes with the same root: *the font decided, not the program.* A glyph fills
  only 50–70 % of its box, each one differently; `🗑` and `▶` are solid shapes
  while `⚙ ⟳ ✕` are thin strokes; and every operating system picks a different
  fallback font. Replaced with rendered images from the **Lucide** set — all
  drawn on a 24×24 grid with the same stroke width.
- **The interface now looks identical on Windows, Linux and macOS.** It did not
  before: Windows used `Segoe UI Symbol`, other systems something else. Anyone
  developing on a Mac saw different glyphs than their users on Windows.
- **The coloured dots in front of blueprints are no longer emoji.** `🟢 🟡 🔵 ⭐`
  live outside the basic plane; Windows rendered them through the colour emoji
  font as coloured blocks that **ignored** the configured colour — in the very
  place you look at most often.
- **Launching Star Citizen now shows a rocket instead of a play arrow.** A `▶`
  means "play video" everywhere, not "start a program".
- **Clearing messages now shows an eraser instead of a bin.** The button deletes
  nothing — it only tidies the display, the blueprints stay. A bin promises
  destruction and puts people off clicking it.
- **"Setup" is now "Run setup".** A verb says something is about to happen; the
  noun alone sounded like a place to look things up.
- The height of the notification bar now grows with the configured font size. It
  was fixed at 26 pixels, which made symbols stick out at "large".

### Removed

- **The autostart switch is gone from the notification bar.** A power symbol
  means "turn the device off" everywhere, and it sat right next to the cross
  that really does close the program — two buttons that both looked like "off".
  The setting is unchanged under "General".
- **The setup assistant button is gone from the notification bar.** It remains
  available in the main window, top right — the settings are where everyone goes anyway once they notice something is off.

### Fixed

- **A help text pointed at a glyph that no longer existed.** "Use ☰ to open the
  blueprint list at any time" was still in the setup assistant, even though `☰`
  had been replaced by the clipboard back in v3.0.0-rc55. All texts now name the
  symbols in words instead of depicting them.

### Thanks


## v3.0.0 - 2026-08-29

> **One window for everything.** The blueprint list and the settings used to live in
> two separate windows, and you had to know which one held what. They are now together —
> tabs on the left, a visible folder for your files, and an installer instead of
> dragging a file somewhere by hand.

### The short version

- **The list shows what the patch brought into the game.** Next to "watching"
  there is now **🔵 new in game**. The catalogue stamps every blueprint with the
  game version it first appeared in; the filter shows the current patch. When the
  next one lands, the new ones move in and the old ones drop out — but the stamp
  stays, so you can still tell which patch a blueprint came with. A **patch
  dropdown** next to the other filters lets you look up any earlier patch, and it
  extends itself as patches arrive. 4.10.0 added 21.
- **A patch history of its own**, so that number is actually right. Comparison
  now runs against **every blueprint ever seen**, not against last week's
  catalogue. The first attempt reported 74 additions, 53 of which had been in
  the game for ages — the data source simply had not listed them for a while.
  And it could not be checked afterwards: scmdb only keeps the current game
  version, and the 4.9.0 data was already gone the same day. So the tool now
  records what each patch brought (`daten/patch-historie.json`, readable in the
  repo) — additions only, never the whole catalogue.
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

- **A "Server status" tab of its own.** Is Star Citizen up? If you cannot get
  into the game, you look for the fault on your own machine first — this
  answers that beforehand. It shows what CIG reports on its status page: the
  state of all three systems, plus the incidents of the last two months in full,
  update lines included. The layout follows the status page, and the states stay
  **in CIG's own wording** (`operational`, `maintenance`) — translating them
  would be a statement RSI never made. While the tab is open it checks once a
  minute; that costs almost nothing because it asks with `ETag` and an unchanged
  page is answered without content. The source is linked below it.
  ⚠️ These entries are **maintained by hand, not measured** — the page says so
  too, so nobody mistakes it for a measurement.
- **A button for „just give me the latest".** Until now you first had to
  understand what a channel is and pick the right one of the two boxes — anyone
  choosing the wrong one was offered nothing at all. There is now a full-width
  button above them that immediately fetches whatever is available, including a
  test build. It changes nothing about the setting below.

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
  Haldjas (pr0): „when I get into the overlay with my mouse during combat, that
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

- **"Paths" moved to the advanced section.** The game folder and the launcher
  are found automatically; anyone who does need to step in is guided by the
  setup assistant, which explains what the page only shows as fields. A tab
  almost nobody needs was just in the way at the top.

- **Launching Star Citizen now sits at the bottom left**, in the accent green
  above "Advanced". The button used to live on the "Mission text" page — where
  blueprint wording is handled — and after that only in the overlay, so only
  while that was visible. Now it is there on **every** page.

- **A Discord button** below it, deliberately quieter: launching the game is what
  you keep this window open for, the Discord link is an offer. Two equally loud
  buttons cancel each other out.

- **"Check now" is now "Check for updates".** The old label never said what it
  checked for. "Update" would have been wrong — the button only looks, it
  fetches nothing.

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

- **A collapsed overlay could not be opened again.** The button toggled, but
  nothing happened on screen — the tool was shut and stayed shut. Cause: on
  collapsing, the current window height was stored as the "open" height. Once
  the stored state and the actual geometry drifted apart, the next collapse
  wrote the **title bar height** as the open height; from then on the window
  "expanded" to its own size. The height is now only remembered while the window
  really is open, and expanding enforces a minimum height.
- **The resize grip covered the ✕ while collapsed.** It sits at the bottom
  right — on a window shrunk to title bar height that is the same spot as the
  top right, and you had to aim to close the tool at all. It now belongs to the
  **list** rather than the window — when the list is collapsed it has no height,
  so the grip is necessarily gone with it. Hiding it in time instead failed
  three times: a state that follows from how things are built is more reliable
  than one restored afterwards.
- **Blueprint names were unreadable without the launcher** — "Golemmc4Orepod"
  instead of "GOLEM MC-4 Ore Pod". The fallback ran `.title()` on the comparison
  key, which has no word boundaries left; the readable name sat right next to it
  in the cache the whole time. This affected **every Linux user**, because there
  is never a launcher there.
- **Self-update never arrived on Windows.** Clicking "get it" produced a warning
  and then nothing at all — except an orphaned 14 MB file in the program folder,
  once per attempt. Two separate bugs were behind it, either of which would have
  been enough on its own:

  The **wrong file** was fetched. Every release carries three assets, and the
  code took the first one ending in `.exe`. GitHub sorts alphabetically and a
  `-` sorts before a `.`, so `SC-BP-Watcher-Setup.exe` came first. The installer
  was moved on top of the program file without ever being run: opening the
  watcher afterwards gave you a setup window.

  And the swap could not have happened anyway. After the app exits, the
  bootloader stays alive to clean up its folder under `%TEMP%`; when a file
  there stayed locked it sat in a "Failed to remove temporary directory" dialog
  — holding the very `.exe` the helper script was waiting to be released. After
  two minutes it gave up. The user would have had to dismiss a warning nobody
  knew was part of the update.

  **On Windows the installer is now launched** instead of the program swapping
  its own file. It closes the running watcher itself, replaces it, keeps the
  "Apps & Features" entry current and starts it back up. On Linux the proven
  AppImage swap stays as it was.

- **The tray icon never appeared on Windows.** It was created on every start and
  failed at the same spot every time, visible only in the error report:
  `argument 11: OverflowError: int too long to convert`. The call that creates
  the window had no type declarations, and without them Python passes every
  value as a 32-bit number — the handle involved is wider than that on 64-bit
  Windows. The same mistake sat in the window procedure's return type. Shutdown
  now cleans the icon up for real, too: the previous route was not allowed to
  work from outside and failed silently.

- **The version shown in "Apps & Features" stayed put.** Only the per-user
  registry branch was checked. Anyone who picked "for all users" during install
  has their entry in the machine branch, which was never updated — so Windows
  kept showing a version that no longer existed. Both branches are searched now.
  On top of that the installer no longer asks "just me" or "all users": the
  program lands in your own user folder either way, which removes the question
  and any administrator prompt when updating.

- **The icons in the bar looked mangled on Windows.** `Segoe UI` contains
  **not one** of the fourteen glyphs — Windows picked a fallback per character
  and reached for **Segoe UI Emoji**: colourful, square emoji images in a slim
  dark bar, at uneven widths (10 to 21 pixels at the same size). That is also
  why the icons could never be evened out via the font size — they came from
  different font files. Windows now explicitly asks for **Segoe UI Symbol**:
  all fourteen glyphs monochrome, in the configured text colour, with half the
  spread. On Linux this was never a problem and nothing changes.

- **The overlay stayed German when you switched to English.** Changing the
  language gave you an English window and a German status bar:
  „8 Baupläne · Log ✓ · ohne Launcher · geprüft", plus the waiting message and
  the autostart text. English versions of those strings had existed all along —
  nobody used them, the code kept assembling the German ones. On top of that
  the overlay never heard about a language change at all; only the settings
  window relabelled itself.
  The catalogue watch message „newly craftable in game“ had the same
  problem. Messages **already sitting in the bar** when you switched stayed
  German too — „Keine Log-Sicherungen gefunden", for one. They had been written
  into the line as finished sentences, frozen in the language of the moment;
  only a restart cleared them. Messages now carry their text key along and are
  rewritten on a language change — including the date, which reads differently
  in English (2026-08-22 rather than 22.08.2026).

- **The hint on the ▶ launch button overwrote the status bar.** It was the only
  one of the ten icons without a tooltip; instead it wrote into the status bar
  and afterwards restored a value that was never kept up to date — so a
  blueprint message was gone after the mouse passed over the icon.

- **The logo was missing from the finished build.** On „Update & About" the
  program loaded `assets/xharig.png`, but the build never packed that file — it
  never showed when starting from source, where the file is present.

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

- **Haldjas** (pr0) — the pop-up mode suggestion; plus the setup that
  failed on the running file, the console windows during updates, the missing
  tray icon, the crash after restarting, the font size that never reached the
  overlay, the text source the wizard forgot — and the observation that
  explained everything: „it stays on rc25".
- **Bomb20** (pr0) — the crash on the very first start (a bug only new users
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
