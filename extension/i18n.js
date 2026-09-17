// Prevodi popupa (bs, en, de, es, fr). Jezik je isti kao u aplikaciji; bez nje jezik browsera.

export const LANGUAGES = ["bs", "en", "de", "es", "fr"];

const TEXTS = {
  "popup.playing": ["Preuzmi video koji se pušta", "Download the playing video", "Laufendes Video herunterladen",
    "Descargar el vídeo en reproducción", "Télécharger la vidéo en cours"],
  "popup.playing_hint": [
    "YouTube, X, TikTok, Instagram, Facebook i oko 1.800 drugih sajtova. U feedu pokreni video koji želiš, pa klikni.",
    "YouTube, X, TikTok, Instagram, Facebook and about 1,800 other sites. In a feed, play the video you want, then click.",
    "YouTube, X, TikTok, Instagram, Facebook und etwa 1.800 weitere Seiten. Im Feed das gewünschte Video abspielen, dann klicken.",
    "YouTube, X, TikTok, Instagram, Facebook y unos 1.800 sitios más. En un feed, reproduce el vídeo que quieras y pulsa.",
    "YouTube, X, TikTok, Instagram, Facebook et environ 1 800 autres sites. Dans un fil, lancez la vidéo voulue puis cliquez."],
  "popup.page": ["Preuzmi link ove stranice", "Download this page's link", "Link dieser Seite herunterladen",
    "Descargar el enlace de esta página", "Télécharger le lien de cette page"],
  "popup.page_hint": ["Ako ništa ne uspije, izaberi pronađeni tok ispod.", "If nothing works, pick a detected stream below.",
    "Wenn nichts klappt, unten einen gefundenen Stream wählen.", "Si nada funciona, elige un flujo detectado abajo.",
    "Si rien ne marche, choisissez un flux détecté ci-dessous."],
  "popup.streams": ["Pronađeni video tokovi", "Detected video streams", "Gefundene Videostreams",
    "Flujos de vídeo detectados", "Flux vidéo détectés"],
  "popup.streams_empty": ["Još ništa. Pokreni video na stranici, pa ponovo otvori ovaj prozor.",
    "Nothing yet. Play a video on the page, then open this window again.",
    "Noch nichts. Video auf der Seite abspielen und dieses Fenster erneut öffnen.",
    "Nada todavía. Reproduce un vídeo en la página y vuelve a abrir esta ventana.",
    "Rien pour l'instant. Lancez une vidéo sur la page, puis rouvrez cette fenêtre."],
  "popup.drm": ["Ova stranica koristi DRM zaštitu (Netflix, Disney+, Prime Video i slično). Takav video se ne može preuzeti.",
    "This page uses DRM protection (Netflix, Disney+, Prime Video and similar). Such video cannot be downloaded.",
    "Diese Seite nutzt DRM-Schutz (Netflix, Disney+, Prime Video u. Ä.). Solche Videos können nicht heruntergeladen werden.",
    "Esta página usa protección DRM (Netflix, Disney+, Prime Video y similares). Ese vídeo no se puede descargar.",
    "Cette page utilise une protection DRM (Netflix, Disney+, Prime Video, etc.). Ces vidéos ne peuvent pas être téléchargées."],
  "popup.download": ["Preuzmi", "Download", "Laden", "Descargar", "Télécharger"],
  "popup.sending": ["Šaljem u Video Download…", "Sending to Video Download…", "Wird an Video Download gesendet…",
    "Enviando a Video Download…", "Envoi vers Video Download…"],
  "popup.added": ["Dodano u red za preuzimanje.", "Added to the download queue.", "Zur Download-Liste hinzugefügt.",
    "Añadido a la cola de descargas.", "Ajouté à la file de téléchargement."],
  "popup.launched": ["Aplikacija je pokrenuta i video je dodan u red.", "The app was started and the video was added to the queue.",
    "Die App wurde gestartet und das Video hinzugefügt.", "La aplicación se inició y el vídeo se añadió a la cola.",
    "L'application a été lancée et la vidéo ajoutée à la file."],
  "popup.sent": ["Poslano: {url}", "Sent: {url}", "Gesendet: {url}", "Enviado: {url}", "Envoyé : {url}"],
  "popup.failed": ["Slanje nije uspjelo.", "Sending failed.", "Senden fehlgeschlagen.", "El envío falló.", "L'envoi a échoué."],
  "status.running": ["aplikacija radi", "app is running", "App läuft", "aplicación abierta", "application ouverte"],
  "status.idle": ["pokreće se na klik", "starts on click", "startet beim Klick", "se abre al pulsar", "se lance au clic"],
  "status.offline": ["nije povezano", "not connected", "nicht verbunden", "no conectado", "non connecté"],
  "error.no-video": ["Na stranici nema videa. Pokreni video pa pokušaj ponovo.",
    "There is no video on the page. Play a video and try again.",
    "Auf der Seite ist kein Video. Video abspielen und erneut versuchen.",
    "No hay ningún vídeo en la página. Reproduce un vídeo e inténtalo de nuevo.",
    "Aucune vidéo sur la page. Lancez une vidéo et réessayez."],
  "error.feed-no-post": ["Nisam našao link ovog videa. Klikni na video da se otvori, pa pokušaj ponovo, ili kopiraj link desnim klikom. Dijagnostika: {detail}",
    "Could not find this video's link. Click the video to open it and try again, or copy the link with a right-click. Diagnostics: {detail}",
    "Link zu diesem Video nicht gefunden. Video anklicken, um es zu öffnen, und erneut versuchen, oder Link per Rechtsklick kopieren. Diagnose: {detail}",
    "No se encontró el enlace de este vídeo. Haz clic en el vídeo para abrirlo e inténtalo de nuevo, o copia el enlace con clic derecho. Diagnóstico: {detail}",
    "Lien de cette vidéo introuvable. Cliquez sur la vidéo pour l'ouvrir et réessayez, ou copiez le lien par clic droit. Diagnostic : {detail}"],
  "error.story-login": ["Instagram stories traže prijavu. Klikni ponovo i u prozoru browsera dozvoli pristup kolačićima.",
    "Instagram stories require login. Click again and allow cookie access in the browser dialog.",
    "Instagram-Stories erfordern eine Anmeldung. Erneut klicken und im Browserdialog den Cookie-Zugriff erlauben.",
    "Las historias de Instagram requieren iniciar sesión. Pulsa de nuevo y permite el acceso a cookies en el diálogo del navegador.",
    "Les stories Instagram exigent une connexion. Cliquez à nouveau et autorisez l'accès aux cookies dans la fenêtre du navigateur."],
  "error.live": ["Ovo je prenos uživo (LIVE) i ne preuzima se. Preuzmi ga kad se prenos završi i snimak bude objavljen.",
    "This is a live stream and is not downloaded. Download it after the stream ends and the recording is published.",
    "Das ist ein Livestream und wird nicht heruntergeladen. Nach dem Ende laden, wenn die Aufzeichnung veröffentlicht ist.",
    "Es una transmisión en directo y no se descarga. Descárgala cuando termine y se publique la grabación.",
    "C'est un direct : il n'est pas téléchargé. Téléchargez-le quand le direct est terminé et l'enregistrement publié."],
  "error.media-gone": ["Tok više nije na listi. Osvježi stranicu i pokreni video ponovo.",
    "The stream is no longer in the list. Reload the page and play the video again.",
    "Der Stream ist nicht mehr in der Liste. Seite neu laden und Video erneut abspielen.",
    "El flujo ya no está en la lista. Recarga la página y reproduce el vídeo de nuevo.",
    "Le flux n'est plus dans la liste. Rechargez la page et relancez la vidéo."],
  "error.not-connected": ["Aplikacija nije povezana sa browserom. Pokreni Video Download jednom ručno.",
    "The app is not connected to the browser. Start Video Download manually once.",
    "Die App ist nicht mit dem Browser verbunden. Video Download einmal manuell starten.",
    "La aplicación no está conectada al navegador. Abre Video Download manualmente una vez.",
    "L'application n'est pas connectée au navigateur. Lancez Video Download une fois manuellement."],
  "error.no-reply": ["Aplikacija nije odgovorila.", "The app did not respond.", "Die App hat nicht geantwortet.",
    "La aplicación no respondió.", "L'application n'a pas répondu."],
  "error.app-timeout": ["Aplikacija se nije javila na vrijeme.", "The app did not start in time.",
    "Die App hat sich nicht rechtzeitig gemeldet.", "La aplicación no respondió a tiempo.",
    "L'application n'a pas répondu à temps."],
  "error.connection": ["Veza sa aplikacijom nije uspjela: {detail}", "Connection to the app failed: {detail}",
    "Verbindung zur App fehlgeschlagen: {detail}", "Falló la conexión con la aplicación: {detail}",
    "La connexion à l'application a échoué : {detail}"],
};

export function pickLanguage(code) {
  const base = String(code || "").replace("-", "_").split("_")[0].toLowerCase();
  if (["bs", "sr", "hr", "sh", "cnr"].includes(base)) return "bs";
  return LANGUAGES.includes(base) ? base : "en";
}

export function translate(language, key, values = {}) {
  const texts = TEXTS[key];
  if (!texts) return key;
  const text = texts[Math.max(0, LANGUAGES.indexOf(language))] ?? texts[1];
  return text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
}

export const TEXT_KEYS = Object.keys(TEXTS);
export const RAW_TEXTS = TEXTS;
