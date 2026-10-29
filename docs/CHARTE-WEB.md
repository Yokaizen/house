# Charte web Proximy — UI & UX

Référence de conception pour tout site, outil ou application web de Proximy (groupe Riccobono, distribution de presse, colis et courriers, « expert du dernier kilomètre »). Elle couvre l'**UX** (ce que la personne vit : trouver, comprendre, agir, être rassurée) et l'**UI** (l'apparence : couleurs, typographie, composants). Signature de marque : **« Parce que la confiance se livre aussi. »**

## Comment utiliser ce document

- **Méthode en 6 étapes** pour chaque écran ou fonctionnalité :
  1. Identifie le profil et le parcours concernés (section 3).
  2. Fixe l'objectif de la page et son **action principale** (sections 2 et 5).
  3. Structure l'information et le contenu (sections 4 et 8).
  4. Choisis le modèle de page et les composants (sections 17 et 18).
  5. Prévois tous les états, l'accessibilité et le mobile (sections 7, 9 et 10).
  6. Termine par la checklist de la section 20.
- Réutilise les composants de la partie UI avant d'en inventer. N'utilise que les couleurs, polices, arrondis et espacements listés ici ; pas de valeur en dur hors variables.
- Conçois toujours la version mobile ET ordinateur (mobile d'abord).
- Les exemples utilisent Tailwind CSS v4. Hors Tailwind, reprends les mêmes valeurs en CSS.

**Plan** : 1 Esprit de marque · **Partie UX** : 2 Principes · 3 Utilisateurs et parcours · 4 Architecture de l'information · 5 Conversion · 6 Formulaires · 7 Retours et états · 8 Contenu et micro-copy · 9 Mobile, terrain, performance · 10 Accessibilité · 11 Confiance et vie privée · 12 Mesure · **Partie UI** : 13 Couleurs · 14 Typographie · 15 Logos, images, mascottes · 16 Mise en page · 17 Composants · 18 Modèles de pages · 19 Écrans et animations · 20 Checklist · Annexe.

# Partie 1 — Fondations

## 1. Esprit de marque et valeurs

Premium, épuré, lumineux, formes rondes, simple et dynamique. Le **rose** = vitalité, proximité, action. Le **bleu marine** = confiance, sérieux, structure. Un écran réussi utilise le bleu pour structurer et le rose pour guider l'œil vers l'action. Un seul message par section, beaucoup d'air.

### Valeurs

Trois valeurs portent l'identité : **Humain** (entreprise à taille humaine, diversité, inclusion, respect, écoute), **Engagement** (l'implication de chacun est le moteur de la performance : précision des tournées, qualité de service) et **Excellence** (recherche constante de performance, innovation et outils technologiques, qualité de la préparation à la livraison).

| Valeur | Dans l'interface et l'expérience |
|---|---|
| Humain | Visages, mascottes, ton chaleureux, vouvoiement bienveillant |
| Service | Chaque écran répond à un besoin : action claire, parcours court |
| Proximité | Adresses, agences et contacts visibles ; vocabulaire simple, pas de jargon |
| Engagement | Confirmer chaque action (messages de succès, suivi d'état) |
| Fiabilité | Statuts explicites, aucune surprise, comportements constants d'un outil à l'autre |
| Expresse | Rapidité : peu de clics, chargements annoncés, actions principales à portée de pouce |
| Implication | Retours utiles : états, progression, aide contextuelle |
| Flexibilité | Interfaces adaptables : mobile d'abord, filtres et préférences |
| Sérénité | Messages rassurants, erreurs expliquées sans reproche, pas d'alarmisme |
| Excellence | Finitions soignées : alignements, états, accessibilité |

# Partie 2 — UX : l'expérience

L'UX décide **ce que la personne vit** : trouver, comprendre, agir, être rassurée. L'UI (partie 3) décide **à quoi cela ressemble**. On conçoit toujours l'UX en premier : un bel écran qui ne mène pas à l'action est un écran raté.

## 2. Principes UX

| # | Principe | Ce que cela impose |
|---|---|---|
| 1 | **Une page, un objectif** | Chaque page a une action principale (bouton rose) et un seul message par section. |
| 2 | **Toujours savoir où l'on est** | Menu actif surligné, fil d'Ariane, titre h1 identique au libellé du menu. |
| 3 | **Peu d'effort** | Toute information clé à 3 clics maximum ; un formulaire de contact tient en 6 champs maximum ; pas de compte obligatoire pour contacter ou postuler. |
| 4 | **Mobile d'abord** | On dessine à 360 px de large, au pouce, puis on agrandit. |
| 5 | **Aucune surprise** | Un composant se comporte partout pareil ; on annonce ce qui va se passer avant de cliquer (« Envoyer la demande », « Fichier PDF, 2,4 Mo »). |
| 6 | **Toujours un retour** | Chaque action reçoit une réponse visible immédiate : survol, appui, chargement, succès, erreur. |
| 7 | **Droit à l'erreur** | On peut corriger, annuler, revenir. Les actions destructrices sont confirmées. Jamais de saisie perdue. |
| 8 | **Rassurer, ne pas alarmer** | Ton calme, erreurs expliquées sans reproche, prochaine étape toujours indiquée. |
| 9 | **Langage du visiteur** | Mots simples, pas de jargon interne (« tournée », « PDV » : à expliquer ou à éviter côté public). |
| 10 | **Inclusif et honnête** | Utilisable par tous (clavier, lecteur d'écran, petit écran, lumière forte). Aucun piège : pas de case précochée, pas de fausse urgence. |

## 3. Utilisateurs et parcours

Avant de concevoir un écran, choisis le profil et le parcours concernés dans ce tableau.

| Profil | Contexte d'usage | Ce qu'il veut | Parcours clé | Outil |
|---|---|---|---|---|
| **Candidat livreur** | Smartphone, souvent en mobilité, peu de temps | Comprendre le métier, voir si c'est près de chez lui, postuler vite | Arrivée → fiche métier → agences / conditions → « Postuler » → confirmation | Proximy Recrute |
| **Candidat manager ou fonction support** | Ordinateur ou mobile, lit plus en détail | Mesurer les responsabilités, l'évolution, la culture | Arrivée → métiers → « Évoluer chez Proximy » → contact ou candidature | Proximy Recrute |
| **Client ou prospect B2B** (éditeur de presse, annonceur, entreprise colis ou courrier, collectivité) | Ordinateur, compare des prestataires | Voir si Proximy répond à son besoin, avoir un interlocuteur | Arrivée → offre concernée → preuves (chiffres, labels, agences) → « Nous contacter » → confirmation | Site Proximy |
| **Client local** (Oise) | Ordinateur ou mobile | Savoir si son secteur est couvert, joindre l'agence | Arrivée → couverture / services → contact | Proximy Oise Diffusion |
| **Livreur en tournée** | En extérieur, une main, gants, soleil, réseau variable | Voir sa tâche, valider, avancer sans réfléchir | Liste du jour → étape → validation → suivante | Application ProxiDriver |
| **Collaborateur interne** | Ordinateur, tâches répétées chaque jour | Trouver, filtrer, corriger, exporter | Liste filtrée → détail → action → confirmation | Back-offices, outils |

Pour chaque nouveau parcours, écris d'abord en une phrase : « *[Profil] veut [objectif] ; il a réussi quand [résultat visible]* ». Exemple : « Un candidat livreur veut postuler ; il a réussi quand il voit "Candidature envoyée" ».

## 4. Architecture de l'information et navigation

- **Structure de référence du site Proximy** : Qui sommes-nous (raison d'être, organisation, schéma logistique, RSE) · Nos offres (Presse, Colis, Courriers, Pub) · Services · Nous rejoindre · Contact. Reprends cette logique pour tout nouveau site : on classe selon les **questions du visiteur**, pas selon l'organigramme.
- **7 entrées maximum** dans le menu principal, 8 sous-entrées maximum par menu, **3 niveaux maximum** au total.
- **Libellés** : 1 à 3 mots, les mots du visiteur (« Nos offres », « Nous rejoindre »), identiques au titre h1 de la page. Pas d'acronyme interne.
- **Un contenu = une place.** Pas de doublon dans un menu (une rubrique n'apparaît qu'une fois), pas de page orpheline : toute page est atteignable depuis un menu ou un lien contextuel.
- **Contact toujours accessible** : bouton « Nous contacter » dans l'en-tête et lien dans le pied de page, sur toutes les pages.
- **URL lisibles** : minuscules, tirets, sans accents (`/nos-offres`, `/nous-rejoindre`). Une URL ne change pas une fois publiée (sinon redirection).
- **Ordre des éléments** : du plus important au moins important pour le visiteur. Les mentions légales, cookies et confidentialité vivent dans le pied de page.
- **Recherche interne** : seulement au-delà d'une cinquantaine de pages ou pour les outils à données (tournées, colis). Sinon, un bon menu suffit.
- Les composants de navigation (en-tête, menu mobile, fil d'Ariane, onglets, pagination) sont décrits en section 17.

## 5. Parcours de conversion et appels à l'action

- **Structure d'une page**, dans cet ordre : promesse (h1 + introduction) → preuve (chiffres, visages, labels, agences) → détail → appel à l'action. La promesse et **l'action principale sont visibles sans faire défiler**, y compris sur mobile.
- **Une action principale par écran** (bouton rose). L'action secondaire est un bouton contour ou un lien. L'appel à l'action est **répété en bas de page** (bandeau bleu).
- **Le libellé annonce le résultat**, pas le geste :

| Page | Action principale | Action secondaire |
|---|---|---|
| Accueil | Découvrir nos offres | Nous contacter |
| Offre ou service | Nous contacter | Voir les autres offres |
| Fiche métier | Postuler | Voir les agences |
| Contact | Envoyer la demande | Appeler l'agence |
| Connexion | Se connecter | Mot de passe oublié |

- **Réassurance près du bouton** : ce qui va se passer et quand (« Notre équipe revient vers vous rapidement. »). Si un délai chiffré est annoncé, il doit être tenu.
- **Preuves** : chiffres clés, visages de l'équipe, labels et partenaires (France Portage Presse, Positive Company), adresses des agences. Une preuve est réelle, datée et vérifiable : jamais de chiffre inventé.
- **Coordonnées actionnables** : téléphone en `tel:`, e-mail en `mailto:`, adresse reliée à une carte.
- **Rien d'intrusif** : pas de fenêtre qui s'ouvre à l'arrivée, pas de bandeau qui masque le contenu (hors cookies), pas d'inscription forcée.

## 6. Formulaires : l'expérience

- **Demander le minimum.** Contact : nom, e-mail, téléphone (facultatif), message, consentement. Chaque champ en plus fait perdre des envois. Un champ obligatoire doit servir à répondre.
- **Aider à saisir** : bon type de clavier (`type="email"`, `type="tel"`, `inputmode`), saisie assistée (`autocomplete="given-name"`, `family-name`, `email`, `tel`), exemple de format en aide sous le champ.
- **Valider au bon moment** : à la sortie du champ, pas à chaque frappe. À l'envoi, le focus va sur le premier champ en erreur ; au-delà de 2 erreurs, un résumé en haut de formulaire liste les corrections (chaque ligne est un lien vers le champ).
- **Ne jamais effacer la saisie** après une erreur. Conserver aussi le brouillon d'une longue candidature.
- **Envoi** : le bouton passe à « Envoi en cours… » et se désactive (pas de double envoi). Si le réseau échoue : message clair, saisie conservée, bouton « Réessayer ».
- **Confirmation** : sur la page, avec titre, ce qui s'est passé et la suite. Texte de référence : « **Message envoyé** — Merci, votre message a bien été envoyé. Notre équipe revient vers vous rapidement. » Prévoir aussi un e-mail de confirmation quand la demande a une suite (candidature, devis).
- **Une demande arrive toujours chez un humain** : chaque formulaire est relié à une boîte e-mail identifiée de l'équipe concernée, testée à la mise en ligne (envoi réel).
- **Formulaire long** (candidature) : découper en 2 à 4 étapes, afficher « Étape 2 sur 4 » avec une barre de progression, permettre de revenir en arrière, finir par un récapitulatif avant l'envoi.
- **Anti-spam discret** : champ piège invisible (honeypot) et limitation du nombre d'envois. Pas de CAPTCHA avec images à reconnaître.
- **Consentement RGPD** : case **non précochée**, finalité claire (« Ces informations servent uniquement à répondre à votre demande »), lien vers la politique de confidentialité.
- Le détail visuel des champs et de leurs états est en section 17.

## 7. Retours, états et erreurs

**Temps de réponse : ce que la personne doit voir**

| Durée | Perception | À afficher |
|---|---|---|
| Moins de 0,1 s | Instantané | Changement d'état immédiat (survol, appui, case cochée) |
| 0,1 à 1 s | Fluide | Rien de spécial, mais jamais d'écran figé |
| 1 à 10 s | Attente | Indicateur rond (action) ou squelette (liste, carte) |
| Plus de 10 s | Risque d'abandon | Barre de progression, message « Cela peut prendre une minute », possibilité d'annuler |

**États à prévoir pour chaque écran** (pas seulement l'état idéal)

| État | Ce que la personne voit | Ton |
|---|---|---|
| Chargement | Squelettes, pas d'écran blanc | « Chargement de vos tournées… » |
| Vide | Mascotte MySpot + phrase positive + action | « Aucune tournée prévue aujourd'hui. » |
| Aucun résultat | Rappel de la recherche + suggestion + « Effacer les filtres » | « Aucun résultat pour « colis ». Vérifiez l'orthographe. » |
| Erreur récupérable | Alerte rouge avec icône, cause, solution, « Réessayer » | « Impossible d'envoyer le message. Vérifiez votre connexion puis réessayez. » |
| Erreur bloquante | Page d'erreur (404, 500, accès refusé) avec sortie | « Cette page a changé d'adresse. » |
| Hors ligne | Bandeau discret, actions mises en attente | « Vous êtes hors ligne. Vos actions seront envoyées dès le retour du réseau. » |
| Succès | Confirmation + suite | « Candidature envoyée. Nous revenons vers vous rapidement. » |
| Désactivé | Bouton grisé **avec la raison** à côté | « Choisissez une agence pour continuer. » |

- **Jamais de code technique** affiché (« Error 500 », trace). Toujours une phrase humaine et une porte de sortie (réessayer, contacter).
- **Confirmer ce qui est grave, annuler ce qui est léger** : suppression ou action irréversible = modale de confirmation (le bouton reprend le verbe : « Supprimer la tournée ») ; action réversible = pas de modale, mais un toast avec « Annuler » pendant 8 secondes.
- **Un seul toast à la fois**, jamais d'information essentielle uniquement dans un toast (il disparaît). Annoncé aux lecteurs d'écran (`aria-live`).
- Les composants (alertes, toasts, modales, squelettes, états vides) sont décrits en section 17.

## 8. Contenu, micro-copy et formats

**Écrire pour être lu en diagonale**

- Le plus important d'abord. Un titre dit ce que la section apporte (« Une tournée suivie en temps réel »), pas son étiquette (« Fonctionnalités »).
- Phrases de 20 mots maximum, paragraphes de 4 lignes maximum, une liste dès 3 éléments, chiffres en chiffres.
- Verbes d'action, voix active, formulations positives. Pas de jargon sans explication, pas de majuscules en milieu de phrase, pas de point d'exclamation (sauf succès).
- Français, **vouvoiement partout**, y compris dans les outils internes et l'application des livreurs.
- Formulations neutres (« les équipes », « les candidats ») ; éviter le point médian, mal lu par les lecteurs d'écran.
- Chaque page a un `<title>` unique (« Nos offres | Proximy », 60 caractères maximum) et une description de 150 caractères qui donne envie de cliquer.

**Micro-copy : à écrire / à éviter**

| Situation | À écrire | À éviter |
|---|---|---|
| Bouton | « Envoyer la demande », « Postuler » | « OK », « Valider », « Cliquez ici » |
| Étiquette de champ | « Adresse e-mail » | Placeholder à la place de l'étiquette |
| Erreur de champ | « Cette adresse e-mail semble incomplète. Exemple : prenom.nom@entreprise.fr » | « Champ invalide » |
| Aide | « Nous l'utilisons uniquement pour vous rappeler. » | Aucun motif donné |
| Succès | « Message envoyé. Notre équipe revient vers vous rapidement. » | « Succès ! » |
| Chargement | « Envoi en cours… » | « Veuillez patienter » |
| Confirmation | « Supprimer la tournée ? Elle ne pourra pas être restaurée. » | « Êtes-vous sûr ? » |
| Page 404 | « Cette page a changé d'adresse. » | « Erreur 404 : page introuvable » |
| Connexion refusée | « E-mail ou mot de passe incorrect. » (ne dit pas lequel) | « Ce compte n'existe pas » |

**Formats**

| Donnée | Format | Exemple |
|---|---|---|
| Date | JJ/MM/AAAA (court), 20 octobre 2026 (long) | 20/10/2026 |
| Heure | 24 h avec « h » | 7 h 30 |
| Montant | espace insécable, virgule, € après | 1 250,50 € |
| Nombre | espace insécable pour les milliers | 1 250 collaborateurs |
| Téléphone | paires séparées par une espace | 01 23 45 67 89 |
| Adresse | numéro, voie, code postal, ville | 38 avenue du Colonel Rol-Tanguy, 93240 Stains |

## 9. Mobile, terrain et performance

- **Mobile d'abord** : conception à 360 px, contrôle à 360 · 390 · 768 · 1024 · 1440 px. Le contenu essentiel est identique sur tous les écrans ; on adapte la présentation, pas l'information.
- **Zone du pouce** : sur mobile, l'action principale est dans le tiers bas de l'écran ou pleine largeur sous le contenu. Cibles de 44 px minimum, 48 px conseillés.
- **Rien qui n'existe qu'au survol** : tout ce qui apparaît au survol (sous-menu, info-bulle) doit aussi s'obtenir au toucher et au clavier.
- **Outils de terrain (ProxiDriver, outils livreurs)**
  - Utilisables d'une main, avec des gants : cibles de 56 px pour les actions répétées, espacées.
  - Lisibles en plein soleil comme de nuit : texte principal à contraste 7:1 minimum, taille 16 px minimum.
  - Peu de saisie : choix, boutons, scan, valeurs par défaut. Pas de texte long.
  - Réseau variable : l'action est enregistrée localement, l'écran affiche « Hors ligne — synchronisation à la reconnexion », rien n'est perdu.
  - Une tâche par écran, une action évidente, retour d'état net après chaque validation.
- **Performance** (objectifs mesurés sur mobile) : affichage du contenu principal ≤ 2,5 s (LCP), réaction aux appuis ≤ 200 ms (INP), aucun décalage de mise en page (CLS ≤ 0,1).
  - Photos au format WebP ou JPEG optimisé, dimensions déclarées (aucun saut de mise en page), photo du bandeau d'accueil viser 300 Ko, chargement différé sous la ligne de flottaison.
  - Polices en `font-display: swap`. Squelettes plutôt qu'écran blanc.
- **Résilience** : le texte, les liens et les formulaires fonctionnent même si un script échoue ; le contenu principal est dans le HTML.

## 10. Accessibilité et inclusion (RGAA / WCAG AA — obligatoire)

L'accessibilité est une exigence légale et une qualité d'usage : ce qui est accessible est plus clair pour tout le monde.

- Contraste 4,5:1 (3:1 pour grands textes et contours d'éléments). Voir section 13.
- **Jamais la couleur seule** : toujours texte et/ou icône (statut + badge, erreur + icône + message).
- **Clavier** : tout est utilisable sans souris ; l'ordre de tabulation suit l'ordre visuel ; aucun piège au clavier ; lien « Aller au contenu » en début de page. **Focus visible** partout : anneau 3 px `navy` décalé de 3 px (blanc sur fond bleu).
- **Lecteurs d'écran** : un seul `h1`, titres hiérarchisés, repères HTML (`header`, `nav`, `main`, `footer`), `lang="fr"`, étiquettes liées aux champs, `role="alert"` pour les erreurs, `aria-live` pour les toasts et résultats, `aria-current="page"` dans les menus.
- **Images** : `alt` descriptif si elle porte une information ; `alt=""` si décorative ; logo « Proximy ». Vidéos sous-titrées.
- **Zoom et texte** : lisible jusqu'à 200 % sans perte de contenu ni défilement horizontal ; tailles en `rem`.
- **Zones tactiles** ≥ 44 × 44 px, 8 px d'écart.
- **Temps** : aucune limite de temps imposée sans avertissement et prolongation possible (session d'un outil interne). Respecter `prefers-reduced-motion` ; jamais de contenu clignotant.
- **Clarté cognitive** : un sujet par écran, consignes courtes, pas de texte dans les images, abréviations expliquées à la première occurrence.

## 11. Confiance, données et vie privée

- **Pied de page obligatoire** : mentions légales, politique de confidentialité, cookies, contact et adresse.
- **Cookies** : aucun traceur non indispensable avant consentement ; « Tout refuser » aussi visible et aussi simple que « Tout accepter » ; choix modifiable à tout moment.
- **Pas de pièges (dark patterns)** : pas de case précochée, de compte à rebours artificiel, de fausse rareté, de culpabilisation (« Non, je ne veux pas réussir »), de désabonnement caché.
- **Dire pourquoi** on demande une donnée, et ne demander que l'utile.
- **Connexion** : message d'erreur générique (ne révèle pas si le compte existe), mot de passe affichable au clic, collage et gestionnaires de mots de passe autorisés, « Mot de passe oublié » visible, déconnexion automatique **annoncée** avant l'échéance.
- **Rassurer au bon endroit** : cadenas / mention de sécurité près d'un champ sensible ; adresse et contact réels visibles.

## 12. Mesurer et améliorer

| Parcours | Ce qu'on suit | Ce que cela révèle |
|---|---|---|
| Candidat | Clics « Postuler », candidatures envoyées, abandon par étape | Le métier est-il clair ? Le formulaire est-il trop long ? |
| Client B2B | Demandes de contact envoyées, clics téléphone et e-mail, pages d'offres vues | L'offre convainc-t-elle ? Le contact est-il trouvé ? |
| Tous | Vitesse (LCP, INP, CLS), erreurs de formulaire par champ, pages 404, recherches sans résultat | Où l'expérience casse |

- **Tester avec de vraies personnes** avant de publier un nouveau parcours : 5 personnes du profil concerné, une tâche réelle chacune (« Trouvez comment postuler comme livreur »), on observe sans guider. Noter où elles hésitent.
- Mesure respectueuse : analytique après consentement, aucune donnée personnelle dans les statistiques.
- Après chaque changement important, refaire le parcours complet sur téléphone, tablette et ordinateur, au clavier une fois.

# Partie 3 — UI : l'interface

L'UI traduit l'UX en écrans cohérents. Chaque valeur ci-dessous est une règle : pas d'exception sans raison.

## 13. Couleurs

### Variables (à déclarer telles quelles)

| Variable | Valeur | Usage |
|---|---|---|
| `brand` (Rosewood) | `#E80A65` | Actions principales, chiffres clés, surtitres, accents |
| `navy` (Imperial Blue) | `#061E66` | Titres, liens, fonds bleus, boutons secondaires forts |
| `platinium` | `#E9E9FF` | Fonds doux, information |
| `indigo` | `#4B4584` | Liens visités, détails |
| blanc | `#FFFFFF` | Fonds, texte sur fond foncé |
| `brand-600` | `#C70653` | Survol bouton rose |
| `brand-700` | `#A10443` | Texte rose sur fond rose clair, bouton appuyé |
| `brand-50` / `brand-100` | `#FFF1F6` / `#FFE4EE` | Fond / bordure d'encart rose |
| `navy-800` | `#061449` | Survol bouton bleu |
| `navy-900` | `#04102F` | Pied de page, dégradés, toasts |
| `navy-50` / `navy-100` | `#F2F4FB` / `#E2E7F5` | Survol de menu / bordures douces |
| `ink` | `#0D1330` | Texte courant |
| `muted` | `#5B6478` | Texte secondaire, sous-menus mobile |
| `line` | `#E4E6EE` | Filets et bordures |
| `paper` | `#F7F7F9` | Fond d'encart, lignes paires de tableau |

### Couleurs d'état

| État | Solide | Texte | Fond |
|---|---|---|---|
| Succès | `#12855A` | `#0B6B47` | `#E6F5EE` |
| Alerte | `#E0A100` | `#7A4B00` | `#FFF3D6` |
| Erreur / danger | `#D1242F` | `#A4161A` | `#FDE8E8` |
| Information | `#061E66` | `#061E66` | `#E9E9FF` |

Le rose de marque n'est jamais une couleur d'erreur. Une erreur est toujours rouge, avec une icône et un texte.

### Règles

- Rose = actions principales, chiffres clés, surtitres. Pas pour du long texte.
- Bleu marine = titres, texte de lien, fonds. **Pas de noir** dans les menus et titres : utilise `navy` (ou `muted` pour le secondaire).
- Rose sur fond bleu marine : uniquement les grands titres et décors, jamais du petit texte (contraste 3,4:1).
- Rosewood sur blanc = contraste 4,5:1 (limite) : réserve-le aux titres, boutons et textes en gras, jamais au petit texte courant.
- Texte sur fond bleu : blanc (ou blanc à 70 % pour le secondaire).

### Contrastes de référence

| Paire | Ratio | Usage autorisé |
|---|---|---|
| Bleu `#061E66` sur blanc | 15,2 | tout texte |
| Encre `#0D1330` sur blanc | 18,2 | texte courant |
| Gris `#5B6478` sur blanc | 5,9 | texte secondaire |
| Indigo `#4B4584` sur blanc | 8,5 | détails |
| Blanc sur Rosewood | 4,5 | boutons (texte 14 px medium minimum) |
| Rosewood sur blanc | 4,5 | titres, surtitres, chiffres |
| Rosewood sur Platinium | 3,8 | grands textes seulement |
| Rosewood sur bleu nuit `#04102F` | 4,2 | grands textes seulement |
| Placeholder `#6A6F85` sur blanc | 5,0 | placeholders (jamais plus clair) |

## 14. Typographie

- **Titres et chiffres clés : Groogla** (une seule graisse, fichier `Croogla4F.woff2`). Interligne 1,05, interlettrage −0,015 em, couleur `navy` (blanc sur fond bleu).
- **Texte : Century Gothic** (Regular et Bold, italiques disponibles). Corps de texte, boutons, menus, champs.
- Repli : `Georgia, serif` pour Groogla ; `ui-sans-serif, sans-serif` pour Century Gothic. Les fichiers de polices sont fournis par Proximy dans `public/fonts/` ; déclare-les avec `@font-face` et `font-display: swap`.

| Rôle | Police | Taille ordinateur / mobile | Interligne |
|---|---|---|---|
| Titre de page (h1, bandeau bleu) | Groogla | 60 / 48 px | 1,05 |
| Titre de section (h2) | Groogla | 48 / 36 px | 1,05 |
| Sous-titre (h3) | Groogla | 24 px | 1,05 |
| Chiffre clé | Groogla | 60 px (compact 38 px) | 1,05 |
| Introduction | Century Gothic | 18 px | 1,625 |
| Texte courant | Century Gothic | 16 px | 1,625 |
| Bouton, menu, champ | Century Gothic medium | 14 px | 1,4 |
| Légende, aide | Century Gothic | 12 px | 1,5 |
| Surtitre (eyebrow) | Century Gothic Bold | 12 px, capitales, +0,18 em | 1 |

Titres et surtitres : un seul `h1` par page, hiérarchie h1 → h2 → h3 sans saut.

## 15. Logos, images, mascottes

- **Logo Proximy** : pin de localisation dans le « O », « X » élancé, bicolore (PROXI en rose, MY en bleu marine). Écriture en majuscules.
- Versions : bicolore sur fond clair ; **blanc** sur fond bleu marine, rose ou photo sombre ; noir pour impressions monochromes ; bleu monochrome possible.
- **Déclinaisons** : le logo Proximy avec la mention de l'entité ou de l'offre placée **sous le « MY », alignée à droite, en bleu marine**. Entités : *Proximy Oise Diffusion*, *MediaPresse* (logotype propre, MEDIA en rose + PRESSE en bleu). Offres commerciales : *ProxiColis* (logotype propre, PROXI en rose + COLIS en bleu), *Proximy Presse*, *Proximy Courrier*, *Proximy Pub*. RH : *Proximy Recrute*. Chacune existe en version blanche pour les fonds foncés. Partenaires et labels affichés en blanc dans le pied de page : France Portage Presse, Positive Company.
- **Interdit** : déformer ou étirer, changer l'épaisseur ou l'alignement, recolorer hors palette, ton sur ton (rose sur rose, bleu sur bleu), casser le bicolore (sauf blanc et noir).
- Taille : en-tête = hauteur 24 px (≈ 110 px de large) ; pied de page ≈ 101 px de large. Ne descends pas sous 80 px de large.
- Fournis les logos en SVG quand c'est possible ; sinon PNG à 2× minimum de la taille affichée.
- **Mascottes — la Proxifamily** : MySpot (personnage principal, s'adapte à toutes les situations), MyCourier (courriers), MyPacket (colis), MyBox (publicité), MyPress (presse). Sur fond clair ou Platinium, jamais sur photo ni sur fond bleu marine (les contours se perdent), jamais recolorées ni déformées, 80 px de haut minimum, une mascotte par bloc (celle de l'offre concernée). Idéales pour états vides, bienvenue et succès.
- **Photos** : authentiques, lumineuses, personnes souriantes en équipement Proximy. Toujours un `alt` pertinent. Fichiers JPEG ou WebP (PNG transparent pour schémas et mascottes), 5 Mo maximum, noms descriptifs en minuscules avec tirets.
- **Filtre bleu sur les photos des bandeaux** : fond `navy-900` (#04102F), photo à **30 % d'opacité** (`object-cover opacity-30`), puis un dégradé de gauche à droite en bleu nuit de **65 % → 50 % → 20 %** (`bg-gradient-to-r from-navy-900/65 via-navy-900/50 to-navy-900/20`). Le texte est à gauche, là où le filtre est le plus dense. Hauteur du bandeau d'accueil : `py-28 sm:py-36 lg:py-44` ; bandeaux des autres pages : `bg-navy py-24 sm:py-28` (fond uni ou même filtre). Jamais de texte blanc sur une photo sans filtre.
- **Formats d'images et coins arrondis** :

| Usage | Format | Arrondi | Classes |
|---|---|---|---|
| Bandeau de page | pleine largeur, recadrée | aucun | `object-cover` |
| Photo de section (métier, histoire) | 4:3 (1:1 sur ordinateur pour une photo isolée) | 16 px | `aspect-4/3 overflow-hidden rounded-2xl` |
| Photo d'offre, RSE | 16:10 | 16 px | `aspect-[16/10] rounded-2xl` |
| Portrait (CODIR) | 3:4, 112 px de large, cadré sur le haut | 12 px | `aspect-[3/4] w-[7rem] rounded-xl object-cover object-top` |
| Schéma, carte, illustration | ratio d'origine, jamais recadrée | aucun | `h-auto w-full` |
| Mascotte, logo | PNG transparent, jamais recadré ni arrondi | aucun | `object-contain` |

- **Icônes** : une seule famille, trait 1,5 px, extrémités arrondies, bleu marine ou Rosewood uniquement, tailles 16 / 20 / 24 px. Une icône ne porte jamais seule une information.

### Patterns et fonds filigranes

Cinq fonds décoratifs officiels (fournis dans le dossier `11-fonds-patterns` du pack : `public/brand/patterns/`). Ils habillent les grandes surfaces (sections, bandeaux, réseaux sociaux) et ne portent **jamais** d'information.

| # | Fond | Composition | Usage |
|---|---|---|---|
| 1 | Ruban filigrane | Ruban gris-bleu `#BCC8D4` à **9 %** d'opacité sur blanc (PNG transparent 2000 × 1125) | Sections claires : valeurs, à propos, contenu long. Texte `navy` ou `ink` |
| 2 | Pins filigrane | Pins de localisation inclinés, beige très clair `#FBF9F7` sur blanc (1600 × 2000) | Agences, couverture, contact, cartes : tout ce qui parle de proximité |
| 3 | Boîtes aux lettres bleu | Photo de boîtes aux lettres teintée bleu marine (≈ `#152A6C`, plus sombre vers `#061E66`) | Bandeau ou bloc sombre sur le courrier et la distribution. Texte blanc |
| 4 | Ruban rose sur bleu | Fond `navy` `#061E66`, grand ruban `brand` `#E80A65` découpé par les bords | Appel à l'action, couvertures, réseaux sociaux. Texte blanc sur la zone bleue unie |
| 5 | Ruban blanc sur rose | Fond `brand` `#E80A65`, grand ruban blanc | Bandeau d'action fort, très peu de texte : titre blanc gras de grande taille uniquement |

Règles :
- **Un seul pattern par section.** Jamais deux patterns superposés, ni un pattern sur une photo.
- Décor pur : en CSS (`background-image`, `background-size: cover`, `background-position: center`) avec une couleur de repli (`background-color`), sans texte alternatif ; si une balise `<img>` est utilisée, `alt=""` et `aria-hidden="true"`.
- Le contraste du texte se calcule sur la couleur de fond **unie** : place le texte sur une zone calme du motif. Ne jamais poser de petit texte rose ou de texte courant sur les rubans colorés (4 et 5).
- Filigranes 1 et 2 : opacité 10 % maximum, jamais renforcés, jamais recolorés. Les rubans sont recadrés par les bords de la surface, jamais étirés ni déformés (épaisseur du trait conservée).
- Pas de pattern derrière un tableau, un formulaire ou un champ : ils restent sur fond blanc ou `paper`.
- Mobile : recadrer (`background-position`) pour garder un tracé visible ; pas de pattern lourd en plus d'une photo : poids du fichier ≤ 150 Ko en WebP.

## 16. Mise en page

| Élément | Valeur |
|---|---|
| Largeur max du contenu | 1152 px (`max-w-6xl`), centré |
| Marges latérales | 24 px mobile, 32 px dès 1024 px (`px-6 lg:px-8`) |
| Section | 80 px haut/bas, 112 px dès 640 px (`py-20 sm:py-28`) |
| Bandeau bleu de page | 96 px haut/bas, 112 px dès 640 px (`bg-navy py-24 sm:py-28`) |
| En-tête | 72 px de haut, fixe (`sticky top-0 h-[72px]`) |
| Points de rupture | mobile < 640 · tablette 640–1023 · ordinateur ≥ 1024 |
| Colonnes | 1 mobile · 2 tablette · 3 à 4 ordinateur |
| Gouttière entre cartes | 16 à 24 px |
| Échelle d'espacement (multiples de 4) | 4, 8, 16, 24, 32, 48 (80 et 112 pour les sections) |
| Arrondis | pilule (boutons, recherche) · 16 px cartes · 12 px champs et menus · 8 px éléments de menu |
| Bordures | 1 px `line` plutôt que des ombres |
| Ombres | seulement pour ce qui flotte : menu déroulant (`shadow-lg`), toast, modale |

### Grille par appareil

| | Téléphone (< 640 px) | Tablette (640–1023 px) | Ordinateur (≥ 1024 px) |
|---|---|---|---|
| Largeur maximale du contenu | pleine largeur − marges | pleine largeur − marges | **1152 px**, centré |
| Nombre de colonnes | 4 | 8 | 12 |
| Marges latérales | 24 px | 24 px | 32 px |
| Gouttière | 16 px | 24 px | 24 px |
| Cartes par ligne | 1 (4 col.) | 2 (4 col. chacune) | 3 (4 col.) ou 4 (3 col.) |

Au-delà de 1152 px, le contenu reste centré : seules les marges grandissent. Un bandeau de couleur ou une photo peut occuper toute la largeur de l'écran.

Alterner les fonds de sections : blanc → papier → bleu. Zones tactiles : 44 × 44 px minimum, 8 px d'écart entre deux cibles.

## 17. Composants

### Boutons

Forme pilule, texte 14 px medium, hauteur 44 px. **Une seule action principale (rose) par écran.**

```
base    : inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60
primary : bg-brand text-white hover:bg-brand-600           (action principale)
dark    : bg-navy text-white hover:bg-navy-800             (en-tête, action secondaire forte)
ghost   : border border-line text-navy hover:border-navy   (alternative)
light   : bg-white text-navy hover:bg-white/90             (sur fond bleu)
quiet   : text-navy underline underline-offset-4           (action discrète)
danger  : bg-[#D1242F] text-white hover:bg-[#A4161A]       (action destructrice)
```

- Tailles : petit 36 px / 13 px · moyen 44 px / 14 px (défaut) · grand 52 px / 16 px.
- États : survol plus foncé (200 ms) · appui `brand-700` · focus anneau bleu 3 px décalé de 3 px (blanc sur fond bleu) · désactivé opacité 60 % · chargement texte « Envoi en cours… » + désactivé.
- Bouton icône seule : rond 44 × 44 px avec libellé accessible (`aria-label`). Bouton flottant mobile : rond 52 px, rose, une seule action clé.
- Icône : flèche → à droite pour avancer, icône à gauche pour une action (16 px, 8 px d'écart).
- Ordre : action principale à droite sur ordinateur, en haut pleine largeur sur mobile. Jamais deux boutons roses côte à côte.
- Libellés : verbe d'action, 1 à 3 mots, majuscule initiale, sans point. « Envoyer la demande », « Supprimer la tournée » — jamais « OK », « Cliquez ici ».

**États par type de bouton**

| Type | Repos | Survol | Appui | Focus clavier | Désactivé |
|---|---|---|---|---|---|
| Principal | `#E80A65`, texte blanc | `#C70653` | `#A10443` | anneau bleu 3 px décalé de 3 px (blanc sur fond bleu) | opacité 60 %, curseur interdit |
| Bleu | `#061E66`, texte blanc | `#061449` | `#04102F` | idem | idem |
| Secondaire (contour) | bordure `#E4E6EE`, texte bleu | bordure et texte bleu marine | fond `#F2F4FB` | idem | idem |
| Discret (texte) | texte bleu souligné | texte rose | texte `#A10443` | idem | idem |
| Danger | `#D1242F`, texte blanc | `#A4161A` | `#8A1115` | idem | idem |
| Clair (sur fond bleu) | blanc, texte bleu | blanc à 90 % | blanc à 80 % | idem | idem |

Chargement : bouton désactivé, libellé « Envoi en cours… ». Icône seule : toujours une **info-bulle** au survol et au focus, en plus de `aria-label`. « Retour » et « Annuler » sont des boutons secondaires.

### Liens

Bleu `navy`, soulignés (`underline underline-offset-2`), survol `brand`, visité `indigo`. Lien externe : icône ↗, `target="_blank" rel="noopener noreferrer"` et mention « nouvelle fenêtre » pour les lecteurs d'écran. Téléchargement : indiquer le format et le poids (« Brochure PDF, 2,4 Mo »).

### Champs de formulaire

```
étiquette : text-sm font-medium text-ink   (+ <span class="text-brand">*</span> si obligatoire)
champ     : mt-2 w-full rounded-xl border border-line bg-white px-4 py-3 text-sm text-ink outline-none transition-colors placeholder:text-[#6A6F85] focus:border-navy focus:ring-2 focus:ring-navy/15
```

- Étiquette visible au-dessus du champ, liée par `for`/`id`. Jamais le placeholder à la place de l'étiquette.
- États : repos (bordure `line`) · focus (bordure bleue + halo) · erreur (bordure `#D1242F` + icône + message rouge sous le champ, `role="alert"`) · succès (bordure `#12855A` + coche) · désactivé (fond `paper`, texte `muted`).
- Message d'erreur : dit ce qui ne va pas et comment corriger, avec un exemple. « Cette adresse e-mail semble incomplète. Exemple : prenom.nom@entreprise.fr ».
- Zone de texte avec compteur « 0 / 1 000 caractères ». Liste déroulante de 4 à 10 choix (au-delà : recherche). Case à cocher 20 px (arrondi 5 px, bleu plein) et radio avec zone tactile 44 px. Interrupteur 44 × 24 px. Date au format JJ/MM/AAAA avec calendrier et saisie clavier. Fichier : zone de dépôt en pointillés avec formats et poids indiqués.
- Mise en page : 1 colonne mobile, 2 colonnes dès 640 px (prénom/nom, e-mail/téléphone). Espacement vertical 20 px entre champs. Bouton principal en bas, aligné à gauche. Mention « * champ obligatoire » en haut. Après envoi : encart « Demande envoyée » centré (pastille rose avec coche, titre Groogla 24 px).

**Compléments formulaires**

| Élément | Règle |
|---|---|
| États d'un champ | Normal · actif (bordure bleue + halo) · rempli · erreur (rouge + icône + message) · validé (vert + coche) · désactivé (fond `paper`, texte gris) · lecture seule (bordure pointillée, pas de halo) |
| Zone de texte longue | Hauteur par défaut 96 px (≈ 4 lignes), redimensionnable en hauteur, compteur « 0 / 1 000 caractères » en bas à droite |
| Liste déroulante | Fermée : champ avec chevron ⌄. Ouverte : panneau blanc arrondi 12 px, ombre moyenne, options de 44 px, survol `navy-50`, choix en gras avec coche. Au-delà de 10 choix : recherche en tête de liste |
| Cases et radios | Alignement **vertical** par défaut (une option par ligne, 12 px d'écart) ; horizontal seulement pour 2 ou 3 options courtes |
| Interrupteur ou case | **Interrupteur** = effet immédiat (activer une notification). **Case** = choix validé à l'envoi du formulaire, ou sélection multiple |
| Date | Calendrier au clic sur l'icône, saisie clavier, format JJ/MM/AAAA, semaine commençant le lundi |
| Fichier | Zone glisser-déposer en pointillés, PDF/JPG/PNG, 10 Mo maximum par fichier, barre de progression rose sous le nom du fichier |

### Cartes

`rounded-2xl border border-line bg-white p-6` · titre Groogla 24 px `navy` · une seule action. Variantes : carte papier (`bg-paper`), carte bleue (`bg-navy text-white`) pour un appel à l'action. Grilles de cartes accolées par un filet : `grid gap-px overflow-hidden rounded-2xl border border-line bg-line`.

**Chiffre clé** : valeur Groogla en rose (`text-brand`) qui passe au bleu marine au survol (`group-hover:text-navy`, 200 ms), légende `muted` dessous (14 px).

### Tableaux de données

En-tête `bg-navy text-white` gras 14 px, arrondi 12 px aux angles ; lignes 44 px minimum, alternance blanc / `paper`, filet 1 px ; statut en badge (texte + couleur) ; action de ligne en bouton petit `ghost`. Ligne survolée ou cochée : fond `navy-50`. Tri : flèche ▲▼ à côté du titre de la colonne triée.

**Organisation** :
1. Case de sélection (si actions groupées).
2. Identifiant ou nom (colonne principale).
3. Informations de contexte (agence, date…).
4. Valeurs chiffrées, alignées à droite, même nombre de décimales.
5. Statut (badge).
6. Actions, toujours en dernière colonne à droite.

Titres de colonnes courts (1 à 2 mots), en-tête fixe au défilement, texte à gauche. Barre d'outils au-dessus : recherche, filtres, export à droite. 25 lignes par page par défaut avec pagination en bas. Maximum 6 à 7 colonnes sur ordinateur (le reste dans la fiche détail). Tableau vide : état vide avec mascotte et action. Sur mobile : chaque ligne devient une carte (identifiant en titre, puis « libellé : valeur », badge et action en bas) ; tri et filtres dans un panneau.

### Messages

- **Alerte dans la page** : icône + titre gras + une phrase ; fond clair et texte foncé de la même teinte (tableau des états), bordure 1 px, arrondi 12 px ; `role="status"` ou `role="alert"`.
- **Toast** : `bg-navy-900 text-white rounded-[14px] shadow`, bas droite (ordinateur) ou bas pleine largeur (mobile), disparaît après 5 s (8 s pour une erreur avec action), reste au survol et au focus, bouton fermer toujours présent.
- **Modale de confirmation** : fond `navy-900/55`, carte blanche arrondie 20 px, 440 px max (plein écran en bas sur mobile). Titre = la question, texte = la conséquence, bouton = verbe de l'action (« Supprimer la tournée »), jamais « OK ». Focus piégé, fermeture par Échap, retour du focus au déclencheur.
- **Badge** : pilule 11 px bold, `px-2.5 py-0.5`, fond et texte de l'état (Nouveau = Platinium/bleu, Priorité = rose clair, Livré = succès, Retard = alerte, Échec = erreur). Toujours un texte.
- **Info-bulle** : fond `navy-900`, texte blanc 12 px, arrondi 8 px, au survol et au focus ; jamais d'information essentielle dedans.
- **Accordéon** : bordure 1 px, arrondi 14 px, titre en gras bleu, chevron.
- **Chargement** : indicateur rond (actions courtes), squelettes (listes et cartes), barre de progression (envois).
- **États vides** : mascotte MySpot + phrase positive + bouton d'action.
- **Pages d'erreur** : 404 « Cette page a changé d'adresse. » · 500 « Un imprévu est survenu. Réessayez dans quelques instants. » · accès refusé « Cette page est réservée. » · maintenance « Petite pause technique. Nous revenons à … ». Surtitre rose « Erreur 404 », titre Groogla 48–60 px, texte `muted`, 2 boutons (principal `dark`, secondaire `ghost`).

### Règles complémentaires des blocs

| Élément | Règle |
|---|---|
| Cartes | Largeur minimale 280 px, image 16:10 en haut, marge 24 px, titre Groogla 24 px, texte court (3 lignes max), 1 bouton ou lien. Carte cliquable : survol fond `navy-50` (200 ms), pas d'ombre |
| Alertes | Icône + titre + phrase. Croix de fermeture pour info et succès ; une erreur reste affichée tant que le problème subsiste |
| Compteurs | Pastille ronde de 20 px minimum, fond rose, texte blanc 11 px gras, « 99+ » au-delà, en haut à droite d'une icône ou d'une entrée de menu |
| Info-bulles | 80 caractères maximum (2 lignes), 240 px de large maximum, apparition après 300 ms au survol et au focus, texte seul sans lien |
| Accordéons | Chevron 20 px qui pivote de 180°, ouverture en 200 ms (hauteur + fondu), plusieurs blocs ouverts possibles |
| Chargement | **Indicateur rond** : action courte (< 3 s). **Squelettes grisés** : listes, cartes, tableaux. **Barre de progression** : envoi de fichier ou opération longue dont l'avancement est connu |
| Aucun résultat | Mascotte MySpot, « Aucun résultat pour « colis » », suggestion (« Vérifiez l'orthographe ») et bouton « Effacer les filtres » |

### Navigation

- **En-tête** : `sticky top-0 z-40 h-[72px] border-b border-line/70 bg-white/90 backdrop-blur-md`. Logo à gauche (24 px de haut), menu en 14 px, entrée active en `brand` (voir surbrillance), bouton d'action unique à droite (`dark`, « Nous contacter »). Sous-menu au survol/focus : `rounded-xl border border-line bg-white p-2 shadow-lg`, éléments `rounded-lg px-4 py-2` avec survol `bg-navy-50 text-brand`.
- **Surbrillance des menus** : menu principal ordinateur au repos `text-ink/70` (14 px), survol et focus `hover:text-brand` (transition 200 ms), page active `text-brand` + `aria-current="page"` (trait rose de 2 px possible dessous). Sous-menu : texte `text-ink/80`, survol `hover:bg-navy-50 hover:text-brand`, arrondi 8 px, apparition 150 ms, ouvert au survol **et** au focus clavier. Menu mobile : appui = fond `bg-navy-50` arrondi 8 px. Menu latéral : survol fond blanc à 5 %, actif fond blanc à 10 % + barre rose 3 px à gauche. La page active ne repose jamais sur la couleur seule (`aria-current` obligatoire).
- **Menu mobile** (< 1024 px) : bouton rond « menu » 40 px avec filet ; panneau blanc sous l'en-tête. Menus principaux en **majuscules** 14 px bold espacées (`tracking-[0.18em]`), en rose pour les rubriques d'offres et en `navy` pour les autres ; sous-menus en `muted` 14 px, sur **2 colonnes**, libellés longs sur plusieurs lignes ; bouton « Nous contacter » en bas. Une rubrique n'apparaît qu'une fois.
- **Menu latéral** (outils internes) : 240 px, fond `navy-900`, texte blanc à 75 %, élément actif fond blanc 10 % + barre rose 3 px à gauche, éléments 44 px, arrondi 10 px ; tiroir sur mobile.
- **Fil d'Ariane** : `Accueil › Nos offres › **Presse**`, 14 px gris, page courante en gras bleu ; sur mobile seulement le niveau parent « ‹ Nos offres ».
- **Onglets** : texte gris, actif en bleu gras avec trait rose 3 px dessous, hauteur 44 px.
- **Pagination** : boutons ronds 44 px, page active bleu plein, « Page 1 sur 12 » pour les lecteurs d'écran.
- **Recherche** : champ pilule 44 px, icône loupe à gauche, bouton effacer à la saisie.
- **Pied de page** : `bg-navy-900 text-white`, slogan Groogla 24 px (18 px mobile) avec flèche « retour en haut » ronde 36 px à droite, 4 colonnes sur ordinateur (marque + réseaux, adresse, offres, entreprise), filet `white/10`, mentions légales / confidentialité / cookies en bas, liens `white/60` → blanc au survol, logos de partenaires en blanc ≈ 101 px.

**Règles de navigation**

| Élément | Règle |
|---|---|
| En-tête | Logo à gauche, menu principal, bouton d'action. Outils internes : recherche, notifications, compte utilisateur (avatar + nom, menu : profil, aide, déconnexion) à droite. 72 px, fond blanc à 90 % avec flou, filet bas, **fixe au défilement** |
| Menu principal | **7 entrées maximum** (6 sur le site actuel), libellés de 1 à 3 mots. Sous-menus déroulants sur 1 niveau, 8 entrées maximum |
| Menu latéral | 240 px ; icône 20 px + libellé 14 px. **Version repliée** : 72 px, icônes seules avec info-bulle, bouton « Réduire » en bas. **2 niveaux maximum** (sous-rubriques décalées de 16 px). Téléphone : tiroir |
| Menu sur téléphone | Bouton rond 40 px, icône « trois traits ». Ouvre un **volet blanc sous l'en-tête** (pas en plein écran). Le même bouton devient une croix « Fermer le menu » ; le volet se referme à chaque navigation |
| Fil d'Ariane | Affiché **dès le 2e niveau**, jamais sur l'accueil. Séparateur ›, 14 px gris, page courante en gras bleu non cliquable. Téléphone : « ‹ Rubrique » seul |
| Onglets | **2 à 6** par page, défilement horizontal sur téléphone, changent la vue sans recharger la page |
| Pagination | « Précédent 1 2 3 … 12 Suivant » pour les tableaux et résultats de plus de 25 lignes. « Voir plus » (bouton secondaire, charge 12 éléments) pour les listes de cartes et sur téléphone |
| Barre de recherche | En-tête (outils) ou haut de liste. Pilule 44 px, 280 px minimum, texte d'aide « Rechercher une tournée, un colis… ». Suggestions sous le champ (5 max) dès 2 caractères ; page de résultats « 12 résultats pour « colis » » ; sans résultat : état vide |
| Pied de page | **Obligatoire** : mentions légales, politique de confidentialité, cookies, contact et adresse, réseaux sociaux. Plan du site au-delà d'une quinzaine de pages |

## 18. Modèles de pages

1. **Accueil** : en-tête · bandeau bleu avec photo assombrie (surtitre rose, h1 Groogla blanc, introduction blanche à 70 %, 2 boutons) · chiffres clés en rose · section métier (photo + texte + bouton) · offres en cartes · appel à l'action bleu · pied de page.
2. **Liste** : bandeau bleu court (titre + intro) · barre de recherche et filtres · tableau ou grille de cartes · pagination · appel à l'action.
3. **Détail** : bandeau bleu (surtitre, titre, intro) · bloc « points clés » · photo + paragraphes · mascotte · liens « précédent / suivant » · appel à l'action.
4. **Formulaire** : bandeau bleu (« Parlons de votre distribution. ») · formulaire (2 colonnes de champs, case de consentement, bouton rose) · encart d'adresse à côté ou dessous.
5. **Connexion** : carte centrée sur fond papier · logo · titre · champ(s) · bouton pleine largeur · phrase de réassurance 12 px.

Chaque modèle doit exister en version ordinateur et mobile.

| Modèle | Profil visé | Objectif de la page | Action principale | À mesurer |
|---|---|---|---|---|
| Accueil | Tous | Faire comprendre Proximy en 10 secondes et orienter | Découvrir nos offres | Clics vers les offres et le contact |
| Liste | Client, candidat, interne | Trouver vite un élément | Ouvrir un élément | Recherches sans résultat, filtres utilisés |
| Détail (offre, métier) | Client, candidat | Convaincre et faire agir | Nous contacter / Postuler | Clics sur l'action principale |
| Formulaire | Client, candidat | Obtenir une demande complète | Envoyer la demande | Envois réussis, abandon par champ |
| Connexion | Interne, client | Entrer sans friction | Se connecter | Erreurs de connexion |

6. **Candidature en étapes** : bandeau court · barre de progression « Étape 2 sur 4 » · un groupe de champs par étape · boutons « Retour » (secondaire) et « Continuer » (principal) · récapitulatif · confirmation avec la suite du processus.
7. **Outil interne (liste + détail)** : menu latéral · barre d'outils (recherche, filtres, export) · tableau · fiche détail en volet ou page · actions groupées · états vide, chargement et erreur prévus.

## 19. Règles transversales : écrans et animations

### Adaptation aux écrans

| Élément | Téléphone | Tablette | Ordinateur |
|---|---|---|---|
| En-tête et menu | logo + bouton menu | logo + bouton menu | menu horizontal complet |
| Menu latéral | tiroir ouvert par un bouton | replié (72 px) | déployé (240 px) |
| Cartes | 1 colonne | 2 colonnes | 3 à 4 colonnes |
| Tableaux | cartes empilées | tableau, colonnes secondaires masquées | tableau complet |
| Formulaires | 1 colonne, bouton pleine largeur | 2 colonnes | 2 colonnes, bouton à gauche |
| Boutons côte à côte | empilés, principal en haut | côte à côte, principal à droite | idem |
| Modales | feuille plein écran en bas | 440 px centrée | 440 px centrée |
| Notifications | bas, pleine largeur | bas droite | bas droite |
| Onglets | défilement horizontal | normaux | normaux |
| Pagination, fil d'Ariane | « Voir plus », « ‹ Rubrique » | complets | complets |

Zones cliquables : 44 × 44 px minimum partout (48 px conseillés sur téléphone), 8 px d'écart.

### Mouvements et animations

Durées : **150 ms** (sous-menu, info-bulle), **200 ms** (couleurs au survol, accordéon, carte cliquable), **300 ms** (modale, tiroir). Autorisés : fondu, glissement de 8 px maximum, rotation d'un chevron. Interdits : rebond, clignotement, défilement automatique, parallaxe, vidéo qui démarre seule avec du son. Toutes les transitions sont supprimées si l'utilisateur demande de réduire les animations (`prefers-reduced-motion`).

# Qualité

## 20. Checklist de fin de tâche

Avant de rendre ton travail, vérifie et indique les écarts éventuels.

**UX**
- [ ] Le profil, le parcours et l'objectif de la page sont identifiés ; **une seule action principale** (bouton rose) par écran, visible sans défiler.
- [ ] Libellés de menus à 1–3 mots, identiques au titre de la page ; contact accessible partout ; pas de page orpheline.
- [ ] Formulaires courts (6 champs maximum), saisie assistée, erreurs utiles (quoi + comment corriger), saisie jamais perdue, confirmation claire avec la suite.
- [ ] États prévus : chargement (squelettes), vide, aucun résultat, erreur, hors ligne, succès, désactivé avec raison.
- [ ] Actions graves confirmées, actions légères annulables ; aucune information essentielle uniquement dans un toast ou une info-bulle.
- [ ] Textes en français, vouvoiement, phrases courtes, micro-copy conforme (pas de « OK ») ; formats de dates, heures, montants, téléphones respectés.
- [ ] Mobile d'abord contrôlé (360 px) ; rien d'accessible uniquement au survol ; performances raisonnables (images optimisées, pas de saut de mise en page).
- [ ] Aucun piège : pas de case précochée, cookies refusables aussi facilement qu'acceptés, pied de page légal présent.
- [ ] Parcours testé de bout en bout, une fois au clavier et une fois sur téléphone.

**UI**
- [ ] Seules les couleurs, polices, arrondis et espacements de la charte sont utilisés (via variables).
- [ ] Contrastes conformes ; aucune information portée par la seule couleur ; aucune zone tactile < 44 px.
- [ ] Focus clavier visible ; un seul h1 ; textes alternatifs ; champs étiquetés.
- [ ] Logo non déformé, bonne version selon le fond ; mascottes uniquement sur fond clair.
- [ ] Composants réutilisés de la section 17 avec tous leurs états.
- [ ] Fonds filigranes décoratifs : un seul par section, texte au contraste conservé.

## Annexe : variables prêtes à coller (Tailwind v4)

```css
@theme {
  --color-brand: #E80A65;      --color-brand-600: #C70653;   --color-brand-700: #A10443;
  --color-brand-50: #FFF1F6;   --color-brand-100: #FFE4EE;
  --color-navy: #061E66;       --color-navy-800: #061449;    --color-navy-900: #04102F;
  --color-navy-50: #F2F4FB;    --color-navy-100: #E2E7F5;
  --color-platinium: #E9E9FF;  --color-indigo: #4B4584;
  --color-ink: #0D1330;        --color-muted: #5B6478;
  --color-line: #E4E6EE;       --color-paper: #F7F7F9;
  --color-success: #12855A;    --color-success-text: #0B6B47; --color-success-bg: #E6F5EE;
  --color-warning: #E0A100;    --color-warning-text: #7A4B00; --color-warning-bg: #FFF3D6;
  --color-danger:  #D1242F;    --color-danger-text:  #A4161A; --color-danger-bg:  #FDE8E8;
  --font-display: "Groogla", Georgia, serif;
  --font-sans: "Century Gothic", ui-sans-serif, sans-serif;
}
.h-display { font-family: var(--font-display); font-weight: 400; line-height: 1.05; letter-spacing: -0.015em; }
.eyebrow { font-size: .75rem; font-weight: 700; line-height: 1; letter-spacing: .18em; text-transform: uppercase; color: var(--color-brand); }
h1, h2, h3 { color: var(--color-navy); }
```
