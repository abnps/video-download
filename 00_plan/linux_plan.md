# Linux (beta): plan

Napisano 28.10.2026 (Ahmed: „Napravi plan"). Odluke označene **[Ahmed]** čekaju njegovu potvrdu.
Početak: poslije izdanja 1.0.5. Ništa plaćeno (pravilo „ništa plaćeno do zarade"): gradnja na GitHubu je besplatna
za javni repo, Linux ne traži nalog ni potpis kao Apple.

## Cilj

Isti program kao na Windowsu i Macu (PySide6, yt-dlp, ffmpeg, Node), kao **Linux (beta)** za x86_64:
preuzmi jedan fajl, pokreni, program se sam ažurira i radi s dodatkom za Chrome, Edge i Firefox. 5 jezika kao i sada.

## Odluke

| # | Pitanje | Prijedlog | Status |
|---|---|---|---|
| L1 | Format paketa | **AppImage** (jedan fajl, bez instalacije i administratora, radi na Ubuntu/Mint/Debian/Fedora…) | [Ahmed] |
| L2 | Najstariji sistem | glibc kao Ubuntu 22.04 (gradnja na `ubuntu-22.04`, pa radi i na novijim) | [Ahmed] |
| L3 | Arhitektura | samo x86_64 (ARM/Raspberry Pi tek ako neko traži) | [Ahmed] |
| L4 | Flatpak/Flathub, .deb, AUR | ne sada (Flatpak sandbox otežava vezu s dodatkom); kasnije po potražnji | [Ahmed] |
| L5 | Oznaka na sajtu | „Linux (beta)", kao Mac, dok ga ne proba bar par ljudi | **potvrđeno** (Ahmed 29.10.2026) |

## Šta treba u kodu (tačno 10 modula zavisi od sistema)

| Dio | Fajl | Linux |
|---|---|---|
| Podaci programa | `runtime.user_data_base`, `native_host.data_dir` | `$XDG_DATA_HOME` ili `~/.local/share/VideoDownload` |
| Podešavanja | `gui._settings` (QSettings) | Qt sam koristi `~/.config/VideoDownload/` |
| „Otvori folder", „Pusti" | `desktop.reveal`, `play_file` | `xdg-open` (folder; označavanje fajla nije standardno) |
| Alati u paketu | `runtime.tools_dir`, `exe()` | `ffmpeg`, `ffprobe`, `node` bez `.exe`, u AppImage-u |
| Veza s dodatkom | `native_messaging.install_native_host` | JSON manifest u `~/.config/google-chrome/NativeMessagingHosts/`, `~/.config/chromium/…`, `~/.config/microsoft-edge/…`, `~/.config/BraveSoftware/Brave-Browser/…`, `~/.mozilla/native-messaging-hosts/` |
| Putanja hosta u manifestu | `native_host` | AppImage se mijenja pri ažuriranju: host je mala skripta u `~/.local/share/VideoDownload/` koja poziva trenutni AppImage (`$APPIMAGE`) |
| Pronalaženje browsera | `dialogs.browser_exe` | `shutil.which("google-chrome", "microsoft-edge", "firefox", …)` |
| Samoažuriranje | `updater.py` | kao Mac: potpisani `release-linux.json` (+ `.sig`) u izdanju; novi AppImage se preuzme pored starog, provjeri SHA-256 i potpis, pa zamijeni |
| Taskbar napredak, tamni naslov | `winshell.py` | samo Windows; na Linuxu se preskače (već je zaštićeno) |
| Prečica u meniju | novo | `.desktop` fajl i ikona pri prvom pokretanju (pitati korisnika), uklanjanje iz Pomoći |

Pravne stvari: licencni ugovor i `licenses/` idu u AppImage (`legal.py` već zna za `lib/pythonX.Y` na Mac/Linuxu);
ffmpeg se pakuje kao statički build s izvornim kodom na istim linkovima kao za Windows.

## Gradnja i izdanje

1. `tools/build_linux.py` (po uzoru na `build_macos.py`): PyInstaller → `appimagetool` → `VideoDownload-linux-x86_64-<verzija>.AppImage` + `.sha256`.
2. `.github/workflows/linux.yml` (po uzoru na `macos.yml`): `runs-on: ubuntu-22.04`, gradi iz taga i dodaje fajlove **nacrtu** izdanja.
3. `tools/sign_linux.py` (kao `sign_macos.py`): lokalno potpisuje `release-linux.json` ključem `release-signing-key.pem`.
4. `tools/publish_release.py`: Linux fajlovi u spisku obaveznih (sa sadašnjih 14 na 18), provjera potpisa i verzije.
5. Stalni link `VideoDownload-linux-x86_64.AppImage` za sajt.

## Sajt

- Četvrta kartica „Linux (beta)" u izboru platforme (`site.js` već bira po sistemu posjetioca), 5 jezika.
- Kratko uputstvo: preuzmi, desni klik → Svojstva → „Dozvoli pokretanje" (ili `chmod +x`), pokreni.
- Dodatak: Firefox i Edge iz prodavnica, Chrome ručno (isti 3 koraka).
- Zahtjevi: Ubuntu 22.04 ili noviji (ili slično), x86_64.

## Proba (prije objave)

- **WSL2 s WSLg** na Ahmedovom Windowsu 11 (besplatno) za brzu probu prozora i preuzimanja.
- **Hyper-V** virtuelna mašina s Ubuntu 24.04 i Fedora za pravu probu: AppImage, prečica, dodatak u Chromeu i Firefoxu, samoažuriranje.
- Bar jedan stvarni korisnik Linuxa (prijatelj ili Discord) prije oznake bez „beta".
- Testovi: postojeći testovi idu i na `ubuntu-latest` u CI (`tests.yml` dobija Linux posao).

## Redoslijed i procjena

| Korak | Trajanje |
|---|---|
| Kod: folderi, xdg-open, alati, browseri | ~1 dan |
| Veza s dodatkom (manifesti, host za AppImage) | ~1 dan |
| AppImage, `build_linux.py`, `linux.yml` | ~1 dan |
| Samoažuriranje (`release-linux.json`, potpis) | ~0,5 dana |
| Sajt (5 jezika) + `publish_release.py` | ~0,5 dana |
| Proba (WSL, VM, stvarni korisnik) i ispravke | 1–2 dana |

Ukupno **oko 4–6 dana** rada. Objava samo na Ahmedovo „objavi", kao dio redovnog izdanja (npr. 1.1.0).

## Rizici

- Različite distribucije (stari glibc, Wayland/X11): gradnja na 22.04 i proba na 2–3 sistema.
- AppImage traži FUSE na nekim novim sistemima: na sajtu kratko uputstvo (`--appimage-extract-and-run` kao rezerva).
- Flatpak verzije browsera ne vide manifest u `~/.config`: napomena na sajtu (preporuka: browser iz paketa distribucije).

## Stanje (28.10.2026, grana `linux`, nije poslano na GitHub)

- [x] Kod: XDG putanje, `restore_system_env` (LD_LIBRARY_PATH za xdg-open/browser/node), otvaranje foldera,
      jezik iz `~/.config/VideoDownload/VideoDownload.conf`, browseri iz PATH-a, Linux tekstovi (Ctrl+L), FFmpeg licenca.
- [x] Veza s dodatkom: manifesti u `~/.config/{google-chrome,chromium,microsoft-edge,BraveSoftware/Brave-Browser}` i
      `~/.mozilla/native-messaging-hosts`; host je sam AppImage (`$APPIMAGE`). Dodatak za Chrome se kopira na stalno
      mjesto (`~/.local/share/VideoDownload/extension`), jer se AppImage otvara na drugoj /tmp putanji.
- [x] Samoažuriranje: `release-linux.json` + `.sig`, novi AppImage pored starog, zamjena poslije gašenja.
- [x] `tools/build_linux.py`, `.github/workflows/linux.yml` (Ubuntu 22.04, svi testovi + self-test paketa i hosta),
      `tools/sign_linux.py`, 5 Linux fajlova obavezno u `publish_release.py` (19 ukupno).
- [x] Sajt: dugme i kartica „Linux (beta)" u 5 jezika.
- [ ] Prva stvarna gradnja (posao „Linux paket" na GitHubu ili WSL) i proba prozora, preuzimanja, dodatka, ažuriranja.
- [ ] Statistika: Linux kolona u `tools/statistika.py` (vlastita.py već broji Linux).
- [ ] Prečica u meniju (.desktop pri prvom pokretanju) — poslije prve probe.
