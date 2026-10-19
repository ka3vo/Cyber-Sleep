# Cyber-sommeil

Outil CLI tout-en-un : Discord, OSINT et réseau, dans un dashboard en terminal.

![status](https://img.shields.io/badge/status-en%20développement-red)

## Fonctionnalités

**Réseau**
- Mon IP publique, IP Scanner (VPN/proxy), IP Pinger, Port Scanner
- Website Info Scanner, Speedtest, WHOIS complet (IP), Carte de localisation IP

**OSINT**
- Username Tracker (multi-plateformes), Email Info, Phone Info
- Discord User/Server Info, Discord Invite Check
- Metadata EXIF (images), Email Breach Count, Archive.org Checker
- Steam Profile Info

**Autres**
- Password Generator / Strength Checker
- QR Code Generator, Link Shortener, Fancy Text Generator, Name Generator

## Installation (Python)

Il te faut [Python 3.10+](https://www.python.org/downloads/) installé (coche "Add Python to PATH" pendant l'installation sous Windows).

```bash
git clone https://github.com/ka3vo/Cyber-Sleep.git
cd Cyber-sommeil
pip install -r requirements.txt
```

## Lancement

```bash
python tool_menu_v2.py
```

Au premier lancement, un guide t'explique comment créer un bot Discord gratuit pour obtenir un token (nécessaire pour les fonctions Discord User/Server Info). Chaque utilisateur garde son propre token en local, dans `token.txt` — **ce fichier n'est jamais partagé ni envoyé nulle part**, et il est déjà exclu du dépôt via `.gitignore`.

## Version .exe (Windows, sans Python)

Une version compilée est disponible dans l'onglet [Releases](https://github.com/ka3vo/Cyber-Sleep/releases) du repo — télécharge juste le `.exe`, pas besoin d'installer Python ni aucun module.

Pour la compiler toi-même :
```bash
pip install pyinstaller
pyinstaller --onefile --name CyberSleep --collect-data pyfiglet tool_menu_v2.py
```
L'exécutable est généré dans le dossier `dist/`.

## ⚠️ Important

- Ne commit jamais `token.txt` ou `settings.txt` (déjà exclus via `.gitignore`).
- Le Port Scanner est à utiliser uniquement sur tes propres machines/serveurs.
- Cet outil est fourni à but éducatif et pour un usage légitime (vérification de comptes, sécurité réseau personnelle, recherche d'informations publiques).
