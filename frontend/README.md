# RFM studio

Interface React de la plateforme : tableau de bord, fiches des segments,
exploration des clients, diagnostics de clustering et assistant marketing.
Les indicateurs proviennent de FastAPI. Aucune donnée de démonstration n'est
substituée à une API indisponible.

## Démarrer avec Docker

Installer Docker et Docker Compose. Node.js n'est pas requis sur la machine.
Le Compose de `n8n/` démarre les quatre services : frontend, FastAPI, n8n et PostgreSQL.
Depuis la racine du dépôt, à la première installation :

```bash
cd n8n
cp .env.example .env
```

Dans `n8n/.env`, renseigner `POSTGRES_PASSWORD` et `SESSION_SECRET` avec deux
secrets distincts. Générer le secret de session avec `openssl rand -hex 32`.
Renseigner `N8N_WEBHOOK_TOKEN` avec la valeur du credential Header Auth
`X-RFM-Token` configuré dans n8n. Il peut rester vide pendant la configuration :
les vues d'analyse fonctionnent, le chatbot affiche une erreur explicite.
La clé DeepSeek se configure uniquement dans n8n.

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Ouvrir <http://127.0.0.1:3001> pour la plateforme et <http://localhost:5678>
pour configurer n8n. Suivre le [guide n8n](../n8n/README.md) pour importer le
workflow, configurer les trois credentials et publier le webhook.
Après avoir renseigné le jeton dans `.env`, appliquer sa valeur au frontend :

```bash
docker compose up -d frontend
```

Pour une installation déjà configurée, compléter le `.env` existant avec
`FRONTEND_PORT=3001`, `SESSION_SECRET` et `N8N_WEBHOOK_TOKEN`, sans le remplacer.
Le fichier `frontend/.env` n'est pas utilisé par ce Compose.

Le frontend appelle `http://segmentation-api:8000` et
`http://n8n:5678/webhook/rfm-chat` sur le réseau Docker. Le navigateur utilise
uniquement le port du frontend ; le jeton est injecté au serveur à l'exécution,
jamais dans les fichiers JavaScript compilés. Modifier `FRONTEND_PORT` si 3001
est occupé. Les ports restent liés à la machine locale.

L'image compile React dans une étape de construction puis exécute seulement
le serveur Node et les fichiers statiques avec l'utilisateur non privilégié
`node`. Le contexte de construction exclut les fichiers `.env`, les dépendances
locales et les sauvegardes. Le contrôle de santé vérifie la page web ; les
connexions API et chatbot se vérifient séparément depuis l'interface.

Pour reconstruire après une modification du frontend, depuis `n8n/` :

```bash
docker compose up --build -d frontend
docker compose logs --tail=100 frontend
```

`docker compose stop` arrête la pile et `docker compose up -d` la redémarre.
Conserver le secret de session et les volumes n8n/PostgreSQL pour maintenir
la continuité des conversations. Ne pas utiliser `down -v` pour une simple mise à jour.

## Démarrer sans Docker pour le frontend

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
Dans ce mode, le frontend est lancé sur l'hôte et utilise les ports publiés
des services Docker. Si le frontend Docker fonctionne déjà, l'arrêter avec
`docker compose stop frontend` depuis `n8n/` pour libérer le port 3001.

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

## Classer un client

Ouvrir **Classer un client** dans la navigation. Saisir la récence en jours,
la fréquence en factures distinctes et le montant des achats positifs en GBP,
puis cliquer sur **Déterminer le segment**. Le résultat affiche le groupe,
la recommandation documentée et les valeurs éventuellement plafonnées.
Modifier un champ efface le résultat précédent pour éviter de l'associer à
une autre saisie. Cette simulation ne crée aucun enregistrement client.

La période d'entraînement et la date de référence sont affichées dans la vue.
Employer les mêmes définitions et une fenêtre comparable : une fréquence
mensuelle n'est pas directement comparable à celle de deux années d'achats.
Le classement fonctionne sans n8n ni clé DeepSeek ; il appelle FastAPI via
le relais `POST /api/predict`. Le bouton d'approfondissement utilise l'assistant
uniquement sur demande, avec le nom du segment et sans les valeurs RFM saisies.
