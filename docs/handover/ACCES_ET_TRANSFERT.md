# Accès, identifiants et transfert de propriété

Ce document liste **ce qui existe**, pas les valeurs réelles (mots de passe, clés API). Les
identifiants eux-mêmes doivent être partagés uniquement via un gestionnaire de mots de passe
partagé (Bitwarden, 1Password, ...) — jamais par email, chat ou dans ce dépôt.

## 1. L'application

- URL en production : **https://rh.climatisationmaroc.com**
- Code source : dépôt GitHub `teamarihafroid-boop/ariha_rh` (branche `master`)
- CI (tests automatiques) : GitHub Actions, se déclenche à chaque `push`

Si `teamarihafroid-boop` n'est pas déjà l'organisation GitHub du client, transférer le dépôt vers
son compte/organisation (Settings → Transfer ownership côté GitHub) ou, a minima, ajouter les
personnes concernées comme collaborateurs avec un rôle adapté (Admin pour un futur développeur,
Read pour simple consultation).

## 2. Comptes et services à transférer / partager

À déplacer dans le gestionnaire de mots de passe partagé du client :

| Service | Ce qu'il contient | Action |
| --- | --- | --- |
| Railway (hébergement) | App + base PostgreSQL + Redis | Ajouter le client comme membre du projet `alluring-nourishment`, ou transférer la propriété du projet |
| Cloudflare (R2 + DNS si géré là) | Stockage des documents collaborateurs | Ajouter le client comme membre du compte Cloudflare |
| OVH | Nom de domaine `climatisationmaroc.com` et zone DNS | Déjà au nom du client normalement — vérifier qui a les accès de connexion |
| GitHub | Code source | Voir section 1 |
| Compte Gemini (clé API IA) | Fonctionnalités IA de l'app | Transférer ou faire générer une nouvelle clé au nom du client |

## 3. Identifiants applicatifs déjà en place

Ces comptes existent déjà **dans l'application elle-même** (pas des accès techniques) :

- `rh@arihafroid.ma` — compte RH (accès complet)
- `dg@arihafroid.ma` — compte DG (vue d'ensemble)
- `employe@arihafroid.ma` — compte employé de démonstration

Recommandé avant remise au client : changer le mot de passe de ces comptes (menu Comptes
utilisateurs → Mot de passe) et transmettre les nouveaux mots de passe par le gestionnaire de
mots de passe, pas par ce dépôt.

## 4. Sauvegardes

Un script de sauvegarde de la base de données existe (`backend/app/scripts/backup_db.py`),
il dépose une sauvegarde compressée sur le stockage R2 (`backups/postgres/...`). Il n'est pas
encore branché sur une tâche planifiée automatique — à faire si une sauvegarde régulière
automatisée est souhaitée (ex. tâche cron sur Railway, ou déclenchement manuel périodique).
