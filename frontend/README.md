# RFM studio

Interface React de la plateforme : tableau de bord, fiches des segments,
exploration des clients, diagnostics de clustering et assistant marketing.
Les indicateurs proviennent de FastAPI. Aucune donnée de démonstration n'est
substituée à une API indisponible.

## Démarrer après un clone

1. Installer Node.js 22.12 ou supérieur et npm.
2. Suivre le [guide n8n](../n8n/README.md) pour démarrer FastAPI, PostgreSQL et
   n8n, importer le workflow, sélectionner ses trois credentials et le publier.
   L'interface d'analyse fonctionne aussi avec [FastAPI seul](../api/README.md).
3. Depuis la racine du dépôt :

   ```bash
   cd frontend
   npm ci
   cp .env.example .env
   ```

4. Renseigner `.env` :

   | Variable | Valeur / rôle |
   | --- | --- |
   | `RFM_API_URL` | `http://127.0.0.1:8000`, adresse de FastAPI depuis le serveur Node |
   | `N8N_WEBHOOK_URL` | `http://127.0.0.1:5678/webhook/rfm-chat`, URL publiée |
   | `N8N_WEBHOOK_TOKEN` | Valeur du credential Header Auth `X-RFM-Token` de n8n |
   | `SESSION_SECRET` | Secret aléatoire stable, généré avec `openssl rand -hex 32` |
   | `PORT` | `3001`, port du serveur web |
   | `HOST` | `127.0.0.1`, écoute locale |
   | `COOKIE_SECURE` | `false` en HTTP local, `true` derrière HTTPS |

   La clé DeepSeek reste dans n8n. Ne préfixer aucun secret par `VITE_` :
   le navigateur n'a besoin d'aucun jeton. Ne pas écraser `.env` lors des mises à jour.

5. Construire et démarrer :

   ```bash
   npm run build
   npm start
   ```

6. Ouvrir <http://127.0.0.1:3001>. Tester les segments, une page de clients,
   un export et une question à l'assistant. Conserver le terminal ouvert.

Le serveur Node sert les fichiers compilés et relaie les requêtes `/api/` vers
FastAPI ou n8n. Le chargement de `.env` utilise [l'option native de Node.js](https://nodejs.org/api/cli.html#--env-filefile).
Les services Docker restent ceux de `n8n/docker-compose.yml` ; le frontend
est lancé sur l'hôte et utilise leurs ports publiés.

## Développer

Depuis `frontend/`, ouvrir deux terminaux :

```bash
npm run server
```

```bash
npm run dev
```

Ouvrir l'adresse indiquée par Vite, habituellement <http://127.0.0.1:5173>.
Le [proxy de développement Vite](https://vite.dev/config/server-options.html#server-proxy)
transmet `/api/` au serveur local sur le port 3001. Si ce port change,
adapter `vite.config.js`. `npm run preview` ne remplace pas le serveur applicatif ;
utiliser `npm start` pour tester la compilation avec les services.

## Parcours disponibles

- **Vue d'ensemble** : effectifs, CA positif, poids des retours, répartition du CA.
- **Segments & clients** : sélection d'un segment, profils moyens et recommandations,
  liste paginée de 25 clients. La recherche porte sur la page chargée ; l'export
  porte sur les lignes filtrées de cette page.
- **Qualité du modèle** : critères de choix de k, scores, stabilité, correspondance
  k=4/k=5 et sensibilité au montant net. Les chiffres restent accompagnés de leurs sources.
- **Assistant marketing** : questions libres et suggestions contextuelles depuis
  les segments. Le rendu Markdown n'active pas le HTML brut.

Les données sont historiques, les montants sont en livres sterling et les
recommandations n'attestent pas de performances de campagne. Les graphiques
utilisent les parts de CA fournies par l'API.

## Conversations et accès

Une conversation possède un UUID dans le stockage de session de l'onglet.
Le serveur associe cet UUID à un cookie signé `HttpOnly` avant de transmettre
un identifiant dérivé à n8n. Deux navigateurs ayant le même UUID ne partagent
ainsi pas le contexte. Le jeton webhook reste côté serveur.

Le texte affiché est conservé dans `sessionStorage` pour retrouver la discussion
après rechargement de l'onglet. PostgreSQL conserve le contexte côté n8n.
**Nouvelle discussion** crée un autre contexte ; cela ne supprime pas les lignes
PostgreSQL. Fermer l'onglet, effacer le cookie ou changer `SESSION_SECRET` peut
empêcher la reprise de la conversation. Sans secret configuré, un secret
éphémère est créé au démarrage. Il ne convient pas à une reprise durable.

Cette configuration est une plateforme locale, sans comptes utilisateurs.
Avant une exposition publique, ajouter une authentification et une limitation
des appels au serveur Node, configurer HTTPS et `COOKIE_SECURE=true`, puis
protéger l'accès aux données individuelles. Un cookie de conversation n'est
pas une authentification. Le reverse proxy doit préserver `Host` et autoriser
les réponses du chatbot jusqu'à 330 secondes. Les polices Google sont facultatives :
le navigateur utilise une police système si elles sont indisponibles.

## Dépannage et validation

| Symptôme | Action |
| --- | --- |
| API indisponible | Vérifier FastAPI, `RFM_API_URL` et les ports Docker |
| Assistant non configuré | Renseigner `N8N_WEBHOOK_TOKEN`, puis redémarrer Node |
| Assistant indisponible | Vérifier le workflow publié, ses credentials et son exécution dans n8n |
| Contexte perdu au redémarrage | Conserver `SESSION_SECRET`, le cookie et l'identifiant de conversation |
| Fichier introuvable | Exécuter `npm run build` depuis `frontend/` |

```bash
npm run lint
npm run build
node --test tests/server.test.mjs
```

Le test du relais utilise un service simulé, sans clé fournisseur : validation,
transmission du jeton côté serveur, isolation des sessions et routes autorisées.
Un test réel du chatbot demande les credentials personnels configurés dans n8n.
