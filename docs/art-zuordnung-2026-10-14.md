# Art-Zuordnung, Prüftabelle 14.10.2026

Grundlage: `vorschau/termine_cache.json`, 1299 Termine (Rohdaten vor Filtern und Dublettenprüfung, manuelle Termine eingeschlossen). Regeln: `arten.py`, Tests: `tests/test_art.py`. Spalte „Regel“: welche Stufe gegriffen hat (Quelle, Titel-Stichwort, Beschreibung, Rohkategorie, „-“ = Sonstiges).

## Verteilung je Art

| Art | Termine | Anteil |
|---|---:|---:|
| Konzert | 106 | 8.2 % |
| Party | 12 | 0.9 % |
| Theater/Kabarett | 46 | 3.5 % |
| Lesung/Vortrag | 212 | 16.3 % |
| Ausstellung/Kunst | 34 | 2.6 % |
| Kurs/Workshop | 55 | 4.2 % |
| Führung | 29 | 2.2 % |
| Fest/Markt | 20 | 1.5 % |
| Kinder/Familie | 49 | 3.8 % |
| Begegnung/Treffen | 129 | 9.9 % |
| Politik | 44 | 3.4 % |
| Sport/Bewegung | 34 | 2.6 % |
| Kino | 384 | 29.6 % |
| Sonstiges | 145 | 11.2 % |
| **Gesamt** | **1299** | |

Kino enthält 381 Film-Tage der Cineworld (beim Seitenaufruf ausgeblendet). Ohne Kino bleiben 915 Termine, davon Sonstiges 145 (15.8 %). Die Zahlen sind Rohdaten vor der Dublettenprüfung; auf den Seiten übernimmt ein Termin mit Sonstiges die Art seines Duplikats.

**Nach Filtern und Dublettenprüfung** (so wie die Seiten gebaut werden, 1.179 Termine): Konzert 88, Party 11, Theater/Kabarett 36, Lesung/Vortrag 180, Ausstellung/Kunst 28, Kurs/Workshop 54, Führung 21, Fest/Markt 17, Kinder/Familie 40, Begegnung/Treffen 125, Politik 43, Sport/Bewegung 32, Kino 383, Sonstiges 121.

**Pflichtfälle** (alle als Test in `tests/test_art.py`, auf den gebauten Daten nachgeprüft): Rock-Pop-Akustik-Session (Altstadtschmiede, Kultur) = Konzert; Jazz in der Kunsthalle (Kunsthalle, Kunst) = Konzert; alle 10 Backyard-Termine = Konzert; „2. Sinfoniekonzert“ (stadt-re, leer) = Konzert; „1. Familienkonzert: Kuscheltierkonzert“ = Konzert; mOOndock-Partys = Party; „Blickpunkt Auge“-Beratung = Sonstiges; Ratssitzungen = Politik; Cineworld = Kino.

**Bewusst offen:** 16 Auftritte in der Gymnasialkirche bei „Recklinghausen leuchtet“ tragen nur Namen („Me and Lu“, „Cascades“) und die Sammelbeschreibung „Musikalische Vorführungen und Vorträge“; sie bleiben Sonstiges, weil Musik und Vortrag dort nicht zu trennen sind (siehe letzter Abschnitt).

## Stichprobe je Art

Je Art bis zu 8 verschiedene Titel aus möglichst verschiedenen Quellen.

### Konzert (106)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 03.10.2026 | 1. Familienkonzert: Kuscheltierkonzert | stadt-re |  | Konzert | Titel „konzert“ |
| 14.10.2026 | Rock-Pop-Akustik-Session | altstadtschmiede | Kultur | Konzert | Titel „Akustik-Session“ |
| 13.10.2026 | 2. Sinfoniekonzert - Lieben Sie Brahms? | vesterleben | Musik | Konzert | Titel „Sinfoni“ |
| 23.10.2026 | Livekonzert! Knud Krautwig und Daniel Brandl sind Lithium. Das Duo aus Cello und Kontraba… | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 16.10.2026 | Jazz in der Kunsthalle – Die Sparda Lounge | kunsthalle | Kunst | Konzert | Titel „Jazz“ |
| 16.10.2026 | Global Local Konzert | gastkirche | Veranstaltungen | Konzert | Titel „Konzert“ |
| 17.10.2026 | Steady Drivin Men, Chugg a Lugg | backyard | Musik | Konzert | Quelle |
| 25.10.2026 | Debut um 11 | debut-um-11 | Konzert | Konzert | Quelle |

### Party (12)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 10.10.2026 | Funzelparty | stadt-re |  | Party | Titel „party“ |
| 17.10.2026 | FLEXI & DADDY REVIVIAL Party im mOOndock | moondock | Party | Party | Quelle |
| 31.10.2026 | Halloween mit Julius (80er/90er/00er & House) | manuell | Party | Party | Titel „Halloween“ |
| 13.11.2026 | Die kleine Altstadtparty | altstadtschmiede | Kultur | Party | Titel „party“ |
| 07.11.2026 | DJ Moguai auf dem Rathausplatz | re-leuchtet | Kultur | Party | Titel „DJ“ |
| 28.11.2026 | ü30 PARTY | subergs |  | Party | Titel „ü30“ |
| 28.11.2026 | Dark Revival Party im mOOndock | moondock | Party | Party | Quelle |
| 07.11.2026 | Abschlusswochenende mit DJ Moguai | manuell | Party | Party | Titel „DJ“ |

### Theater/Kabarett (46)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 01.10.2026 | Die Springmaus | stadt-re |  | Theater/Kabarett | Beschreibung „Comedy“ |
| 18.10.2026 | Altes Land | vesterleben | Kultur | Theater/Kabarett | Beschreibung „Theater“ |
| 15.10.2026 | Stimmen aus dem Exil | nlgr | Literatur | Theater/Kabarett | Beschreibung „Theater“ |
| 11.10.2026 | Jugendtheater: „Müsli vor dem offenen Kühlschrank“ | manuell | Theater | Theater/Kabarett | Titel „theater“ |
| 06.11.2026 | Theater Ex Libris: Frankenstein | re-leuchtet | Kultur | Theater/Kabarett | Titel „Theater“ |
| 01.11.2026 | Frauengestalten bei Brecht | gegendruck | Theater | Theater/Kabarett | Beschreibung „Theater“ |
| 07.10.2026 | Martha and Me – English theatre | stadt-re |  | Theater/Kabarett | Titel „theatre“ |
| 24.10.2026 | Das Kriminal Dinner – Der letzte Joint | vesterleben | Kultur | Theater/Kabarett | Titel „Kriminal Dinner“ |

### Lesung/Vortrag (212)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 01.10.2026 | Lesung mit Tanja Peters: Schließ Frieden mit deinem Körper! | stadt-re |  | Lesung/Vortrag | Titel „Lesung“ |
| 17.10.2026 | Literaturtreff am Samstag | vesterleben | Kultur | Lesung/Vortrag | Titel „Literatur“ |
| 09.10.2026 | Weißt Du, welche Sternlein stehen? (ab 8) | sternwarte | Astronomie | Lesung/Vortrag | Quelle |
| 24.10.2026 | Leseshow mit Rainer Rudloff: "Der Herr der Ringe" | stadtbibliothek | Bibliothek | Lesung/Vortrag | Titel „Leseshow“ |
| 16.10.2026 | HENZE 100 – Briefwechsel zwischen Ingeborg Bachmann und Max Frisch | nlgr | Literatur | Lesung/Vortrag | Kategorie „Literatur“ |
| 28.10.2026 | Künstliche Intelligenz und Bildung | vhs | Bildung | Lesung/Vortrag | Beschreibung „Vortrag“ |
| 04.10.2026 | Schwester Reginalda, das Portrait einer kämpferischen Frau mit Energie und Humor | geschichte-re | Geschichte | Lesung/Vortrag | Kategorie „Geschichte“ |
| 28.10.2026 | ROADTRIP OMAN BY TRIKE | adfc | Veranstaltung | Lesung/Vortrag | Beschreibung „vortrag“ |

### Ausstellung/Kunst (34)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 02.10.2026 | Kunst, Architektur, Technik & KI ausprobieren | stadt-re |  | Ausstellung/Kunst | Titel „Kunst“ |
| 20.10.2026 | REspect4you: Clemens Wolter Graffiti Aktion | vesterleben | Kultur | Ausstellung/Kunst | Titel „Graffiti“ |
| 13.10.2026 | ArtLab | kunsthalle | Kunst | Ausstellung/Kunst | Kategorie „Kunst“ |
| 10.10.2026 | Kunstbetrachtungen am Wochenende: Macht und Pracht – Kunst als Propaganda an den Höfen de… | vhs | Bildung | Ausstellung/Kunst | Titel „Kunst“ |
| 27.10.2026 | Heldengeschichten - von der Ikone zum Comic | ikonen-museum | Kunst | Ausstellung/Kunst | Kategorie „Kunst“ |
| 16.10.2026 | Skulpturen im Park | re-leuchtet | Kultur | Ausstellung/Kunst | Titel „Skulptur“ |
| 15.10.2026 | Sonderausstellung „Ich, Gustave Courbet“ im Folkwang-Museum | seniorenbeirat | Senioren | Ausstellung/Kunst | Titel „ausstellung“ |
| 03.10.2026 | Vernissage am 03. Oktober 2026 um 18:00 "Der Zauber dahinter" von Udo Mathee und Udo Home… | stadtlabor | Kunst | Ausstellung/Kunst | Titel „Vernissage“ |

### Kurs/Workshop (55)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 13.10.2026 | Inklusiver Erste Hilfe Kurs für Menschen mit und ohne Behinderung | stadt-re |  | Kurs/Workshop | Titel „Kurs“ |
| 19.10.2026 | Bühne frei! Schauspiel-Workshop | vesterleben | Kultur | Kurs/Workshop | Titel „Workshop“ |
| 22.10.2026 | Ferienworkshop für Kinder im Alter von 8-12 Jahren | kunsthalle | Kunst | Kurs/Workshop | Titel „workshop“ |
| 28.10.2026 | Digital-Treff | vhs | Kurs | Kurs/Workshop | Quelle (VHS-Kurs) |
| 17.10.2026 | Fahrschultraining - noch sicher mit dem Auto? | seniorenbeirat | Senioren | Kurs/Workshop | Titel „training“ |
| 31.10.2026 | Kreativ-Workshops für mehr Vielfalt | selbsthilfe-kontaktstelle | Selbsthilfe | Kurs/Workshop | Titel „Workshop“ |
| 24.10.2026 | Veranstaltungskalender - Workshop: Wie werde ich vom KI-Veranstaltungskalender gefunden? | manuell | Bildung | Kurs/Workshop | Titel „Workshop“ |
| 13.12.2026 | Manga-Workshop in der Augustinessenstraße: Weihnachts-Spezial | stadtbibliothek | Bibliothek | Kurs/Workshop | Titel „Workshop“ |

### Führung (29)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 06.10.2026 | Für „Hinz und Kunz“ – Redewendungen am Objekt erklärt | stadt-re |  | Führung | Beschreibung „Beim Rundgang“ |
| 15.10.2026 | Die Not mit dem lieben Geld – Stadtgeschichte als Geldgeschichte | vesterleben | Kultur | Führung | Beschreibung „Die Führung“ |
| 18.10.2026 | Öffentliche Führung | kunsthalle | Kunst | Führung | Titel „Öffentliche Führung“ |
| 31.10.2026 | Lesen und Schreiben im Alltag (Exkursion) | vhs | Bildung | Führung | Titel „Exkursion“ |
| 18.10.2026 | Exkursion Prag – Die Goldene Stadt im Herzen Europas Geschichte – Kultur -Religion | geschichte-re | Geschichte | Führung | Titel „Exkursion“ |
| 06.10.2026 | Stadtgang von unten | gastkirche | Veranstaltungen | Führung | Titel „Stadtgang“ |
| 18.10.2026 | Öffentliche Themenführung: Teufel und Dämonen | ikonen-museum | Kunst | Führung | Titel „Themenführung“ |
| 28.10.2026 | Nachts im Museum - Taschenlampenführung in der Retro Station | re-leuchtet | Kultur | Führung | Titel „Taschenlampenführung“ |

### Fest/Markt (20)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 14.10.2026 | Trödelmarkt Vestlandhalle | vesterleben | Kultur | Fest/Markt | Titel „Trödel“ |
| 24.10.2026 | Ukrainefest | gastkirche | Veranstaltungen | Fest/Markt | Titel „fest“ |
| 09.10.2026 | MITTELALTERMERKT | zeche-klaerchen |  | Fest/Markt | Titel „MITTELALTERM“ |
| 24.10.2026 | Kreativmarkt | genial-re | Begegnung | Fest/Markt | Titel „markt“ |
| 09.10.2026 | Mittelaltermarkt an der Drachenbrücke | manuell | Fest | Fest/Markt | Titel „Mittelalterm“ |
| 20.11.2026 | Handwerkermarkt auf der Zeche | stadt-re |  | Fest/Markt | Titel „markt“ |
| 08.11.2026 | Verkaufsoffener Sonntag | re-leuchtet | Kultur | Fest/Markt | Titel „Verkaufsoffen“ |
| 09.12.2026 | Tonie-Tauschbörse | stadtbibliothek | Bibliothek | Fest/Markt | Titel „Tauschbörse“ |

### Kinder/Familie (49)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 05.10.2026 | Babytreff im Familienbüro (jeden Montag) | stadt-re |  | Kinder/Familie | Titel „Baby“ |
| 17.10.2026 | ENTFÄLLT: Zweisprachiges Bilderbuchkino (DE/EN) in Süd: "Zoey die Superheldin" | vesterleben | Kultur | Kinder/Familie | Titel „Bilderbuch“ |
| 08.10.2026 | Bilderbuchkino in Süd | stadtbibliothek | Bibliothek | Kinder/Familie | Titel „Bilderbuch“ |
| 19.10.2026 | Kulturrucksack 5 | campus-emscherland | Bildung | Kinder/Familie | Titel „Kulturrucksack“ |
| 19.10.2026 | Sparkassen-Erlebnisland | manuell | Familie | Kinder/Familie | Kategorie „Familie“ |
| 05.11.2026 | Eltern helfen Eltern. Pflegegrad beantragen für Kinder und Jugendliche | vhs | Bildung | Kinder/Familie | Titel „Eltern“ |
| 05.11.2026 | Lichterlauf für Kinder | re-leuchtet | Kultur | Kinder/Familie | Titel „Kinder“ |
| 07.10.2026 | Digitale Medien und Kinder: Chancen nutzen, Risiken erkennen | stadt-re |  | Kinder/Familie | Titel „Kinder“ |

### Begegnung/Treffen (129)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 23.10.2026 | Offene Schmiede | altstadtschmiede | Kultur | Begegnung/Treffen | Titel „Offene Schmiede“ |
| 14.10.2026 | Tofuclub – vegane KüfA | vesterleben | Kultur | Begegnung/Treffen | Titel „KüfA“ |
| 05.10.2026 | Trauercafé | gastkirche | Veranstaltungen | Begegnung/Treffen | Titel „café“ |
| 20.10.2026 | Frauenforum Recklinghausen | frauenforum |  | Begegnung/Treffen | Titel „forum“ |
| 14.10.2026 | Seniorenbüro | seniorenbeirat | Senioren | Begegnung/Treffen | Kategorie „Senioren“ |
| 02.10.2026 | Offenes Begegnungs-Café | genial-re | Begegnung | Begegnung/Treffen | Titel „Begegnung“ |
| 12.10.2026 | Queerer Stammtisch | facebook |  | Begegnung/Treffen | Titel „Stammtisch“ |
| 06.10.2026 | Ehrenamts- und Selbsthilfe-Café | manuell | Ehrenamt | Begegnung/Treffen | Titel „Selbsthilfe“ |

### Politik (44)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 13.10.2026 | Sitzung AK Medien | seniorenbeirat | Senioren | Politik | Titel „Sitzung“ |
| 08.10.2026 | Sitzung des Betriebsausschusses VCC | ratssitzungen | Politik | Politik | Quelle |
| 01.10.2026 | Bürgermeistersprechstunde | manuell | Politik | Politik | Titel „Bürgermeister“ |
| 10.11.2026 | wiR Erinnern - die Recklinghäuser Polizei und die Novemberpogrome 1938 | vhs | Bildung | Politik | Titel „pogrom“ |
| 18.11.2026 | Neue Wehrpflicht und Kriegsdienstverweigerung | gastkirche | Veranstaltungen | Politik | Titel „Wehrpflicht“ |
| 13.10.2026 | Sitzung des Ausschusses für Ordnung und Sicherheit, Feuerwehr und Katastrophenschutz | ratssitzungen | Politik | Politik | Quelle |
| 09.11.2026 | Pogromnacht vom 9. November 1938. Öffentliches Gedenken der Bürgerschaft | vhs | Bildung | Politik | Titel „Pogrom“ |
| 16.11.2026 | Sitzung AK Soziales | seniorenbeirat | Senioren | Politik | Titel „Sitzung“ |

### Sport/Bewegung (34)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 10.10.2026 | Sitztanz | stadt-re |  | Sport/Bewegung | Titel „tanz“ |
| 14.10.2026 | ADFC Feierabend-Tour – Fahrt ins Blaue | vesterleben | Kultur | Sport/Bewegung | Titel „Feierabend-Tour“ |
| 04.10.2026 | Zum Heid-, Weihnachts- und Pfingstsee | adfc | Radtour | Sport/Bewegung | Kategorie „Radtour“ |
| 17.10.2026 | PILGERTAG - 15km-Runde rund um Schloss Lembeck | ev-akademie | Bildung | Sport/Bewegung | Titel „PILGER“ |
| 07.10.2026 | Atem-Meditation | campus-emscherland | Bildung | Sport/Bewegung | Titel „Meditation“ |
| 20.11.2026 | Yin Yoga & Soundmeditation | vhs | Bildung | Sport/Bewegung | Titel „Yoga“ |
| 04.11.2026 | Medidativer Tanzabend | gastkirche | Veranstaltungen | Sport/Bewegung | Titel „Tanz“ |
| 06.10.2026 | Feierabendtour - Fahrt ins Blaue | adfc | Radtour | Sport/Bewegung | Titel „Feierabendtour“ |

### Kino (384)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 01.10.2026 | Avengers: Endgame Extended | cineworld | Kino | Kino | Quelle |
| 07.11.2026 | Film „Die verlorene Sprache” von Samira Klaho | nlgr | Literatur | Kino | Titel „Film“ |
| 12.11.2026 | Nachspiel - Ein Kino-Dokumentarfilm von Christoph Hühner und Gabriele Voss | vhs | Bildung | Kino | Titel „Dokumentarfilm“ |
| 07.11.2026 | Die verlorene Sprache | manuell | Film | Kino | Kategorie „Film“ |
| 01.10.2026 | Adams Acht | cineworld | Kino | Kino | Quelle |
| 01.10.2026 | Bibi Blocksberg - Die total verhexte Zeitreise | cineworld | Kino | Kino | Quelle |

### Sonstiges (145)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 01.10.2026 | KI:MBISS - KI zum Mitnehmen / Networking, KI und Pommes | stadt-re |  | Sonstiges | - |
| 25.10.2026 | Die Lieder meiner Nachbar*innen | altstadtschmiede | Kultur | Sonstiges | - |
| 14.10.2026 | KI für PowerPoint-Präsentationen | vesterleben | Kultur | Sonstiges | - |
| 21.10.2026 | Raus-Wege | gastkirche | Veranstaltungen | Sonstiges | - |
| 02.10.2026 | Fahrradcodierung im Infoladen Börster Weg 38a | adfc | Veranstaltung | Sonstiges | - |
| 23.10.2026 | Traumprojektion an der Engelsburg | re-leuchtet | Kultur | Sonstiges | - |
| 01.10.2026 | Flashmob zum Weltaltentag | manuell | Freizeit | Sonstiges | - |
| 08.10.2026 | Kaleidoskop der Geschichten - Männer mit internationaler Geschichte aus Recklinghausen | stadt-re |  | Sonstiges | - |

## Alle Konzert-Treffer (106)

| Datum | Titel | Quelle | Rohkategorie | Art | Regel |
|---|---|---|---|---|---|
| 03.10.2026 | 1. Familienkonzert: Kuscheltierkonzert | stadt-re |  | Konzert | Titel „konzert“ |
| 08.10.2026 | Mantra: Mitsingkonzert in der Friedhofskapelle Recklinghausen | stadt-re |  | Konzert | Titel „Mitsing“ |
| 10.10.2026 | Klassenvorspiel Schlagzeug (Christian Schneider) | manuell | Konzert | Konzert | Kategorie „Konzert“ |
| 11.10.2026 | Mezzoforte: Vom Wandern - Konzert mit Marie Borger und Thorsten Töpp | manuell | Konzert | Konzert | Titel „Konzert“ |
| 13.10.2026 | 2. Sinfoniekonzert - Lieben Sie Brahms? | stadt-re |  | Konzert | Titel „Sinfoni“ |
| 13.10.2026 | 2. Sinfoniekonzert - Lieben Sie Brahms? | vesterleben | Musik | Konzert | Titel „Sinfoni“ |
| 14.10.2026 | Klassenvorspiel Violine (Bernd Kullack) | manuell | Konzert | Konzert | Kategorie „Konzert“ |
| 14.10.2026 | Rock-Pop-Aktusik-Session | vesterleben | Kultur | Konzert | Titel „Aktusik-Session“ |
| 14.10.2026 | Rock-Pop-Akustik-Session | altstadtschmiede | Kultur | Konzert | Titel „Akustik-Session“ |
| 14.10.2026 | Rock-Pop-Akustik-Session | vesterleben | Kultur | Konzert | Titel „Akustik-Session“ |
| 15.10.2026 | Jazz Einsteiger-Session | altstadtschmiede | Kultur | Konzert | Titel „Jazz“ |
| 15.10.2026 | Jazz-Session | vesterleben | Kultur | Konzert | Titel „Jazz“ |
| 16.10.2026 | Jazz in der Kunsthalle - Die Sparda Lounge: Emily Otto | stadt-re |  | Konzert | Titel „Jazz“ |
| 16.10.2026 | Klassenvorspiel Schlagzeug (Kai Putzke) | manuell | Konzert | Konzert | Kategorie „Konzert“ |
| 16.10.2026 | Jazz in der Kunsthalle - Die Sparda Lounge: Emily Otto | vesterleben | Musik | Konzert | Titel „Jazz“ |
| 16.10.2026 | Jazz in der Kunsthalle – Die Sparda Lounge | kunsthalle | Kunst | Konzert | Titel „Jazz“ |
| 16.10.2026 | Henze100: WO BIST DU DENN, und wo bin ich? | vesterleben | Musik | Konzert | Kategorie „Musik“ |
| 16.10.2026 | Global Local Konzert | gastkirche | Veranstaltungen | Konzert | Titel „Konzert“ |
| 17.10.2026 | Steady Drivin Men, Chugg a Lugg | backyard | Musik | Konzert | Quelle |
| 17.10.2026 | Live-Musik im Recklinghäuser: The Mojo Turner Group | recklinghaeuser |  | Konzert | Titel „Live-Musik“ |
| 17.10.2026 | Mohito Royal (Punkrock unplugged) | manuell | Konzert | Konzert | Titel „unplugged“ |
| 18.10.2026 | 1. Rathauskonzert - Fjorde und Wälder | stadt-re |  | Konzert | Titel „konzert“ |
| 18.10.2026 | 1. Rathauskonzert - Fjorde und Wälder | vesterleben | Kultur | Konzert | Titel „konzert“ |
| 18.10.2026 | 1. Rathauskonzert - Fjorde und Wälder | vesterleben | Musik | Konzert | Titel „konzert“ |
| 18.10.2026 | Festmesse 120 Jahre Pauluskirche | josefeich | Konzert | Konzert | Kategorie „Konzert“ |
| 18.10.2026 | Allen-Forrester Band | backyard | Musik | Konzert | Quelle |
| 23.10.2026 | Livekonzert! Knud Krautwig und Daniel Brandl sind Lithium | vesterleben | Kultur | Konzert | Titel „konzert“ |
| 23.10.2026 | Livekonzert! Knud Krautwig und Daniel Brandl sind Lithium. Das Duo aus Cello und Kontraba… | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 23.10.2026 | Sean Athens Band | backyard | Musik | Konzert | Quelle |
| 23.10.2026 | Melodien unter Sternen I – Musik zum Träumen | re-leuchtet | Kultur | Konzert | Titel „Melodie“ |
| 24.10.2026 | DIALOG e.V. | altstadtschmiede | Kultur | Konzert | Beschreibung „Konzert“ |
| 24.10.2026 | DIALOG e.V.: Trio Schokolade & Bandura Duo Soul-Lied | vesterleben | Kultur | Konzert | Titel „Trio“ |
| 24.10.2026 | Buried Friends, Sustained Fire | backyard | Musik | Konzert | Quelle |
| 25.10.2026 | Konzertreihe - DEBUT um 11 e. V. | stadt-re |  | Konzert | Titel „Konzert“ |
| 25.10.2026 | Debut um 11 | debut-um-11 | Konzert | Konzert | Quelle |
| 25.10.2026 | Konzert: Tallana Gabriel und Boris Rosenthal | manuell | Konzert | Konzert | Titel „Konzert“ |
| 25.10.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 27.10.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 30.10.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 30.10.2026 | Melodien unter Sternen II – Musik zum Träumen | re-leuchtet | Kultur | Konzert | Titel „Melodie“ |
| 30.10.2026 | Pirates in black | backyard | Musik | Konzert | Quelle |
| 31.10.2026 | Gastspiel Akustikduo | re-leuchtet | Kultur | Konzert | Titel „Akusti“ |
| 01.11.2026 | Geistliche Abendmusik | stadt-re |  | Konzert | Titel „musik“ |
| 01.11.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 01.11.2026 | Zac Schulze Gang | backyard | Musik | Konzert | Quelle |
| 03.11.2026 | 3. Sinfoniekonzert - Lichtblick | stadt-re |  | Konzert | Titel „Sinfoni“ |
| 03.11.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 03.11.2026 | Max Hagen Trio | backyard | Musik | Konzert | Quelle |
| 05.11.2026 | Schulchor | re-leuchtet | Kultur | Konzert | Titel „chor“ |
| 05.11.2026 | Folk/Lyrik Livekonzert! From Shore To Shore – Ein musikalischer Streifzug über die Britis… | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 06.11.2026 | Jazz in der Kunsthalle - Die Sparda Lounge: Accordion Affairs (Trio um Jörg Siebenhaar) | stadt-re |  | Konzert | Titel „Jazz“ |
| 06.11.2026 | Jazz in der Kunsthalle – Die Sparda Lounge | kunsthalle | Kunst | Konzert | Titel „Jazz“ |
| 06.11.2026 | Chorgemeinschaft St. Elisabeth | re-leuchtet | Kultur | Konzert | Titel „Chor“ |
| 06.11.2026 | Orbitron, Sleeping Green | backyard | Musik | Konzert | Quelle |
| 07.11.2026 | Jazzy November: Lady "D" im Herbstlicht | stadt-re |  | Konzert | Titel „Jazz“ |
| 07.11.2026 | Louis Spohr: Die letzten Dinge | stadt-re |  | Konzert | Beschreibung „Oratori“ |
| 07.11.2026 | Jazzy November: Lady „D“ im Herbstlicht | re-leuchtet | Kultur | Konzert | Titel „Jazz“ |
| 07.11.2026 | Akkordeonensemble REacction | re-leuchtet | Kultur | Konzert | Titel „ensemble“ |
| 07.11.2026 | Next Generation Voodoo, Pastör | backyard | Musik | Konzert | Quelle |
| 08.11.2026 | „The Glams“, Live-Musik mit Verena und Meike | re-leuchtet | Kultur | Konzert | Titel „Live-Musik“ |
| 08.11.2026 | Ruhepol-Konzert der Neuen Philharmonie Westfalen | re-leuchtet | Kultur | Konzert | Titel „Konzert“ |
| 08.11.2026 | Ruhepol-Konzert der Neuen Philharmonie Westfalen | re-leuchtet | Kultur | Konzert | Titel „Konzert“ |
| 08.11.2026 | Ruhepol-Konzert der Neuen Philharmonie Westfalen | re-leuchtet | Kultur | Konzert | Titel „Konzert“ |
| 11.11.2026 | Rock-Pop-Akustik-Session | altstadtschmiede | Kultur | Konzert | Titel „Akustik-Session“ |
| 12.11.2026 | Mantra: Mitsingkonzert in der Friedhofskapelle Recklinghausen | stadt-re |  | Konzert | Titel „Mitsing“ |
| 13.11.2026 | Godzilla in the Kitchen, Mudfinger | backyard | Musik | Konzert | Quelle |
| 14.11.2026 | Live-Musik im Recklinghäuser: Desert Style | recklinghaeuser |  | Konzert | Titel „Live-Musik“ |
| 15.11.2026 | 2. Rathauskonzert - Zwischen Poesie und Tiefe - Romantische Klangwelten von Glinka bis Br… | stadt-re |  | Konzert | Titel „konzert“ |
| 18.11.2026 | NPW Barock: 1. Konzert - Da Spalla | stadt-re |  | Konzert | Titel „Konzert“ |
| 19.11.2026 | 1. Schulkonzert: Peter und der Wolf | stadt-re |  | Konzert | Titel „konzert“ |
| 20.11.2026 | Jazz in der Kunsthalle - Die Sparda Lounge: Jazz Akestra | stadt-re |  | Konzert | Titel „Jazz“ |
| 20.11.2026 | Tom Gaebel & His Orchestra: Best of | stadt-re |  | Konzert | Titel „Orchest“ |
| 20.11.2026 | Jazz in der Kunsthalle – Die Sparda Lounge | kunsthalle | Kunst | Konzert | Titel „Jazz“ |
| 20.11.2026 | Global Local Konzert | gastkirche | Veranstaltungen | Konzert | Titel „Konzert“ |
| 20.11.2026 | Mamma Mia - The Ultimative Abba Night | eventim | Konzert | Konzert | Kategorie „Konzert“ |
| 22.11.2026 | Konzertreihe - DEBUT um 11 e. V. | stadt-re |  | Konzert | Titel „Konzert“ |
| 26.11.2026 | Peter Orloff & Schwarzmeer Kosaken-Chor - Abschiedskonzert | eventim | Konzert | Konzert | Titel „Chor“ |
| 27.11.2026 | Adventssingen | stadt-re |  | Konzert | Titel „Adventssingen“ |
| 27.11.2026 | Livekonzert! Duo Gastspiel – Live unterm Sternenzelt! | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 28.11.2026 | Get Back - A Tribute to The Beatles | eventim | Konzert | Konzert | Kategorie „Konzert“ |
| 03.12.2026 | „VoxART“ Advent | stadt-re |  | Konzert | Beschreibung „konzert“ |
| 04.12.2026 | Blues in der Bude: Last Christmas | stadt-re |  | Konzert | Titel „Blues“ |
| 05.12.2026 | Kaffee- und Kuchenkonzert des Jugendsinfonieorchesters | stadt-re |  | Konzert | Titel „konzert“ |
| 06.12.2026 | Auf dem Weg zur Weihnacht | stadt-re |  | Konzert | Beschreibung „Oratori“ |
| 08.12.2026 | 4. Sinfoniekonzert - ÜberraschendEs | stadt-re |  | Konzert | Titel „Sinfoni“ |
| 10.12.2026 | Ein Abend zum Mitsingen mit "Sing-a-long" Duo | stadt-re |  | Konzert | Titel „Mitsing“ |
| 11.12.2026 | Johann Sebastian Bach: Weihnachtsoratorium | stadt-re |  | Konzert | Titel „oratorium“ |
| 18.12.2026 | Livekonzert! "Vom Klang der Sterne" | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 20.12.2026 | Weihnachtskonzert | stadt-re |  | Konzert | Titel „konzert“ |
| 23.12.2026 | Weihnachtskonzert - Musikalische Einstimmung auf die Feiertage | stadt-re |  | Konzert | Titel „konzert“ |
| 23.12.2026 | Weihnachtskonzert - Musikalische Einstimmung auf die Feiertage | stadt-re |  | Konzert | Titel „konzert“ |
| 03.01.2027 | Neujahrskonzert - Reisefieber | stadt-re |  | Konzert | Titel „konzert“ |
| 07.01.2027 | Neujahrskonzert - Reisefieber | stadt-re |  | Konzert | Titel „konzert“ |
| 13.01.2027 | Die Hommage an Udo Jürgens - Das Konzert mit Alex Parker | eventim | Konzert | Konzert | Titel „Konzert“ |
| 14.01.2027 | „Imagine“ - VOCALICIOUS- Chor | stadt-re |  | Konzert | Titel „Chor“ |
| 19.01.2027 | 5. Sinfoniekonzert - Heimat | stadt-re |  | Konzert | Titel „Sinfoni“ |
| 19.01.2027 | Smetana in Turnschuhen: „Má vlast“ (Mein Vaterland) | stadt-re |  | Konzert | Beschreibung „konzert“ |
| 22.01.2027 | Livekonzert! Sternenzelt und SphärenklängeWERNER WORSCHECH - intuitive, meditative Musik | sternwarte | Astronomie | Konzert | Quelle, Titel „konzert“ |
| 24.01.2027 | Konzertreihe - DEBUT um 11 e. V.- Auftakt zum Jubiläumsjahr 2027 | stadt-re |  | Konzert | Titel „Konzert“ |
| 31.01.2027 | 3. Rathauskonzert - He(a)r Story | stadt-re |  | Konzert | Titel „konzert“ |
| 06.02.2027 | Jazzy Februar: Lieder - Songs - Canciones - Músicas | stadt-re |  | Konzert | Titel „Jazz“ |
| 07.02.2027 | Erlebniskonzert: Magische Melodien: Anime & Ghibli live | stadt-re |  | Konzert | Titel „konzert“ |
| 11.02.2027 | Mantra Mitsingkonzert | stadt-re |  | Konzert | Titel „Mitsing“ |
| 12.02.2027 | Blues in der Bude: Greyhoud Georg Duo | stadt-re |  | Konzert | Titel „Blues“ |
| 14.02.2027 | Konzertreihe - DEBUT um 11 e. V. | stadt-re |  | Konzert | Titel „Konzert“ |
| 16.02.2027 | 6. Sinfoniekonzert - Per Aspera ad Astra | stadt-re |  | Konzert | Titel „Sinfoni“ |

## Musik-Stichworte im Titel, aber nicht Konzert (30)

Weites Suchmuster (u. a. Musik, Live, Lied, Klang, Duo, Festival, DJ, Musical, Oper), damit nichts durchrutscht. Spalte „Begründung“: Ergebnis der Durchsicht.

| Datum | Titel | Quelle | Rohkategorie | Art | Regel | Begründung |
|---|---|---|---|---|---|---|
| 25.11.2026 | Kunst im Ohr - Ein Livestream für alle Sinne 4 | vhs | Bildung | Ausstellung/Kunst | Titel „Kunst“ | richtig: Kunstbetrachtung als Stream, „Live“ heißt hier Livestream |
| 06.10.2026 | Miteinander singen | gastkirche | Veranstaltungen | Begegnung/Treffen | Titel „Miteinander singen“ | vertretbar: gemeinsames Singen zum Mitmachen, kein Auftritt (Test) |
| 03.11.2026 | Miteinander singen | gastkirche | Veranstaltungen | Begegnung/Treffen | Titel „Miteinander singen“ | vertretbar: gemeinsames Singen zum Mitmachen, kein Auftritt (Test) |
| 01.12.2026 | Miteinander singen | gastkirche | Veranstaltungen | Begegnung/Treffen | Titel „Miteinander singen“ | vertretbar: gemeinsames Singen zum Mitmachen, kein Auftritt (Test) |
| 06.12.2026 | André Rieus Weihnachtskonzert 2026: Let it Snow | cineworld | Kino | Kino | Quelle | richtig: Kinoübertragung (Cineworld), kein Konzert vor Ort |
| 25.10.2026 | Der Klang der Stradivari | cineworld | Kino | Kino | Quelle | richtig: Film |
| 26.10.2026 | Der Klang der Stradivari | cineworld | Kino | Kino | Quelle | richtig: Film |
| 28.10.2026 | Der Klang der Stradivari | cineworld | Kino | Kino | Quelle | richtig: Film |
| 08.11.2026 | Die Tribute von Panem - The Ballad of Songbirds & Snakes | cineworld | Kino | Kino | Quelle | richtig: Spielfilm, „Songbirds“ |
| 13.12.2026 | RBO 2026/ 27: Carmen (The Royal Opera) | cineworld | Kino | Kino | Quelle | richtig: Opernübertragung im Kino |
| 28.02.2027 | RBO 2026/ 27: Götterdämmerung (The Royal Opera) | cineworld | Kino | Kino | Quelle | richtig: Opernübertragung im Kino |
| 04.11.2026 | Rammstein - Live in Mexico City | cineworld | Kino | Kino | Quelle | richtig: Konzertfilm im Kino |
| 07.11.2026 | Rammstein - Live in Mexico City | cineworld | Kino | Kino | Quelle | richtig: Konzertfilm im Kino |
| 18.11.2026 | Grüne Erbsen und Kleine Rote Punkte -Warum Supermassive Schwarze Löcher so schnell so gro… | sternwarte | Astronomie | Lesung/Vortrag | Quelle | richtig: astronomischer Vortrag, „Punkte“ ist kein Punk (Fehlalarm behoben, Test) |
| 20.01.2027 | Keltika – Klänge aus der Anderswelt | sternwarte | Astronomie | Lesung/Vortrag | Quelle | vertretbar: Musikprogramm vom Band im Planetarium, kein Konzert; Sternwarte-Regel |
| 19.11.2026 | Live-Hörspiel mit den Vorlesern NRW: "James Bond - Im Angesicht des Todes" | stadt-re |  | Lesung/Vortrag | Titel „Hörspiel“ | richtig: Hörspiel/Lesung |
| 19.11.2026 | Live-Hörspiel mit den Vorlesern NRW: "James Bond - Im Angesicht des Todes" | stadtbibliothek | Bibliothek | Lesung/Vortrag | Titel „Hörspiel“ | richtig: Hörspiel/Lesung |
| 09.10.2026 | Mit Bowie zu Mond und Mars | sternwarte | Astronomie | Lesung/Vortrag | Quelle | vertretbar: Musikprogramm vom Band im Planetarium, kein Konzert; Sternwarte-Regel |
| 30.12.2026 | Musik im Sternenzelt | sternwarte | Astronomie | Lesung/Vortrag | Quelle | vertretbar: Musikprogramm vom Band im Planetarium (meditative Klänge), kein Konzert |
| 13.11.2026 | Musik. Zeit. Raum. - Musikprogramm im Planetarium | sternwarte | Astronomie | Lesung/Vortrag | Quelle | vertretbar: Musikprogramm vom Band im Planetarium, kein Konzert |
| 07.11.2026 | Abschlusswochenende mit DJ Moguai | manuell | Party | Party | Titel „DJ“ | richtig: DJ-Auftritt = Party |
| 19.12.2026 | DIE SCHLAGER PARTY | subergs |  | Party | Titel „PARTY“ | richtig |
| 07.11.2026 | DJ Moguai auf dem Rathausplatz | re-leuchtet | Kultur | Party | Titel „DJ“ | richtig: DJ-Auftritt = Party |
| 12.12.2026 | GECCO Party – House, Beats & Clubvibes | subergs |  | Party | Titel „Party“ | richtig |
| 31.10.2026 | Halloween mit Julius (80er/90er/00er & House) | manuell | Party | Party | Titel „Halloween“ | richtig |
| 15.10.2026 | "Blickpunkt Auge"-Beratung | manuell | Sonstiges | Sonstiges | - | richtig: Beratung; „Blickpunkt“ ist kein Punk (Pflichtfall, Test) |
| 25.10.2026 | Die Lieder meiner Nachbar*innen | altstadtschmiede | Kultur | Sonstiges | - | richtig: transkulturelles Mitmachprojekt mit Rezepttausch, kein Konzert (Fehlalarm behoben, Test) |
| 23.01.2027 | Selbstfürsorge durch Yoga und Klang – Ein Tagesretreat für dein Nervensystem | vhs | Bildung | Sport/Bewegung | Titel „Yoga“ | richtig: Yoga-Retreat |
| 21.01.2027 | Aladin - das Musical | stadt-re |  | Theater/Kabarett | Titel „Musical“ | richtig: Musical = Bühnenstück |
| 05.01.2027 | Best of Musicals | stadt-re |  | Theater/Kabarett | Titel „Musicals“ | vertretbar: Musical-Gala, Bühnenshow; Suche nach „Musical“ findet es |

## Sonstiges mit Musik-Wörtern in der Beschreibung (30)

Diese Termine bleiben bewusst bei Sonstiges, weil die Beschreibung nur mehrdeutige Wörter enthält (Musik, Hits, Klavier). Einzeln bewertet; ein Teil wird durch die Dublettenprüfung ohnehin ergänzt.

| Datum | Titel | Quelle | Beschreibung (Anfang) |
|---|---|---|---|
| 28.10.2026 | Adrian Buskies: Salty Sticks | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 30.10.2026 | CASCADES | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 30.10.2026 | Cascades | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 23.10.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 24.10.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 29.10.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 30.10.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 31.10.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 05.11.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 06.11.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 08.11.2026 | Das PortAl Formidabel – Träumen unterm Sternenhimmel | re-leuchtet | Tina Vogel-Portale und Roland Portale als Walking-Act mit bekannten und eigenen Hits zum Zuhören und Mitmache… |
| 25.10.2026 | Die Lieder meiner Nachbar*innen | altstadtschmiede | Ein transkulturelles Mitmachtprojekt Was verbindet uns über den Alltag hinaus? Oft sind es die kleinen Dinge:… |
| 28.10.2026 | Dr. Werner Koppe: Recklinghäuser Lichtspielhäuser | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 01.10.2026 | Flashmob zum Weltaltentag | manuell | Seniorenbeirat und Seniorenreferat der Stadt Recklinghausen laden unter dem Motto „Jung und Alt gemeinsam – T… |
| 06.11.2026 | Georg Möllers: Franziskanische Spuren in Recklinghausen – z… | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 02.02.2027 | Helge Schneider - Ellebogen vom Tich! | stadt-re | Helge Schneider Ellebogen vom Tich! Helge Schneider, der Perückenträger aus dem Ruhrgebiet, manövriert sich t… |
| 10.11.2026 | Henze100: TRISTAN | stadt-re | Richard Wagner: Englischhornsolo aus der Oper Tristan und Isolde Hans Werner Henze: Vier Präludien zu „Trista… |
| 16.10.2026 | Henze100: WO BIST DU DENN, und wo bin ich? | stadt-re | Ingeborg Bachmann und Max Frisch: Briefwechsel und Bühnenszenen Konzept, Text- und Musikauswahl: R. M. Klaas … |
| 03.11.2026 | Karl-Friedrich Hausberg | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 04.11.2026 | Katharina Fabri und Luisa Pohl | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 29.10.2026 | M. / A. / L. Schönert | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 01.11.2026 | Me and Lu | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 25.11.2026 | Moondog | stadt-re | Die Künstlerin Renate Rave-Schneider aus Münster präsentiert eine Performance über den blinden US-Musiker „Mo… |
| 31.10.2026 | Niclas Floer und Co | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 07.11.2026 | N‘Joy | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 27.10.2026 | Udo Herbst | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 24.10.2026 | Victoria Peiler Jamie Biernath | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 23.10.2026 | Vivian Swoboda | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 02.11.2026 | Vivian Swoboda | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |
| 08.11.2026 | wavering | re-leuchtet | Musikalische Vorführungen und Vorträge in der Gymnasialkirche |

