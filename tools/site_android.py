"""Android tutorijal na sajtu: tekstovi na pet jezika i HTML bez dodatnog JavaScripta."""

import html

PAGE = "android-guide.html"


def guide_body(lang: str, apk_url: str, download_label: str) -> tuple[str, str, str]:
    """Samostalni vodič; sistemske postavke korisnik otvara ručno prema uputstvu."""
    t = TEXT[lang]
    esc = html.escape
    title = "Android — " + t["dev_guide_title"]
    parts = [f'<h1>{esc(title)}</h1>', f'<p class="lead">{esc(t["dev_guide_intro"])}</p>']
    for section in ("install", "enable", "usb", "wifi", "finish"):
        lines = t[f"dev_{section}_body"].splitlines()
        content = "\n".join(f'<p>{esc(line)}</p>' for line in lines)
        parts.append(f'<section class="box"><h2 style="margin-top:0">{esc(t[f"dev_{section}_title"])}</h2>{content}</section>')
    parts.append(f'<p>{esc(t["dev_unavailable_hint"])}</p>')
    parts.append(f'<p><a href="https://developer.android.com/studio/debug/dev-options">{esc(t["dev_official_help"])}</a></p>')
    parts.append(f'<p><a href="https://developer.android.com/studio/run/device#wireless">{esc(t["dev_pairing_help"])}</a></p>')
    parts.append(f'<p><a class="btn" href="{esc(apk_url)}">{esc(download_label)}</a></p>')
    return title, t["dev_guide_subtitle"], "\n".join(parts)


def hub_card(lang: str) -> str:
    t = TEXT[lang]
    return (f'<li><a href="{PAGE}"><b>Android — {html.escape(t["dev_guide_title"])}</b></a>'
            f'<br><span>{html.escape(t["dev_guide_subtitle"])}</span></li>')

TEXT = {
    "en": {
        "dev_guide_title": "Developer options guide",
        "dev_guide_subtitle": "Phone setup for testing and support",
        "dev_guide_intro": "Video Download works without Developer options. Use this guide only when connecting your phone to a computer for testing or troubleshooting.",
        "dev_install_title": "Installing an APK is separate",
        "dev_install_body": "To install the downloaded APK, allow installs from the browser or file manager that opens it. For updates inside Video Download, allow this app instead. Developer options and USB debugging are not required.",
        "dev_enable_title": "1. Enable Developer options",
        "dev_enable_body": "Samsung: Settings → About phone → Software information → Build number.\nOther phones: Settings → About phone → Build number (the path may differ).\nTap Build number seven times. If asked, enter your phone unlock PIN on the system screen. Return to Settings and find Developer options, sometimes under System.",
        "dev_usb_title": "2. Connect with USB",
        "dev_usb_body": "In Developer options, enable USB debugging. Connect a data-capable USB cable to your own computer. When the phone asks to allow USB debugging, approve only the computer you trust. Testing from the computer also requires Android Platform Tools (ADB) or Android Studio.",
        "dev_wifi_title": "3. Or connect over Wi-Fi",
        "dev_wifi_body": "On Android 11 or later, connect the phone and computer to the same trusted Wi-Fi network. Open Developer options → Wireless debugging → Pair device with pairing code. Pair through Android Studio or ADB on the computer. The pairing code and port are shown on the phone; the connection port can be different. Do not share the code publicly.",
        "dev_finish_title": "4. After testing",
        "dev_finish_body": "Turn off USB debugging and Wireless debugging when finished. If the computer is no longer trusted, revoke USB debugging authorizations and forget its entry under Paired devices. Developer options can also be switched off.",
        "dev_unavailable_hint": "Menu names vary. If you cannot find an option, use the search in Settings. Managed phones may restrict these options. On Samsung, Auto Blocker may block debugging; follow the system message or ask support.",
        "dev_official_help": "Official Android guide",
        "dev_pairing_help": "Wi-Fi pairing instructions"
    },
    "bs": {
        "dev_guide_title": "Tutorijal: opcije za programere",
        "dev_guide_subtitle": "Podešavanje telefona za testiranje i podršku",
        "dev_guide_intro": "Video Download radi bez opcija za programere. Ovaj vodič koristi samo kada povezuješ telefon s računarom radi testiranja ili otklanjanja grešaka.",
        "dev_install_title": "Instalacija APK-a je odvojena",
        "dev_install_body": "Za instalaciju preuzetog APK-a dozvoli instaliranje pregledniku ili upravitelju fajlova koji ga otvara. Za ažuriranje iz Video Download dozvolu daješ ovoj aplikaciji. Opcije za programere i USB otklanjanje grešaka nisu potrebni.",
        "dev_enable_title": "1. Uključi opcije za programere",
        "dev_enable_body": "Samsung: Postavke → O telefonu → Informacije o softveru → Broj verzije (Build number).\nOstali telefoni: Postavke → O telefonu → Broj verzije (putanja može biti drugačija).\nDodirni Broj verzije sedam puta. Ako telefon traži, unesi PIN za otključavanje u sistemskom prozoru. Vrati se u Postavke i pronađi Opcije za programere, ponekad u odjeljku Sistem.",
        "dev_usb_title": "2. Poveži USB kablom",
        "dev_usb_body": "U opcijama za programere uključi USB otklanjanje grešaka (USB debugging). Poveži telefon sa svojim računarom kablom koji prenosi podatke. Kad telefon traži dozvolu, potvrdi samo računar kojem vjeruješ. Za testiranje s računara potrebni su i Android Platform Tools (ADB) ili Android Studio.",
        "dev_wifi_title": "3. Ili poveži preko Wi-Fi mreže",
        "dev_wifi_body": "Na Androidu 11 ili novijem poveži telefon i računar na istu pouzdanu Wi-Fi mrežu. Otvori Opcije za programere → Bežično otklanjanje grešaka (Wireless debugging) → Upari uređaj kodom. Uparivanje obavi kroz Android Studio ili ADB na računaru. Kod i port za uparivanje pišu na telefonu; port za povezivanje može biti drugačiji. Kod ne dijeli javno.",
        "dev_finish_title": "4. Nakon testiranja",
        "dev_finish_body": "Isključi USB i bežično otklanjanje grešaka kada završiš. Ako više ne vjeruješ računaru, opozovi USB ovlaštenja i ukloni ga iz liste uparenih uređaja. Možeš isključiti i same opcije za programere.",
        "dev_unavailable_hint": "Nazivi menija se razlikuju. Ako ne nalaziš neku opciju, koristi pretragu u Postavkama. Službeni telefoni mogu imati ograničenja. Na Samsungu Auto Blocker može blokirati otklanjanje grešaka; prati sistemsku poruku ili se obrati podršci.",
        "dev_official_help": "Zvanični Android vodič",
        "dev_pairing_help": "Uputstvo za Wi-Fi uparivanje"
    },
    "de": {
        "dev_guide_title": "Anleitung: Entwickleroptionen",
        "dev_guide_subtitle": "Telefon für Tests und Support einrichten",
        "dev_guide_intro": "Video Download funktioniert ohne Entwickleroptionen. Diese Anleitung brauchst du nur, um dein Telefon für Tests oder zur Fehlersuche mit einem Computer zu verbinden.",
        "dev_install_title": "APK-Installation ist unabhängig",
        "dev_install_body": "Erlaube zum Installieren der heruntergeladenen APK die Installation über den Browser oder Dateimanager, der sie öffnet. Für Updates in Video Download erlaubst du es dieser App. Entwickleroptionen und USB-Debugging sind nicht erforderlich.",
        "dev_enable_title": "1. Entwickleroptionen aktivieren",
        "dev_enable_body": "Samsung: Einstellungen → Telefoninfo → Softwareinformationen → Buildnummer.\nAndere Telefone: Einstellungen → Über das Telefon → Buildnummer (der Pfad kann abweichen).\nTippe siebenmal auf Buildnummer. Gib bei Nachfrage die Entsperr-PIN im Systemdialog ein. Suche danach in den Einstellungen nach Entwickleroptionen, manchmal unter System.",
        "dev_usb_title": "2. Per USB verbinden",
        "dev_usb_body": "Aktiviere USB-Debugging in den Entwickleroptionen. Verbinde dein Telefon mit einem Datenkabel mit deinem eigenen Computer. Bestätige die USB-Debugging-Anfrage nur für einen vertrauenswürdigen Computer. Auf dem Computer werden auch Android Platform Tools (ADB) oder Android Studio benötigt.",
        "dev_wifi_title": "3. Oder über WLAN verbinden",
        "dev_wifi_body": "Ab Android 11: Verbinde Telefon und Computer mit demselben vertrauenswürdigen WLAN. Öffne Entwickleroptionen → Drahtloses Debugging → Gerät mit Kopplungscode koppeln. Kopple es über Android Studio oder ADB am Computer. Code und Kopplungsport stehen auf dem Telefon; der Verbindungsport kann abweichen. Teile den Code nicht öffentlich.",
        "dev_finish_title": "4. Nach dem Test",
        "dev_finish_body": "Schalte USB-Debugging und drahtloses Debugging anschließend aus. Vertraust du dem Computer nicht mehr, widerrufe die USB-Debugging-Autorisierungen und entferne ihn aus den gekoppelten Geräten. Auch die Entwickleroptionen lassen sich ausschalten.",
        "dev_unavailable_hint": "Menünamen können abweichen. Findest du eine Option nicht, nutze die Suche in den Einstellungen. Verwaltete Telefone können diese Optionen einschränken. Auf Samsung kann die Automatische Sperre das Debugging blockieren; beachte die Systemmeldung oder frage den Support.",
        "dev_official_help": "Offizielle Android-Anleitung",
        "dev_pairing_help": "Anleitung zur WLAN-Kopplung"
    },
    "es": {
        "dev_guide_title": "Guía: opciones de desarrollador",
        "dev_guide_subtitle": "Configurar el teléfono para pruebas y soporte",
        "dev_guide_intro": "Video Download funciona sin opciones de desarrollador. Usa esta guía solo para conectar el teléfono a un ordenador y realizar pruebas o resolver problemas.",
        "dev_install_title": "La instalación del APK es independiente",
        "dev_install_body": "Para instalar el APK descargado, permite la instalación desde el navegador o gestor de archivos que lo abre. Para actualizar desde Video Download, permite la instalación desde esta aplicación. No se necesitan opciones de desarrollador ni depuración USB.",
        "dev_enable_title": "1. Activar opciones de desarrollador",
        "dev_enable_body": "Samsung: Ajustes → Acerca del teléfono → Información de software → Número de compilación.\nOtros teléfonos: Ajustes → Acerca del teléfono → Número de compilación (la ruta puede variar).\nToca Número de compilación siete veces. Si se solicita, introduce el PIN de desbloqueo en la pantalla del sistema. Vuelve a Ajustes y busca Opciones de desarrollador, a veces dentro de Sistema.",
        "dev_usb_title": "2. Conectar por USB",
        "dev_usb_body": "Activa Depuración USB en las opciones de desarrollador. Conecta el teléfono a tu ordenador con un cable que transmita datos. Autoriza la depuración solo si confías en ese ordenador. El ordenador también necesita Android Platform Tools (ADB) o Android Studio.",
        "dev_wifi_title": "3. O conectar por Wi-Fi",
        "dev_wifi_body": "En Android 11 o posterior, conecta el teléfono y el ordenador a la misma red Wi-Fi de confianza. Abre Opciones de desarrollador → Depuración inalámbrica → Vincular dispositivo con código. Vincúlalo con Android Studio o ADB en el ordenador. El código y el puerto de vinculación aparecen en el teléfono; el puerto de conexión puede ser distinto. No publiques el código.",
        "dev_finish_title": "4. Al terminar las pruebas",
        "dev_finish_body": "Desactiva la depuración USB e inalámbrica al terminar. Si ya no confías en el ordenador, revoca las autorizaciones de depuración USB y elimínalo de los dispositivos vinculados. También puedes desactivar las opciones de desarrollador.",
        "dev_unavailable_hint": "Los nombres de los menús varían. Si no encuentras una opción, usa la búsqueda de Ajustes. Los teléfonos administrados pueden restringir estas opciones. En Samsung, el Bloqueador automático puede impedir la depuración; sigue el mensaje del sistema o contacta con soporte.",
        "dev_official_help": "Guía oficial de Android",
        "dev_pairing_help": "Instrucciones para vincular por Wi-Fi"
    },
    "fr": {
        "dev_guide_title": "Guide : options pour développeurs",
        "dev_guide_subtitle": "Configurer le téléphone pour les tests et le support",
        "dev_guide_intro": "Video Download fonctionne sans les options pour développeurs. Utilise ce guide uniquement pour connecter ton téléphone à un ordinateur afin de tester ou de résoudre un problème.",
        "dev_install_title": "Installer un APK est indépendant",
        "dev_install_body": "Pour installer le fichier APK téléchargé, autorise le navigateur ou le gestionnaire de fichiers qui l’ouvre à installer des applications. Pour une mise à jour dans Video Download, autorise cette application. Les options pour développeurs et le débogage USB ne sont pas nécessaires.",
        "dev_enable_title": "1. Activer les options pour développeurs",
        "dev_enable_body": "Samsung : Paramètres → À propos du téléphone → Informations sur le logiciel → Numéro de version.\nAutres téléphones : Paramètres → À propos du téléphone → Numéro de build (le chemin peut varier).\nAppuie sept fois sur le numéro. Si demandé, saisis le code de déverrouillage dans la fenêtre système. Reviens aux Paramètres et cherche Options de développement, parfois dans Système.",
        "dev_usb_title": "2. Se connecter par USB",
        "dev_usb_body": "Active le débogage USB dans les options de développement. Relie le téléphone à ton ordinateur avec un câble permettant le transfert de données. N’autorise le débogage que pour un ordinateur de confiance. Android Platform Tools (ADB) ou Android Studio est aussi nécessaire sur l’ordinateur.",
        "dev_wifi_title": "3. Ou se connecter par Wi-Fi",
        "dev_wifi_body": "Sous Android 11 ou version ultérieure, connecte le téléphone et l’ordinateur au même réseau Wi-Fi de confiance. Ouvre Options de développement → Débogage sans fil → Associer l’appareil avec un code. Associe-le via Android Studio ou ADB sur l’ordinateur. Le téléphone affiche le code et le port d’association ; le port de connexion peut être différent. Ne publie pas le code.",
        "dev_finish_title": "4. Après les tests",
        "dev_finish_body": "Désactive le débogage USB et sans fil après utilisation. Si tu ne fais plus confiance à l’ordinateur, révoque les autorisations de débogage USB et supprime-le des appareils associés. Tu peux aussi désactiver les options de développement.",
        "dev_unavailable_hint": "Les noms des menus varient. Si tu ne trouves pas une option, utilise la recherche des Paramètres. Les téléphones gérés peuvent restreindre ces options. Sur Samsung, le Bloqueur automatique peut empêcher le débogage ; suis le message système ou contacte le support.",
        "dev_official_help": "Guide officiel Android",
        "dev_pairing_help": "Instructions d’association Wi-Fi"
    }
}
