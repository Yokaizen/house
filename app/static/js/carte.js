// Positionnement d'un lieu (établissement ou domicile) sur une carte OpenStreetMap.
(function () {
  "use strict";
  var script = document.currentScript;
  var champLat = document.getElementById(script.dataset.lat);
  var champLon = document.getElementById(script.dataset.lon);
  var champRayon = document.getElementById(script.dataset.rayon);
  var rayonDefaut = parseInt(script.dataset.rayonDefaut, 10) || 100;
  var resultat = document.getElementById("geocodage-resultat");

  function nombre(champ) { var v = parseFloat((champ.value || "").replace(",", ".")); return isNaN(v) ? null : v; }
  function rayon() { return (champRayon && parseInt(champRayon.value, 10)) || rayonDefaut; }

  var carte = null, repere = null, cercle = null;
  if (window.L) {
    var lat = nombre(champLat), lon = nombre(champLon);
    carte = L.map("carte").setView(lat !== null ? [lat, lon] : [48.86, 2.35], lat !== null ? 16 : 9);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; contributeurs OpenStreetMap"
    }).addTo(carte);
    if (lat !== null) placer(lat, lon, false);
    carte.on("click", function (e) { placer(e.latlng.lat, e.latlng.lng, true); });
  } else {
    document.getElementById("carte").innerHTML = "<p class='discret' style='padding:12px'>Carte indisponible : saisissez la latitude et la longitude.</p>";
  }

  function placer(lat, lon, majChamps) {
    if (majChamps) { champLat.value = lat.toFixed(6); champLon.value = lon.toFixed(6); }
    if (!carte) return;
    if (!repere) {
      repere = L.marker([lat, lon], { draggable: true }).addTo(carte);
      repere.on("dragend", function () { var p = repere.getLatLng(); placer(p.lat, p.lng, true); });
      cercle = L.circle([lat, lon], { radius: rayon(), color: "#E80A65", fillColor: "#E80A65", fillOpacity: 0.12 }).addTo(carte);
    } else {
      repere.setLatLng([lat, lon]); cercle.setLatLng([lat, lon]);
    }
    cercle.setRadius(rayon());
  }

  [champLat, champLon].forEach(function (c) {
    c.addEventListener("change", function () {
      var lat = nombre(champLat), lon = nombre(champLon);
      if (lat !== null && lon !== null) { placer(lat, lon, false); carte && carte.setView([lat, lon], 16); }
    });
  });
  if (champRayon) champRayon.addEventListener("input", function () { cercle && cercle.setRadius(rayon()); });

  var bouton = document.getElementById("geocoder");
  if (bouton) bouton.addEventListener("click", function () {
    var val = function (id) { var e = document.getElementById(id); return e ? e.value.trim() : ""; };
    var adresse = [val("adresse_numero"), val("adresse_voie"), val("code_postal"), val("ville")].filter(Boolean).join(" ");
    if (adresse.length < 5) { resultat.textContent = "Renseignez l'adresse avant de la localiser."; return; }
    resultat.textContent = "Recherche…";
    fetch("/admin/api/geocoder?adresse=" + encodeURIComponent(adresse) + "&code_postal=" + encodeURIComponent(val("code_postal")),
          { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.trouve) { resultat.textContent = "Adresse introuvable : placez le lieu sur la carte."; return; }
        resultat.textContent = "Trouvé : " + d.libelle + (d.score < 0.7 ? " (confiance faible, vérifiez sur la carte)" : "");
        placer(d.latitude, d.longitude, true);
        carte && carte.setView([d.latitude, d.longitude], 17);
      })
      .catch(function () { resultat.textContent = "Service de localisation indisponible."; });
  });
})();
