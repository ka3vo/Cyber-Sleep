import os
import re
import sys
from datetime import datetime, timezone

# pip install colorama pyfiglet requests phonenumbers dnspython python-whois
import requests
import phonenumbers
from phonenumbers import geocoder, carrier as pn_carrier
import dns.resolver
import whois as whois_lib
import socket
import secrets
import string as string_mod
import qrcode
import speedtest
from colorama import init, Fore, Style
import pyfiglet
from PIL import Image, ExifTags

init(autoreset=True)
COLOR = Fore.LIGHTRED_EX + Style.BRIGHT      # couleur principale (rouge)
WARN = Fore.LIGHTYELLOW_EX + Style.BRIGHT    # erreurs / avertissements
OK = Fore.LIGHTGREEN_EX + Style.BRIGHT       # succès
WIDTH = 100

# token.txt est créé à côté du script (ou du .exe), jamais dans le code
BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
TOKEN_FILE = os.path.join(BASE_DIR, "token.txt")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.txt")
API = "https://discord.com/api/v10"


# ---------- Réglages (son) ----------
def sound_enabled():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() != "sound=off"
    return True


def toggle_sound():
    new_state = not sound_enabled()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write("sound=on" if new_state else "sound=off")
    print(OK + f"\nSon {'activé' if new_state else 'désactivé'}.")
    beep()
    pause()


def beep():
    """Petit jingle façon sci-fi joué à la fin d'une action."""
    if not sound_enabled():
        return
    try:
        if os.name == "nt":
            import winsound
            for freq, duree in ((660, 60), (880, 60), (1320, 90)):
                winsound.Beep(freq, duree)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass

# Badges Discord (public_flags)
BADGES = {
    1: "Discord Staff",
    2: "Partenaire Discord",
    4: "HypeSquad Events",
    8: "Bug Hunter niveau 1",
    64: "HypeSquad Bravery",
    128: "HypeSquad Brilliance",
    256: "HypeSquad Balance",
    512: "Early Supporter",
    16384: "Bug Hunter niveau 2",
    131072: "Early Verified Bot Developer",
    262144: "Certified Moderator",
    4194304: "Active Developer",
}


# ---------- Affichage ----------
def clear():
    os.system("cls" if os.name == "nt" else "clear")


GRADIENT = [196, 160, 160, 124, 124, 88]   # dégradé rouge (clair -> sombre)


def banner(title="CYBER   SLEEP"):
    """Bannière utilisée pour les écrans secondaires (guide, etc.)."""
    clear()
    art = pyfiglet.figlet_format(title, font="ansi_shadow", width=250)
    lines = [l for l in art.split("\n") if l.strip()]
    print()
    for i, line in enumerate(lines):
        shade = GRADIENT[min(i, len(GRADIENT) - 1)]
        print(f"\033[1;38;5;{shade}m{line}\033[0m")
    print(COLOR + "  discord & osint toolkit".center(90))
    print()


def pause():
    beep()
    input(COLOR + "\n[+] Appuie sur Entrée pour continuer...")


def boot_sequence():
    """Petit écran de chargement affiché au démarrage du tool."""
    import time
    clear()
    etapes = [
        "Initialisation du système...",
        "Connexion aux serveurs Discord...",
        "Chargement du module OSINT...",
        "Chargement du module Outils...",
        "Vérification de l'intégrité...",
        "Accès autorisé.",
    ]
    for etape in etapes:
        print(COLOR + f"[~] {etape}")
        time.sleep(0.35)

    largeur = 40
    print()
    for i in range(largeur + 1):
        barre = "█" * i + "░" * (largeur - i)
        pct = int(i / largeur * 100)
        print(COLOR + f"\r[{barre}] {pct}%", end="", flush=True)
        time.sleep(0.015)
    print()
    time.sleep(0.4)


# ---------- Saisies ----------
def ask_discord_id(label="ID Discord"):
    while True:
        value = input(COLOR + f"[+] {label} : ").strip()
        if value.isdigit() and 17 <= len(value) <= 20:
            return value
        print(WARN + "ID invalide (17 à 20 chiffres attendus).")


def ask_text(label):
    return input(COLOR + f"[+] {label} : ").strip()


# ---------- Token ----------
def show_bot_guide():
    banner("GUIDE")
    print(COLOR + "Comment obtenir ton token de bot (2 minutes) :\n")
    print(COLOR + " 1. Va sur  https://discord.com/developers/applications")
    print(COLOR + " 2. Clique sur 'New Application', donne un nom, valide")
    print(COLOR + " 3. Menu de gauche : 'Bot'")
    print(COLOR + " 4. Clique sur 'Reset Token', puis 'Copy'")
    print(COLOR + " 5. Colle le token dans ce tool\n")
    print(WARN + "Ne partage JAMAIS ton token : il donne le contrôle de ton bot.")
    print(WARN + "Pas besoin d'inviter le bot sur un serveur pour ce tool.")


def check_token(token):
    """Vérifie que le token est valide. Renvoie (ok, nom_du_bot)."""
    try:
        r = requests.get(
            f"{API}/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
    except requests.RequestException:
        return None, None  # pas de connexion
    if r.status_code == 200:
        return True, r.json().get("username")
    return False, None


def setup_token():
    """Guide + saisie + vérification + sauvegarde. Renvoie le token ou None."""
    show_bot_guide()
    print()
    token = ask_text("Colle ton token ici (ou Entrée pour annuler)")
    if not token:
        return None

    ok, name = check_token(token)
    if ok is None:
        print(WARN + "\nImpossible de joindre Discord (vérifie ta connexion).")
        pause()
        return None
    if not ok:
        print(WARN + "\nToken invalide. Vérifie que tu as bien tout copié.")
        pause()
        return None

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    print(OK + f"\nToken valide (bot : {name}). Enregistré dans token.txt")
    pause()
    return token


def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    return setup_token()


def delete_token():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(OK + "\nToken supprimé.")
    else:
        print(WARN + "\nAucun token enregistré.")
    pause()


# ---------- Actions ----------
def info_utilisateur():
    token = get_token()
    if not token:
        return

    uid = ask_discord_id("ID de l'utilisateur")

    try:
        r = requests.get(
            f"{API}/users/{uid}",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre Discord (vérifie ta connexion).")
        return pause()

    if r.status_code == 401:
        print(WARN + "\nToken invalide ou expiré. Va dans Paramètres pour le changer.")
        return pause()
    if r.status_code == 404:
        print(WARN + "\nAucun utilisateur trouvé avec cet ID.")
        return pause()
    if r.status_code == 429:
        print(WARN + "\nTrop de requêtes, attends quelques secondes.")
        return pause()
    if r.status_code != 200:
        print(WARN + f"\nErreur Discord ({r.status_code}).")
        return pause()

    u = r.json()

    # Date de création (contenue dans l'ID)
    ts = ((int(uid) >> 22) + 1420070400000) / 1000
    created = datetime.fromtimestamp(ts, tz=timezone.utc)
    age_jours = (datetime.now(timezone.utc) - created).days

    avatar = (
        f"https://cdn.discordapp.com/avatars/{uid}/{u['avatar']}.png?size=1024"
        if u.get("avatar") else "Aucun"
    )
    banner_url = (
        f"https://cdn.discordapp.com/banners/{uid}/{u['banner']}.png?size=1024"
        if u.get("banner") else "Aucune"
    )

    flags = u.get("public_flags", 0)
    badges = [name for bit, name in BADGES.items() if flags & bit]

    color = u.get("accent_color")
    color_txt = f"#{color:06X}" if color is not None else "Aucune"

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Pseudo          : {u.get('username')}")
    print(COLOR + f" Nom affiché     : {u.get('global_name') or 'Aucun'}")
    print(COLOR + f" ID              : {u.get('id')}")
    print(COLOR + f" Type            : {'Bot' if u.get('bot') else 'Utilisateur'}")
    print(COLOR + f" Compte créé le  : {created:%d/%m/%Y à %H:%M UTC} ({age_jours} jours)")
    print(COLOR + f" Badges          : {', '.join(badges) if badges else 'Aucun'}")
    print(COLOR + f" Couleur profil  : {color_txt}")
    print(COLOR + f" Avatar          : {avatar}")
    print(COLOR + f" Bannière        : {banner_url}")
    print(COLOR + "─" * 60)
    pause()


VERIF_LEVELS = {
    0: "Aucune",
    1: "Faible (email vérifié)",
    2: "Moyenne (inscrit depuis 5 min)",
    3: "Élevée (membre depuis 10 min)",
    4: "Très élevée (téléphone vérifié)",
}


def parse_invite(text):
    """Extrait le code d'un lien discord.gg/xxx, discord.com/invite/xxx ou d'un code seul."""
    m = re.search(r"(?:discord\.gg/|discord(?:app)?\.com/invite/)([A-Za-z0-9-]+)", text)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9-]{2,32}", text):
        return text
    return None


def fetch_invite(prompt="Lien d'invitation (discord.gg/...)"):
    """Demande un lien et renvoie le JSON de l'invitation, ou None en cas de souci."""
    code = parse_invite(ask_text(prompt))
    if not code:
        print(WARN + "\nLien d'invitation invalide.")
        pause()
        return None
    try:
        r = requests.get(
            f"{API}/invites/{code}",
            params={"with_counts": "true", "with_expiration": "true"},
            timeout=10,
        )
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre Discord (vérifie ta connexion).")
        pause()
        return None
    if r.status_code == 404:
        print(WARN + "\nInvitation introuvable, expirée ou supprimée.")
        pause()
        return None
    if r.status_code == 429:
        print(WARN + "\nTrop de requêtes, attends quelques secondes.")
        pause()
        return None
    if r.status_code != 200:
        print(WARN + f"\nErreur Discord ({r.status_code}).")
        pause()
        return None
    return r.json()


def info_serveur():
    data = fetch_invite()
    if not data:
        return
    g = data.get("guild")
    if not g:
        print(WARN + "\nCette invitation ne mène pas à un serveur (groupe ou DM).")
        return pause()

    gid = g["id"]
    ts = ((int(gid) >> 22) + 1420070400000) / 1000
    created = datetime.fromtimestamp(ts, tz=timezone.utc)

    icon = (f"https://cdn.discordapp.com/icons/{gid}/{g['icon']}.png?size=1024"
            if g.get("icon") else "Aucune")
    banner_url = (f"https://cdn.discordapp.com/banners/{gid}/{g['banner']}.png?size=1024"
                  if g.get("banner") else "Aucune")

    total = data.get("approximate_member_count")
    online = data.get("approximate_presence_count")
    expires = data.get("expires_at")
    if expires:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        expires_txt = f"{exp_dt:%d/%m/%Y à %H:%M UTC}"
    else:
        expires_txt = "Jamais"

    features = g.get("features", [])
    inviter = data.get("inviter") or {}
    channel = data.get("channel") or {}

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Nom              : {g.get('name')}")
    print(COLOR + f" ID               : {gid}")
    print(COLOR + f" Description      : {g.get('description') or 'Aucune'}")
    print(COLOR + f" Membres          : {total if total is not None else '?'}")
    print(COLOR + f" En ligne         : {online if online is not None else '?'}")
    print(COLOR + f" Créé le          : {created:%d/%m/%Y à %H:%M UTC}")
    print(COLOR + f" Boosts           : {g.get('premium_subscription_count', 0)}")
    print(COLOR + f" Vérification     : {VERIF_LEVELS.get(g.get('verification_level'), '?')}")
    print(COLOR + f" URL perso        : {g.get('vanity_url_code') or 'Aucune'}")
    print(COLOR + f" Salon d'invit.   : #{channel.get('name', '?')}")
    print(COLOR + f" Invité par       : {inviter.get('username') or 'Inconnu'}")
    print(COLOR + f" Expire le        : {expires_txt}")
    print(COLOR + f" Fonctions        : {', '.join(features) if features else 'Aucune'}")
    print(COLOR + f" Icône            : {icon}")
    print(COLOR + f" Bannière         : {banner_url}")
    print(COLOR + "─" * 60)
    pause()


def verifier_invitation():
    data = fetch_invite("Lien d'invitation à vérifier")
    if not data:
        return
    g = data.get("guild") or {}
    print(OK + f"\nInvitation valide : serveur « {g.get('name', '?')} »")
    expires = data.get("expires_at")
    if expires:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        print(COLOR + f"Expire le {exp_dt:%d/%m/%Y à %H:%M UTC}")
    else:
        print(COLOR + "N'expire jamais.")
    pause()


def guide():
    show_bot_guide()
    pause()


# ---------- OSINT : IP ----------
def ip_info():
    ip = ask_text("Adresse IP")
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,regionName,city,zip,isp,org,as,mobile,proxy,hosting,query"},
            timeout=10,
        )
        data = r.json()
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if data.get("status") != "success":
        print(WARN + f"\nAdresse IP invalide ou introuvable ({data.get('message', '?')}).")
        return pause()

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" IP               : {data.get('query')}")
    print(COLOR + f" Pays             : {data.get('country')}")
    print(COLOR + f" Région           : {data.get('regionName')}")
    print(COLOR + f" Ville            : {data.get('city')}")
    print(COLOR + f" Code postal      : {data.get('zip') or '?'}")
    print(COLOR + f" Fournisseur      : {data.get('isp')}")
    print(COLOR + f" Organisation     : {data.get('org') or '?'}")
    print(COLOR + f" AS               : {data.get('as') or '?'}")
    print(COLOR + f" Mobile           : {'Oui' if data.get('mobile') else 'Non'}")
    print(COLOR + f" VPN / Proxy      : {'Oui' if data.get('proxy') else 'Non'}")
    print(COLOR + f" Datacenter       : {'Oui' if data.get('hosting') else 'Non'}")
    print(COLOR + "─" * 60)
    pause()


# ---------- RÉSEAU : WHOIS complet d'une IP ----------
def ip_whois():
    ip = ask_text("Adresse IP")
    if not ip:
        return
    try:
        r = requests.get(f"https://rdap.org/ip/{ip}", timeout=10)
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if r.status_code != 200:
        print(WARN + f"\nAdresse IP introuvable ou invalide ({r.status_code}).")
        return pause()

    data = r.json()

    # Nom et pays du bloc d'adresses
    nom_bloc = data.get("name", "?")
    pays = data.get("country", "?")
    cidr = f"{data.get('startAddress', '?')} - {data.get('endAddress', '?')}"
    type_bloc = data.get("type", "?")

    # Organisation / contact (entités liées au bloc)
    organisation = "?"
    for entite in data.get("entities", []):
        vcard = entite.get("vcardArray")
        if vcard and len(vcard) > 1:
            for champ in vcard[1]:
                if champ[0] == "fn":
                    organisation = champ[3]
                    break
        if organisation != "?":
            break

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" IP               : {ip}")
    print(COLOR + f" Nom du bloc      : {nom_bloc}")
    print(COLOR + f" Organisation     : {organisation}")
    print(COLOR + f" Pays             : {pays}")
    print(COLOR + f" Plage d'adresses : {cidr}")
    print(COLOR + f" Type             : {type_bloc}")
    print(COLOR + "─" * 60)
    pause()


# ---------- RÉSEAU : Carte de localisation IP ----------
def ip_map():
    ip = ask_text("Adresse IP")
    if not ip:
        return
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,country,regionName,city,lat,lon,isp,query"},
            timeout=10,
        )
        data = r.json()
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if data.get("status") != "success":
        print(WARN + f"\nAdresse IP invalide ou introuvable ({data.get('message', '?')}).")
        return pause()

    lat, lon = data.get("lat"), data.get("lon")
    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" IP               : {data.get('query')}")
    print(COLOR + f" Localisation     : {data.get('city')}, {data.get('regionName')}, {data.get('country')}")
    print(COLOR + f" Fournisseur      : {data.get('isp')}")
    print(COLOR + f" Coordonnées      : {lat}, {lon}")
    print(OK + f" Google Maps      : https://maps.google.com/?q={lat},{lon}")
    print(COLOR + "─" * 60)
    print(WARN + " Note : position approximative (ville du fournisseur internet, pas l'adresse exacte).")
    pause()


# ---------- RÉSEAU : IP Pinger ----------
def ip_pinger():
    cible = ask_text("IP ou domaine à pinger")
    if not cible:
        return

    cmd = ["ping", "-n", "4", cible] if os.name == "nt" else ["ping", "-c", "4", cible]
    print(COLOR + f"\nPing de {cible}...\n")
    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        sortie = result.stdout or result.stderr
        print(Fore.WHITE + sortie.strip())
    except Exception as e:
        print(WARN + f"\nÉchec du ping ({e}).")
    pause()


# ---------- RÉSEAU : DNS Lookup complet ----------
def dns_lookup():
    domaine = ask_text("Nom de domaine (ex: exemple.com)")
    if not domaine:
        return
    domaine = re.sub(r"^https?://", "", domaine).split("/")[0]

    types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]
    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Domaine          : {domaine}")
    print(COLOR + "─" * 60)

    trouve_qqchose = False
    for t in types:
        try:
            reponses = dns.resolver.resolve(domaine, t)
            valeurs = [str(r).strip() for r in reponses]
            trouve_qqchose = True
            print(COLOR + f" {t:<6}" + Fore.WHITE + f" : {valeurs[0]}")
            for v in valeurs[1:]:
                print(COLOR + " " * 9 + Fore.WHITE + f": {v}")
        except dns.resolver.NoAnswer:
            pass
        except dns.resolver.NXDOMAIN:
            print(WARN + "\nCe domaine n'existe pas.")
            return pause()
        except Exception:
            pass

    if not trouve_qqchose:
        print(WARN + " Aucun enregistrement DNS trouvé.")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Email ----------
def email_info():
    email = ask_text("Adresse email")
    m = re.fullmatch(r"[^@\s]+@([^@\s]+\.[^@\s]+)", email)
    if not m:
        print(WARN + "\nFormat d'email invalide.")
        return pause()
    domain = m.group(1)

    try:
        mx = dns.resolver.resolve(domain, "MX")
        mx_hosts = sorted(str(r.exchange).rstrip(".") for r in mx)
        has_mx = True
    except Exception:
        mx_hosts = []
        has_mx = False

    connu = {
        "gmail.com": "Google (Gmail)",
        "outlook.com": "Microsoft (Outlook)",
        "hotmail.com": "Microsoft (Hotmail)",
        "yahoo.com": "Yahoo",
        "icloud.com": "Apple (iCloud)",
        "proton.me": "Proton Mail",
        "protonmail.com": "Proton Mail",
    }
    fournisseur = connu.get(domain.lower(), "Inconnu / domaine personnalisé")

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Email            : {email}")
    print(COLOR + f" Domaine          : {domain}")
    print(COLOR + f" Fournisseur      : {fournisseur}")
    print(COLOR + f" Domaine valide   : {'Oui (reçoit des mails)' if has_mx else 'Non / injoignable'}")
    if mx_hosts:
        print(COLOR + f" Serveurs mail    : {', '.join(mx_hosts[:3])}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Email breach count (par domaine) ----------
def email_breach_count():
    email = ask_text("Adresse email")
    m = re.fullmatch(r"[^@\s]+@([^@\s]+\.[^@\s]+)", email)
    if not m:
        print(WARN + "\nFormat d'email invalide.")
        return pause()
    domaine = m.group(1)

    try:
        r = requests.get(
            "https://haveibeenpwned.com/api/v3/breaches",
            params={"domain": domaine},
            headers={"User-Agent": "CyberSleep-OSINT-Tool"},
            timeout=10,
        )
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if r.status_code != 200:
        print(WARN + f"\nErreur du service ({r.status_code}).")
        return pause()

    breaches = r.json()
    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Email            : {email}")
    print(COLOR + f" Domaine          : {domaine}")
    print(COLOR + f" Fuites connues   : {len(breaches)}")
    if breaches:
        for b in breaches[:8]:
            date = b.get("BreachDate", "?")
            print(COLOR + f"   - {b.get('Name', '?')} ({date})")
    else:
        print(OK + " Aucune fuite publique connue liée à ce domaine.")
    print(COLOR + "─" * 60)
    print(WARN + " Note : fuites connues du DOMAINE de l'email, pas de cette adresse précise.")
    pause()


# ---------- OSINT : Archive.org Checker ----------
def archive_checker():
    url = ask_text("URL ou domaine (ex: exemple.com)")
    if not url:
        return
    if not re.match(r"^https?://", url):
        url = "https://" + url

    print(COLOR + "\nRecherche en cours...")

    # Snapshot le plus proche d'aujourd'hui
    try:
        r1 = requests.get(
            "https://archive.org/wayback/available",
            params={"url": url},
            timeout=10,
        )
        snap = r1.json().get("archived_snapshots", {}).get("closest")
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre archive.org (vérifie ta connexion).")
        return pause()

    # Première capture connue (via CDX API)
    premiere = None
    try:
        r2 = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={"url": url, "output": "json", "fl": "timestamp", "limit": 1, "collapse": "urlkey"},
            timeout=10,
        )
        data2 = r2.json()
        if len(data2) > 1:
            premiere = data2[1][0]
    except requests.RequestException:
        pass

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" URL              : {url}")
    if snap and snap.get("available"):
        d = snap.get("timestamp", "")
        date_fmt = f"{d[6:8]}/{d[4:6]}/{d[:4]}" if len(d) >= 8 else d
        print(OK + f" Dernière archive : {date_fmt}")
        print(OK + f" Lien             : {snap.get('url')}")
    else:
        print(WARN + " Aucune archive trouvée pour cette page.")

    if premiere:
        date_fmt = f"{premiere[6:8]}/{premiere[4:6]}/{premiere[:4]}" if len(premiere) >= 8 else premiere
        print(COLOR + f" Première capture : {date_fmt}")
        print(COLOR + f" Existe depuis    : https://web.archive.org/web/{premiere}/{url}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Steam Profile Info ----------
def steam_info():
    import xml.etree.ElementTree as ET

    entree = ask_text("Lien du profil Steam ou pseudo (vanity URL)")
    if not entree:
        return

    # Extraire le pseudo ou l'ID à partir d'un lien complet
    m = re.search(r"steamcommunity\.com/(id|profiles)/([^/\s]+)", entree)
    if m:
        type_url, identifiant = m.group(1), m.group(2)
    else:
        type_url, identifiant = "id", entree.strip()

    url = f"https://steamcommunity.com/{type_url}/{identifiant}?xml=1"
    try:
        r = requests.get(url, timeout=10)
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre Steam (vérifie ta connexion).")
        return pause()

    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        print(WARN + "\nProfil introuvable.")
        return pause()

    if root.tag == "response" and root.findtext("error"):
        print(WARN + f"\n{root.findtext('error')}")
        return pause()

    def champ(tag, defaut="?"):
        v = root.findtext(tag)
        return v if v else defaut

    etat = champ("onlineState")
    message_etat = champ("stateMessage")
    visibilite = champ("visibilityState")
    prive = visibilite != "3"

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Pseudo           : {champ('steamID')}")
    print(COLOR + f" SteamID64        : {champ('steamID64')}")
    print(COLOR + f" Statut           : {etat} ({re.sub('<.*?>', '', message_etat)})")
    print(COLOR + f" Profil           : {'Privé' if prive else 'Public'}")
    if not prive:
        print(COLOR + f" Membre depuis    : {champ('memberSince')}")
        print(COLOR + f" Niveau Steam     : {champ('steamRating', 'Non visible')}")
        print(COLOR + f" Avatar           : {champ('avatarFull')}")
        loc = champ("location", "")
        if loc:
            print(COLOR + f" Localisation     : {loc}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Téléphone ----------
def phone_info():
    numero = ask_text("Numéro (format international, ex: +33612345678)")
    try:
        parsed = phonenumbers.parse(numero, None)
    except phonenumbers.NumberParseException:
        print(WARN + "\nNuméro invalide. Utilise le format international (+33...).")
        return pause()

    if not phonenumbers.is_valid_number(parsed):
        print(WARN + "\nCe numéro n'est pas valide.")
        return pause()

    pays = geocoder.description_for_number(parsed, "fr") or "Inconnu"
    operateur = pn_carrier.name_for_number(parsed, "fr") or "Inconnu"
    type_num = phonenumbers.number_type(parsed)
    types = {
        0: "Fixe", 1: "Mobile", 2: "Fixe ou mobile",
        3: "Numéro surtaxé", 4: "Numéro gratuit", 5: "Partagé",
        6: "VoIP", 27: "Personnel", 7: "Pager",
    }

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Numéro           : {phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}")
    print(COLOR + f" Pays             : {pays}")
    print(COLOR + f" Opérateur        : {operateur}")
    print(COLOR + f" Type de ligne    : {types.get(type_num, 'Inconnu')}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Domaine ----------
def domain_info():
    domaine = ask_text("Nom de domaine (ex: exemple.com)")
    domaine = re.sub(r"^https?://", "", domaine).split("/")[0]

    try:
        ip = __import__("socket").gethostbyname(domaine)
    except Exception:
        ip = "Introuvable"

    try:
        w = whois_lib.whois(domaine)
        registrar = w.registrar or "Inconnu"
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        expires = w.expiration_date
        if isinstance(expires, list):
            expires = expires[0]
        ns = w.name_servers or []
        if isinstance(ns, str):
            ns = [ns]
    except Exception:
        registrar, created, expires, ns = "Indisponible", None, None, []

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Domaine          : {domaine}")
    print(COLOR + f" IP               : {ip}")
    print(COLOR + f" Registrar        : {registrar}")
    print(COLOR + f" Créé le          : {created or '?'}")
    print(COLOR + f" Expire le        : {expires or '?'}")
    print(COLOR + f" Serveurs DNS     : {', '.join(ns[:3]) if ns else '?'}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : QR Code ----------
def qr_code():
    texte = ask_text("Texte ou lien à encoder")
    if not texte:
        return

    qr = qrcode.QRCode(border=2)
    qr.add_data(texte)
    qr.make(fit=True)

    print(COLOR)
    qr.print_ascii(invert=True)

    out_path = os.path.join(BASE_DIR, "qrcode.png")
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
    print(OK + f"\nQR code enregistré : {out_path}")
    pause()


# ---------- OUTILS : Raccourcisseur de lien ----------
def raccourcir_lien():
    lien = ask_text("Lien à raccourcir")
    if not re.match(r"^https?://", lien):
        lien = "https://" + lien
    try:
        r = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": lien},
            timeout=10,
        )
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if r.status_code == 200 and r.text.startswith("http"):
        print(OK + f"\nLien raccourci : {r.text.strip()}")
    else:
        print(WARN + f"\nErreur : {r.text.strip()}")
    pause()


# ---------- OUTILS : Username checker ----------
USERNAME_SITES = {
    "GitHub": "https://github.com/{u}",
    "Twitter / X": "https://x.com/{u}",
    "Instagram": "https://www.instagram.com/{u}/",
    "TikTok": "https://www.tiktok.com/@{u}",
    "Reddit": "https://www.reddit.com/user/{u}/",
    "Twitch": "https://www.twitch.tv/{u}",
    "Steam": "https://steamcommunity.com/id/{u}",
    "YouTube": "https://www.youtube.com/@{u}",
    "Pinterest": "https://www.pinterest.com/{u}/",
}


def username_checker():
    pseudo = ask_text("Pseudo à vérifier")
    if not pseudo:
        return

    headers = {"User-Agent": "Mozilla/5.0 (CyberSleep OSINT Tool)"}
    print(COLOR + "\n" + "─" * 60)
    for site, template in USERNAME_SITES.items():
        url = template.format(u=pseudo)
        try:
            r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            pris = r.status_code == 200
        except requests.RequestException:
            print(WARN + f" {site:<14} : impossible de vérifier")
            continue

        if pris:
            print(OK + f" {site:<14} : pris      -> {url}")
        else:
            print(COLOR + f" {site:<14} : disponible")
    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Scan de ports ----------
PORTS_COURANTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
    3306: "MySQL", 3389: "RDP", 8080: "HTTP alt",
}


def scan_ports():
    cible = ask_text("Adresse ou domaine (uniquement sur tes propres machines !)")
    try:
        ip = socket.gethostbyname(cible)
    except socket.gaierror:
        print(WARN + "\nAdresse introuvable.")
        return pause()

    print(COLOR + f"\nScan de {cible} ({ip})...\n")
    ouverts = []
    for port, nom in PORTS_COURANTS.items():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6)
        result = s.connect_ex((ip, port))
        s.close()
        if result == 0:
            ouverts.append((port, nom))
            print(OK + f" [OUVERT]  {port:<6} {nom}")
        else:
            print(COLOR + f" [fermé]   {port:<6} {nom}")

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Ports ouverts : {len(ouverts)} / {len(PORTS_COURANTS)}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OSINT : Métadonnées EXIF ----------
def metadata_exif():
    chemin = ask_text("Chemin de l'image (ex: C:\\Users\\toi\\Desktop\\photo.jpg)")
    chemin = chemin.strip('"')
    if not chemin:
        return
    if not os.path.isfile(chemin):
        print(WARN + "\nFichier introuvable. Vérifie le chemin.")
        return pause()

    try:
        img = Image.open(chemin)
    except Exception as e:
        print(WARN + f"\nImpossible d'ouvrir l'image ({e}).")
        return pause()

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Fichier          : {os.path.basename(chemin)}")
    print(COLOR + f" Format           : {img.format}")
    print(COLOR + f" Dimensions       : {img.width} x {img.height} px")

    exif_data = img.getexif()
    if not exif_data:
        print(WARN + " Aucune métadonnée EXIF trouvée dans cette image.")
        print(COLOR + "─" * 60)
        return pause()

    champs_utiles = {
        "Make": "Marque de l'appareil",
        "Model": "Modèle de l'appareil",
        "DateTime": "Date de la photo",
        "Software": "Logiciel utilisé",
        "Orientation": "Orientation",
    }
    trouve = False
    for tag_id, valeur in exif_data.items():
        nom = ExifTags.TAGS.get(tag_id, str(tag_id))
        if nom in champs_utiles:
            print(COLOR + f" {champs_utiles[nom]:<16} : {valeur}")
            trouve = True

    # Coordonnées GPS si présentes
    gps_info = exif_data.get_ifd(0x8825) if hasattr(exif_data, "get_ifd") else {}
    if gps_info:
        try:
            def to_deg(valeurs, ref):
                d, m, s = valeurs
                deg = d + m / 60 + s / 3600
                return -deg if ref in ("S", "W") else deg

            lat = to_deg(gps_info[2], gps_info[1])
            lon = to_deg(gps_info[4], gps_info[3])
            print(OK + f" GPS              : {lat:.6f}, {lon:.6f}")
            print(OK + f" Google Maps      : https://maps.google.com/?q={lat},{lon}")
            trouve = True
        except Exception:
            pass

    if not trouve:
        print(WARN + " Aucune métadonnée exploitable trouvée (photo probablement nettoyée).")

    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Mon IP publique ----------
def mon_ip():
    try:
        r = requests.get("http://ip-api.com/json/", timeout=10)
        data = r.json()
    except requests.RequestException:
        print(WARN + "\nImpossible de joindre le service (vérifie ta connexion).")
        return pause()

    if data.get("status") != "success":
        print(WARN + "\nImpossible de récupérer ton IP.")
        return pause()

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" IP publique      : {data.get('query')}")
    print(COLOR + f" Pays             : {data.get('country')}")
    print(COLOR + f" Région           : {data.get('regionName')}")
    print(COLOR + f" Ville            : {data.get('city')}")
    print(COLOR + f" Fournisseur      : {data.get('isp')}")
    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Speedtest ----------
def speed_test():
    print(COLOR + "\nRecherche du meilleur serveur...")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        print(COLOR + "Test du download...")
        down = st.download() / 1_000_000       # bits -> Mbps
        print(COLOR + "Test de l'upload...")
        up = st.upload() / 1_000_000
        ping = st.results.ping
    except Exception as e:
        print(WARN + f"\nÉchec du test ({e}).")
        return pause()

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Ping             : {ping:.0f} ms")
    print(COLOR + f" Download         : {down:.1f} Mbps")
    print(COLOR + f" Upload           : {up:.1f} Mbps")
    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Générateur de mot de passe ----------
def generer_mdp():
    longueur_txt = ask_text("Longueur (défaut : 16)")
    longueur = int(longueur_txt) if longueur_txt.isdigit() else 16
    longueur = max(4, min(longueur, 128))

    symboles = ask_text("Inclure des symboles ? (o/n, défaut : o)").lower()
    alphabet = string_mod.ascii_letters + string_mod.digits
    if symboles != "n":
        alphabet += "!@#$%^&*()-_=+?"

    mdp = "".join(secrets.choice(alphabet) for _ in range(longueur))

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Mot de passe     : {mdp}")
    print(COLOR + f" Longueur         : {longueur} caractères")
    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Texte stylé ----------
FANCY_STYLES = {
    "Gothique (𝕱𝖗𝖆𝖐𝖙𝖚𝖗)": {
        **{c: chr(0x1D56C + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D586 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
    },
    "Bulles (Ⓒⓘⓡⓒⓛⓔ)": {
        **{c: chr(0x24D0 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
        **{c: chr(0x24B6 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{str(d): (chr(0x2460 + d - 1) if d != 0 else "⓪") for d in range(10)},
    },
    "Gras (𝐁𝐨𝐥𝐝)": {
        **{c: chr(0x1D400 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D41A + i) for i, c in enumerate(string_mod.ascii_lowercase)},
        **{str(d): chr(0x1D7CE + d) for d in range(10)},
    },
    "Script (𝓼𝓬𝓻𝓲𝓹𝓽)": {
        **{c: chr(0x1D4D0 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D4EA + i) for i, c in enumerate(string_mod.ascii_lowercase)},
    },
    "Carré (🅂🅀🅄🄰🅁🄴)": {
        **{c: chr(0x1F130 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1F130 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
    },
    "Monospace (𝚖𝚘𝚗𝚘)": {
        **{c: chr(0x1D670 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D68A + i) for i, c in enumerate(string_mod.ascii_lowercase)},
        **{str(d): chr(0x1D7F6 + d) for d in range(10)},
    },
    "Sans Gras (𝗦𝗮𝗻𝘀 𝗯𝗼𝗹𝗱)": {
        **{c: chr(0x1D5D4 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D5EE + i) for i, c in enumerate(string_mod.ascii_lowercase)},
        **{str(d): chr(0x1D7EC + d) for d in range(10)},
    },
    "Sans Italique (𝘚𝘢𝘯𝘴 𝘪𝘵𝘢𝘭𝘪𝘤)": {
        **{c: chr(0x1D608 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1D622 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
    },
    "Vaporwave (Ｆｕｌｌｗｉｄｔｈ)": {
        **{c: chr(0xFF21 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0xFF41 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
        **{str(d): chr(0xFF10 + d) for d in range(10)},
        " ": "　",
    },
    "Bulles pleines (🅑🅤🅑🅑🅛🅔)": {
        **{c: chr(0x1F150 + i) for i, c in enumerate(string_mod.ascii_uppercase)},
        **{c: chr(0x1F150 + i) for i, c in enumerate(string_mod.ascii_lowercase)},
    },
}

# Style spécial : texte inversé (tête en bas), table + inversion de l'ordre
UPSIDE_DOWN = {
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ", "g": "ƃ",
    "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "ʅ", "m": "ɯ", "n": "u",
    "o": "o", "p": "d", "q": "b", "r": "ɹ", "s": "s", "t": "ʇ", "u": "n",
    "v": "ʌ", "w": "ʍ", "x": "x", "y": "ʎ", "z": "z",
    "A": "∀", "B": "𐐒", "C": "Ɔ", "D": "ᗡ", "E": "Ǝ", "F": "Ⅎ", "G": "⅁",
    "H": "H", "I": "I", "J": "ſ", "K": "ʞ", "L": "˥", "M": "W", "N": "N",
    "O": "O", "P": "Ԁ", "Q": "Ό", "R": "ᴚ", "S": "S", "T": "┴", "U": "∩",
    "V": "Λ", "W": "M", "X": "X", "Y": "⅄", "Z": "Z",
    "0": "0", "1": "Ɩ", "2": "ᄅ", "3": "Ɛ", "4": "ㄣ", "5": "ϛ", "6": "9",
    "7": "ㄥ", "8": "8", "9": "6", ".": "˙", ",": "'", "'": ",",
    "?": "¿", "!": "¡", "(": ")", ")": "(",
}


def texte_stylé():
    texte = ask_text("Texte à transformer")
    if not texte:
        return

    print(COLOR + "\n" + "─" * 60)
    for nom, table in FANCY_STYLES.items():
        resultat = "".join(table.get(c, c) for c in texte)
        print(COLOR + f" {nom}")
        print(Fore.WHITE + f"  {resultat}\n")

    inverse = "".join(UPSIDE_DOWN.get(c, c) for c in texte)[::-1]
    print(COLOR + " Inversé (ʇxǝʇ ǝpᴉsdn)")
    print(Fore.WHITE + f"  {inverse}\n")

    print(COLOR + "─" * 60)
    pause()


# ---------- OUTILS : Force du mot de passe ----------
def force_mdp():
    import math
    mdp = ask_text("Mot de passe à tester")
    if not mdp:
        return

    longueur = len(mdp)
    a_min = any(c.islower() for c in mdp)
    a_maj = any(c.isupper() for c in mdp)
    a_chiffre = any(c.isdigit() for c in mdp)
    a_symbole = any(not c.isalnum() for c in mdp)

    taille_alphabet = 0
    taille_alphabet += 26 if a_min else 0
    taille_alphabet += 26 if a_maj else 0
    taille_alphabet += 10 if a_chiffre else 0
    taille_alphabet += 33 if a_symbole else 0
    taille_alphabet = max(taille_alphabet, 1)

    entropie = longueur * math.log2(taille_alphabet)

    courants = ["123456", "password", "azerty", "motdepasse", "qwerty", "admin", "azertyuiop"]
    est_courant = mdp.lower() in courants

    if est_courant:
        niveau, couleur = "TRÈS FAIBLE (mot de passe courant)", WARN
    elif entropie < 28:
        niveau, couleur = "FAIBLE", WARN
    elif entropie < 45:
        niveau, couleur = "MOYEN", Fore.LIGHTYELLOW_EX + Style.BRIGHT
    elif entropie < 65:
        niveau, couleur = "FORT", OK
    else:
        niveau, couleur = "TRÈS FORT", OK

    conseils = []
    if longueur < 12:
        conseils.append("Utilise au moins 12 caractères.")
    if not a_maj:
        conseils.append("Ajoute des majuscules.")
    if not a_chiffre:
        conseils.append("Ajoute des chiffres.")
    if not a_symbole:
        conseils.append("Ajoute des symboles (!@#...).")

    print(COLOR + "\n" + "─" * 60)
    print(COLOR + f" Longueur         : {longueur} caractères")
    print(COLOR + f" Entropie estimée : {entropie:.0f} bits")
    print(couleur + f" Niveau           : {niveau}")
    print(COLOR + "─" * 60)
    if conseils:
        print(COLOR + " Conseils :")
        for c in conseils:
            print(COLOR + f"  - {c}")
    pause()


# ---------- AUTRES : Générateur de nom aléatoire ----------
ADJECTIFS = [
    "Dark", "Shadow", "Silent", "Crimson", "Frozen", "Hidden", "Ghost",
    "Phantom", "Neon", "Toxic", "Savage", "Rogue", "Cyber", "Nova",
    "Lunar", "Solar", "Mystic", "Void", "Crypto", "Iron",
]
NOMS = [
    "Wolf", "Raven", "Viper", "Falcon", "Reaper", "Phoenix", "Dragon",
    "Tiger", "Fox", "Panther", "Storm", "Blade", "Hunter", "Ghost",
    "Knight", "Spirit", "Titan", "Shark", "Cobra", "Eagle",
]


def generateur_nom():
    print(COLOR + "\n" + "─" * 60)
    for _ in range(10):
        adj = secrets.choice(ADJECTIFS)
        nom = secrets.choice(NOMS)
        suffixe = secrets.randbelow(999)
        print(COLOR + f" {adj}{nom}{suffixe}")
    print(COLOR + "─" * 60)
    pause()


# ---------- Paramètres (écran dédié) ----------
def ecran_parametres():
    while True:
        banner("PARAMETRES")
        son = "activé" if sound_enabled() else "désactivé"
        print(COLOR + f" [1] Changer / entrer mon token")
        print(COLOR + f" [2] Supprimer mon token")
        print(COLOR + f" [3] Comment créer un bot ?")
        print(COLOR + f" [4] Son : {son} (cliquer pour changer)")
        print(COLOR + f" [0] Retour\n")
        choix = input(COLOR + "[+] Choix : ").strip()
        if choix == "0":
            return
        elif choix == "1":
            setup_token()
        elif choix == "2":
            delete_token()
        elif choix == "3":
            guide()
        elif choix == "4":
            toggle_sound()
        else:
            print(WARN + "Choix invalide.")
            pause()


# ---------- Dashboard 3 colonnes ----------
# Numérotation continue à travers les 3 colonnes, comme sur un vrai dashboard CLI.
COL_RESEAU = [
    ("01", "Mon IP publique", mon_ip),
    ("02", "IP Scanner (infos / VPN)", ip_info),
    ("03", "IP Pinger", ip_pinger),
    ("04", "Port Scanner", scan_ports),
    ("05", "Website Info Scanner", domain_info),
    ("06", "Speedtest", speed_test),
    ("07", "WHOIS complet (IP)", ip_whois),
    ("08", "Carte de localisation IP", ip_map),
    ("09", "Coming Soon...", None),
]

COL_OSINT = [
    ("10", "Username Tracker", username_checker),
    ("11", "Email Info", email_info),
    ("12", "Phone Info", phone_info),
    ("13", "Discord User Info", info_utilisateur),
    ("14", "Discord Server Info", info_serveur),
    ("15", "Discord Invite Check", verifier_invitation),
    ("16", "Metadata EXIF (image)", metadata_exif),
    ("17", "Email Breach Count", email_breach_count),
    ("18", "Archive.org Checker", archive_checker),
]

COL_AUTRES = [
    ("19", "Password Generator", generer_mdp),
    ("20", "Password Strength", force_mdp),
    ("21", "QR Code Generator", qr_code),
    ("22", "Link Shortener", raccourcir_lien),
    ("23", "Fancy Text Generator", texte_stylé),
    ("24", "Name Generator", generateur_nom),
    ("25", "Steam Profile Info", steam_info),
    ("26", "Coming Soon...", None),
    ("27", "Coming Soon...", None),
]

ACTIONS = {num: fn for col in (COL_RESEAU, COL_OSINT, COL_AUTRES) for num, _, fn in col if fn}

COL_WIDTH = 33

RESET = Style.RESET_ALL


def _ligne(item, couleur, dernier):
    num, label, fn = item
    branche = "└─" if dernier else "├─"
    if fn is None:
        texte = f" {couleur}{branche} [{num}]{RESET} {Fore.LIGHTBLACK_EX}{label}{RESET}"
        brut = f" {branche} [{num}] {label}"
    else:
        texte = f" {couleur}{branche} [{num}]{RESET} {Fore.WHITE}{label}{RESET}"
        brut = f" {branche} [{num}] {label}"
    pad = " " * max(0, COL_WIDTH - len(brut))
    return texte + pad


PAGE_SIZE = 5
NB_PAGES = -(-max(len(COL_RESEAU), len(COL_OSINT), len(COL_AUTRES)) // PAGE_SIZE)  # arrondi au-dessus


def dashboard(page):
    banner("CYBER   SLEEP")

    w = COL_WIDTH
    haut = "╭" + "─" * w + "┬" + "─" * w + "┬" + "─" * w + "╮"
    milieu = "├" + "─" * w + "┼" + "─" * w + "┼" + "─" * w + "┤"
    bas = "╰" + "─" * w + "┴" + "─" * w + "┴" + "─" * w + "╯"

    titres = (
        f"{COLOR}{'RÉSEAU'.center(w)}{RESET}│"
        f"{COLOR}{'OSINT'.center(w)}{RESET}│"
        f"{COLOR}{'AUTRES'.center(w)}{RESET}"
    )

    print(COLOR + haut)
    print(COLOR + "│" + titres + COLOR + "│")
    print(COLOR + milieu)

    debut = page * PAGE_SIZE
    fin = debut + PAGE_SIZE
    r_page = COL_RESEAU[debut:fin]
    o_page = COL_OSINT[debut:fin]
    a_page = COL_AUTRES[debut:fin]

    for i in range(PAGE_SIZE):
        r = _ligne(r_page[i], COLOR, i == len(r_page) - 1) if i < len(r_page) else " " * w
        o = _ligne(o_page[i], COLOR, i == len(o_page) - 1) if i < len(o_page) else " " * w
        a = _ligne(a_page[i], COLOR, i == len(a_page) - 1) if i < len(a_page) else " " * w
        print(COLOR + f"│{r}{COLOR}│{o}{COLOR}│{a}{COLOR}│")

    print(COLOR + bas)
    bar = f" Page {page + 1}/{NB_PAGES}   |   [N] Next   |   [B] Back   |   [P] Paramètres   |   [E] Exit "
    print(COLOR + bar.center(w * 3 + 4, "─") + "\n")


def main_loop():
    page = 0
    while True:
        dashboard(page)
        print(COLOR + "┌─(cybersleep@main)")
        choix = input(COLOR + "└─$ ").strip().lower()

        cle = choix.zfill(2) if choix.isdigit() else choix

        if choix == "e":
            sys.exit()
        elif choix == "p":
            ecran_parametres()
        elif choix == "n":
            page = (page + 1) % NB_PAGES
        elif choix == "b":
            page = (page - 1) % NB_PAGES
        elif cle in ACTIONS:
            ACTIONS[cle]()
        else:
            print(WARN + "Choix invalide.")
            pause()


if __name__ == "__main__":
    if os.name == "nt":
        os.system("title CYBER SLEEP")
        os.system("mode con: cols=120 lines=42")
    boot_sequence()
    main_loop()
