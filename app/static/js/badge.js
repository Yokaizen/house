// Badgeage : demande la position au moment du clic uniquement, l'envoie au
// serveur qui ne renvoie (et ne conserve) que le résultat du contrôle de zone.
(function () {
  "use strict";
  // Heure affichée dans le fuseau du serveur (celui des badgeages), quel que soit l'appareil.
  var FUSEAU = window.FUSEAU || "Europe/Paris";
  var ZONES = {
    dans_zone: "Vous êtes dans la zone d'un lieu de travail autorisé.",
    hors_zone: "Vous n'êtes pas dans la zone d'un lieu de travail autorisé. Le badgeage est enregistré avec la mention « hors zone ».",
    indetermine: "Votre position est trop imprécise pour être vérifiée. Le badgeage est enregistré avec la mention « indéterminé ».",
    indisponible: "Position non transmise. Le badgeage est enregistré avec la mention « position refusée »."
  };

  function horloge() {
    var d = new Date();
    var h = document.getElementById("horloge");
    if (!h) return;
    h.textContent = d.toLocaleTimeString("fr-FR", { timeZone: FUSEAU, hour: "2-digit", minute: "2-digit" });
    document.getElementById("date-jour").textContent = d.toLocaleDateString("fr-FR",
      { timeZone: FUSEAU, weekday: "long", day: "numeric", month: "long", year: "numeric" });
  }
  horloge();
  setInterval(horloge, 10000);

  var bouton = document.getElementById("bouton-badge");
  var statut = document.getElementById("statut");
  if (!bouton) return;

  function appareil() {
    var ua = navigator.userAgent || "";
    var ipad = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;
    return (/Mobi|Android|iPhone|iPad/i.test(ua) || ipad) ? "mobile" : "ordinateur";
  }

  function envoyer(position) {
    var corps = { type: bouton.dataset.type, appareil: appareil() };
    if (position) {
      corps.latitude = position.coords.latitude;
      corps.longitude = position.coords.longitude;
      corps.precision = position.coords.accuracy;
    }
    statut.textContent = "Enregistrement…";
    fetch("/api/badger", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": window.CSRF, "Accept": "application/json" },
      body: JSON.stringify(corps)
    }).then(function (r) {
      return r.json().then(function (data) { return { ok: r.ok, statut: r.status, data: data }; });
    }).then(function (res) {
      if (res.statut === 401) { window.location.href = "/connexion"; return; }
      if (!res.ok) { throw new Error(res.data.erreur || "Erreur lors de l'enregistrement."); }
      var libelle = res.data.type === "entree" ? "Arrivée enregistrée" : "Départ enregistré";
      statut.innerHTML = "";
      var titre = document.createElement("strong");
      titre.textContent = libelle + " à " + res.data.heure + ".";
      var detail = document.createElement("div");
      detail.className = "discret";
      detail.textContent = ZONES[res.data.zone] || "";
      statut.appendChild(titre);
      statut.appendChild(detail);
      bouton.hidden = true;
      setTimeout(function () { window.location.reload(); }, 4000);
    }).catch(function (e) {
      statut.textContent = e.message || "Connexion au serveur impossible. Réessayez.";
      bouton.disabled = false;
    });
  }

  bouton.addEventListener("click", function () {
    bouton.disabled = true;
    if (!navigator.geolocation || !window.isSecureContext) {
      envoyer(null);
      return;
    }
    statut.textContent = "Vérification de votre position…";
    // Si la demande d'autorisation reste sans réponse, le navigateur ne rappelle jamais :
    // au bout de 30 s, le badgeage part sans position plutôt que de rester bloqué.
    var envoye = false;
    function une_fois(pos) {
      if (envoye) return;
      envoye = true;
      clearTimeout(garde);
      envoyer(pos);
    }
    var garde = setTimeout(function () { une_fois(null); }, 30000);
    navigator.geolocation.getCurrentPosition(
      function (pos) { une_fois(pos); },
      function () { une_fois(null); },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
    );
  });
})();
