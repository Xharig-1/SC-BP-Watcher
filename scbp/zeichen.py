# -*- coding: utf-8 -*-
"""Die Symbole der Melde-Leiste — gezeichnet statt getippt.

⚠ **Warum nicht einfach Unicode-Zeichen?** Drei Gründe, alle am 26.08.2026
aufgeschlagen:

1. **Die halbe Auswahl fehlt.** Nur Zeichen aus der Grundebene (bis `U+FFFF`)
   sind in der Oberflächenschrift verlässlich da. Papierkorb (`U+1F5D1`),
   Glocke (`U+1F514`) und Klemmbrett (`U+1F4CB`) liegen darüber — im Fenster
   steht dann ein Fragezeichen, und auffallen tut das erst im laufenden
   Programm, nicht im Code.
2. **Sie sind unscharf.** der Autor im Vergleich mit dem SC-Deutsch-Launcher:
   „die button größe oben, ist auch deutlich angenehmer und die wirken auch
   schärfer als im watcher display bei mir". Ein Schriftzeichen wird in der
   Größe gezeichnet, die die Schrift dafür vorsieht, und auf einem 4096 Pixel
   breiten Bildschirm ist das winzig.
3. **Sie sehen überall anders aus.** Dieselbe Zeile trägt unter Windows, Linux
   und Mac drei verschiedene Formen — das Programm hat aber genau eine
   Formensprache.

Gezeichnet lösen sich alle drei auf einmal: jede Größe scharf, jedes Motiv
möglich, überall dasselbe Bild.

**Bauform.** Jede Funktion bekommt `(leinwand, x, y, groesse, farbe)` — `x`/`y`
ist die **Mitte**, `groesse` die Kantenlänge des gedachten Quadrats. Alle Maße
sind Anteile davon, damit die Zeichen mit der eingestellten Schriftgröße
mitwachsen. Wer ein neues Zeichen hinzufügt, hält sich daran und trägt es unten
in `ALLE` ein.
"""


def _q(x, y, groesse):
    """Linke obere Ecke und Kantenlänge aus Mittelpunkt und Größe."""
    return x - groesse / 2.0, y - groesse / 2.0, groesse


def glocke(leinwand, x, y, groesse, farbe):
    """Eine Glocke — für „es gibt eine neue Fassung".

    Löst das `ⓘ` ab. Ein „i" heißt „hier steht etwas"; eine Glocke heißt „für
    dich ist etwas da". Vorbild ist der SC-Deutsch-Launcher, der Autor dazu:
    „Die Glocke für Updates ist auch besser."

    ⚠ **Zwei Anläufe gingen daneben, beide sahen aus wie eine Tanne.** Der Grund
    war beide Male derselbe, nur unterschiedlich verpackt:

    * Der erste Versuch zog den Umriss mit `smooth=True` zu einer Spitze
      zusammen.
    * Der zweite setzte einen Halbkreis auf ein Trapez, das nach unten breiter
      wird — zusammen ergibt das erst recht einen Kegel.

    Was gefehlt hat, ist das **Erkennungsmerkmal einer Glocke: der breite,
    waagerechte Rand am Boden.** Ohne ihn bleibt jede Glockenform ein Kegel, egal
    wie sauber die Rundung oben ist. Deshalb ist er hier ein eigenes Rechteck und
    deutlich breiter als der Körper darüber.

    Merke fürs nächste gezeichnete Zeichen: Zuerst überlegen, **woran** man das
    Motiv erkennt, und dieses Merkmal zuerst bauen — nicht die Gesamtsilhouette
    verfeinern und hoffen.
    """
    lx, oy, g = _q(x, y, groesse)

    # 1. Der Griff ganz oben.
    leinwand.create_oval(lx + g * 0.45, oy + g * 0.02,
                         lx + g * 0.55, oy + g * 0.12,
                         fill=farbe, outline=farbe)

    # 2. Der Körper: oben rund, unten fast senkrecht. Ein Oval, dessen untere
    #    Hälfte vom Rechteck darunter überdeckt wird.
    leinwand.create_oval(lx + g * 0.26, oy + g * 0.10,
                         lx + g * 0.74, oy + g * 0.62,
                         fill=farbe, outline=farbe)
    leinwand.create_rectangle(lx + g * 0.26, oy + g * 0.34,
                              lx + g * 0.74, oy + g * 0.70,
                              fill=farbe, outline=farbe)

    # 3. Der Bodenrand — das Merkmal, an dem eine Glocke erkannt wird.
    #    Deutlich breiter als der Körper, flach, waagerecht.
    leinwand.create_rectangle(lx + g * 0.10, oy + g * 0.68,
                              lx + g * 0.90, oy + g * 0.80,
                              fill=farbe, outline=farbe)

    # 4. Der Klöppel darunter.
    leinwand.create_oval(lx + g * 0.42, oy + g * 0.82,
                         lx + g * 0.58, oy + g * 0.96,
                         fill=farbe, outline=farbe)


def klemmbrett(leinwand, x, y, groesse, farbe):
    """Ein Klemmbrett — für die Bauplan-Liste.

    Löst das `☰` ab. Drei Striche heißen „irgendeine Liste", ein Klemmbrett
    heißt „deine gesammelten Sachen". der Autor: „dieses klemmbrett für die BP
    ist auch besser."
    """
    lx, oy, g = _q(x, y, groesse)
    grund = leinwand['bg']

    # Das Brett.
    leinwand.create_rectangle(lx + g * 0.16, oy + g * 0.12,
                              lx + g * 0.84, oy + g * 0.94,
                              fill=farbe, outline=farbe)
    # Die Klemme oben — in der Grundfarbe abgesetzt, damit sie sich abhebt.
    leinwand.create_rectangle(lx + g * 0.36, oy + g * 0.04,
                              lx + g * 0.64, oy + g * 0.18,
                              fill=farbe, outline=farbe)
    leinwand.create_rectangle(lx + g * 0.40, oy + g * 0.14,
                              lx + g * 0.60, oy + g * 0.22,
                              fill=grund, outline=grund)
    # Drei Zeilen als Andeutung des Inhalts.
    for i, breite in enumerate((0.58, 0.46, 0.52)):
        oben = oy + g * (0.36 + i * 0.16)
        leinwand.create_rectangle(lx + g * 0.26, oben,
                                  lx + g * (0.26 + breite), oben + g * 0.07,
                                  fill=grund, outline=grund)


ALLE = {
    'glocke': glocke,
    'klemmbrett': klemmbrett,
}
