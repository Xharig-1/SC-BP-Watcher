# Roadmap

**English** · [Deutsch](ROADMAP.de.md)

## What it is for

SC BP Watcher is a small overlay that shows, while you play Star Citizen, when a new blueprint is unlocked — on **Windows and Linux**, from a shared codebase.

Four things are deliberate and will stay that way:

- **Lightweight.** Plain Python standard library, no extra packages. What has no dependency cannot lose one.
- **It's yours.** No account, no sign-in, no cloud. What the tool knows sits in files on your disk.
- **It reads, it does not write.** Nothing about the game installation is changed.
- **Honest over pretty.** If something might be missing, it says so — an uncomfortable answer beats a nice number you cannot rely on.

## What it does today

| | |
|---|---|
| ✅ | Live detection of new blueprints from the game log, shown in the overlay |
| ✅ | **Its own blueprint inventory** — the SC Deutsch Launcher is not needed |
| ✅ | **Catch-up**: earlier play sessions are read on start |
| ✅ | **Blueprint list** to look up, filter and tick off, with progress |
| ✅ | **Where each blueprint drops** — faction, contract, required standing, payout |
| ✅ | Catalogue watch: reports what becomes **newly craftable** in the game, plus a watchlist |
| ✅ | **New in game** filter plus a patch dropdown: see what each patch added |
| ✅ | Class, size and grade tag (`M/1/A`) |
| ✅ | Setup wizard, repeatable at any time |
| ✅ | German and English, switchable |
| ✅ | Windows and Linux, with autostart on both |
| ✅ | Export your inventory — for the KRT Profit Basetool, for scmdb.net and as a full backup |
| ✅ | Collapse the overlay, for anyone on a single screen |

## What is being worked on

No schedule and no fixed order — the state of things is in [`CHANGELOG.md`](CHANGELOG.md), and the **ⓘ "What's new"** window inside the tool shows what each build brought.

Currently in the works: more convenience during setup and a tray icon.

## Relationship to the SC Deutsch Launcher

**Freedom of choice, not replacement.**

This page used to argue that a self-kept inventory is necessarily inaccurate because it could only be filled "from today on". Two measurements disproved that:

- The watcher reads the **stored logs** on start. Having played without it running does not tear a hole, as long as Star Citizen still has the backup. If a gap remains anyway, it is **stated** rather than hidden.
- The launcher itself counts **too low**: it is missing the P4-AR Rifle although the Fabricator lists it as owned. Starter blueprints were never "received" and appear in no log. Its number is a lower bound, not an inventory.

The launcher remains useful all the same: it confirms finds and maintains a catalogue with German names. If it is there, it is used. If it is not — always the case on Linux — the watcher works anyway.

## Getting involved

Wishes, bug reports and ideas are welcome as an [issue](../../issues).
