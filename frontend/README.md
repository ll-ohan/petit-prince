# Interface Web - Le Petit Prince RAG

Interface web minimaliste pour interagir avec le système RAG du Petit Prince.

## Caractéristiques

### 🎯 Design Philosophy
- **Zéro dépendances** : Pas de framework (React/Vue), pas de npm, pas de build
- **Single-page** : Un fichier HTML avec CSS inline, un fichier JS
- **Accessible** : HTML sémantique, navigation clavier, compatible lecteurs d'écran
- **Responsive** : Optimisé mobile, tablet et desktop
- **Progressif** : Fonctionne sans JavaScript (message d'activation)

### ✨ Fonctionnalités

**Interface de chat :**
- Messages utilisateur et assistant avec design différencié
- Streaming en temps réel (SSE) ou mode bloquant
- Indicateur de chargement pendant la génération
- Sauvegarde automatique de la conversation (localStorage)
- Bouton pour effacer l'historique

**Mode Debug :**
- Visualisation des métriques de tokens
- Timings détaillés (embedding, search, rerank, generation)
- Affichage des sources récupérées avec scores de pertinence
- Tags HAUTE/MODÉRÉE selon le seuil

**Paramètres :**
- URL de l'API configurable
- Toggle streaming on/off
- Mode debug activable
- Métriques étendues optionnelles
- Indicateur d'état de connexion

**Initialisation :**
- Bouton pour réindexer le livre
- Confirmation avant lancement
- Feedback sur le succès/échec

## Structure des fichiers

```
frontend/
├── index.html          # Interface complète avec CSS inline
├── app.js              # Logique API + DOM manipulation
└── README.md           # Ce fichier
```

## Utilisation

### Mode développement (local)

Servir les fichiers statiques avec n'importe quel serveur HTTP :

```bash
# Python
cd frontend
python -m http.server 8080

# Node.js
npx serve frontend

# PHP
php -S localhost:8080 -t frontend
```

Puis ouvrir http://localhost:8080

### Mode production (Docker)

L'interface est automatiquement servie par Nginx avec Docker Compose :

```bash
docker-compose up -d
```

Accéder à http://localhost

### Configuration Nginx

Le fichier [../config/nginx.conf](../config/nginx.conf) configure :
- Serving des fichiers statiques
- Proxy des requêtes API vers le backend
- Support du streaming (SSE)
- Headers de sécurité
- Compression gzip
- Cache des assets

## API Communication

### Endpoints utilisés

```javascript
// Health check
GET /health

// Initialisation
POST /api/init

// Chat
POST /api/v1/chat/completions
Headers:
  - Content-Type: application/json
  - X-Include-Metrics: true (optionnel)
Body:
  - messages: array de {role, content}
  - stream: boolean
```

### Streaming (SSE)

Format Server-Sent Events conforme OpenAI :

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",...}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk",...}

data: [DONE]
```

## Personnalisation

### Thème de couleurs

Modifier les variables CSS dans [index.html](index.html) :

```css
:root {
    --primary: #4A90E2;        /* Couleur principale */
    --secondary: #F5A623;       /* Couleur secondaire */
    --background: #FAFBFC;      /* Fond de page */
    --surface: #FFFFFF;         /* Cartes et surfaces */
    --text-dark: #2C3E50;       /* Texte principal */
    --text-light: #7F8C8D;      /* Texte secondaire */
}
```

### Messages vides

Modifier le HTML de l'état vide :

```html
<div class="empty-state">
    <div class="empty-state-icon">🌟</div>
    <h2 class="empty-state-title">Votre titre</h2>
    <p class="empty-state-text">Votre texte</p>
</div>
```

### Toasts

Modifier les icônes et styles dans [app.js](app.js) :

```javascript
const icons = {
    success: '✓',
    error: '✗',
    warning: '⚠',
    info: 'ℹ'
};
```

## Stockage Local

L'application utilise localStorage pour persister :

```javascript
petitprince_api_url         // URL de l'API
petitprince_conversation    // Historique des messages
petitprince_streaming       // Préférence streaming
petitprince_debug           // Mode debug
petitprince_metrics         // Métriques étendues
```

Pour réinitialiser :

```javascript
localStorage.clear();
location.reload();
```

## Compatibilité

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

**Fonctionnalités modernes utilisées :**
- CSS Grid & Flexbox
- CSS Custom Properties (variables)
- Fetch API
- Async/Await
- LocalStorage
- ReadableStream (pour SSE)

## Performance

**Optimisations :**
- CSS inline (pas de requête réseau)
- Minimal JavaScript (< 15KB non compressé)
- Pas de bundle, pas de transpilation
- Cache navigateur pour assets
- Compression gzip via Nginx

**Métriques typiques :**
- First Contentful Paint: < 500ms
- Time to Interactive: < 1s
- Total size: < 20KB (HTML + JS)

## Sécurité

**Headers de sécurité (Nginx) :**
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

**Bonnes pratiques :**
- Pas d'eval() ou innerHTML avec données utilisateur
- textContent utilisé pour l'affichage de texte
- Validation côté serveur (pas seulement client)
- HTTPS recommandé en production

## Améliorations futures

Idées d'évolutions (optionnelles) :

1. **Export de conversation** : Télécharger en JSON/Markdown
2. **Recherche dans l'historique** : Filtrer les messages
3. **Favoris** : Marquer des questions/réponses
4. **Mode vocal** : Speech-to-text pour les questions
5. **Multi-langue** : Interface en anglais
6. **Thème sombre** : Toggle dark/light mode
7. **Raccourcis clavier** : Navigation rapide

## Debugging

Activer les logs dans la console :

```javascript
// Dans app.js, ajoutez en haut :
const DEBUG = true;

// Puis utilisez :
if (DEBUG) console.log('Message de debug');
```

Vérifier les requêtes réseau dans DevTools (onglet Network).

## License

MIT - Voir [../README.md](../README.md)
