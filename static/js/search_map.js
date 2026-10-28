/*
 * MediFind search page script.
 *
 * 1. "Use my location" button: asks the browser for the customer's position,
 *    puts it in the hidden lat/lng inputs and re-runs the search.
 * 2. Results map: shows a pin for each pharmacy in the results plus a blue
 *    dot for the customer. The data comes from Django via json_script.
 *
 * The server validates lat/lng again; this script is only a helper.
 */
(function () {
  "use strict";

  const form = document.getElementById("search-form");
  if (!form) {
    return;
  }
  const latInput = form.querySelector('[name="lat"]');
  const lngInput = form.querySelector('[name="lng"]');
  const nearSelect = form.querySelector('[name="near"]');
  const statusText = document.getElementById("location-status");

  // ----- 1. Location -----

  // Choosing an area from "Near" means: stop using the GPS position.
  nearSelect.addEventListener("change", function () {
    latInput.value = "";
    lngInput.value = "";
  });

  document.getElementById("use-my-location").addEventListener("click", function () {
    if (!navigator.geolocation) {
      statusText.textContent = "Your browser cannot share its location. Choose an area under 'Near'.";
      return;
    }
    statusText.textContent = "Finding your location…";
    navigator.geolocation.getCurrentPosition(
      function (position) {
        latInput.value = position.coords.latitude.toFixed(6);
        lngInput.value = position.coords.longitude.toFixed(6);
        form.submit(); // search again, now measuring from the customer's position
      },
      function (error) {
        if (error.code === error.PERMISSION_DENIED) {
          statusText.textContent =
            "Location permission is blocked. Allow it in your browser settings, or choose an area under 'Near'.";
        } else {
          statusText.textContent = "Could not get your location. Choose an area under 'Near' instead.";
        }
      },
      { timeout: 15000 }
    );
  });

  // ----- 2. Results map -----

  const mapElement = document.getElementById("results-map");
  const dataElement = document.getElementById("map-data");
  if (!mapElement || !dataElement) {
    return; // no results, so no map
  }
  const data = JSON.parse(dataElement.textContent);

  const map = L.map(mapElement);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    // Required by OSM's tile policy (see location_picker.js for details).
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(map);

  const points = [];

  // Blue dot: where distances are measured from.
  const userPoint = [data.user.lat, data.user.lng];
  L.circleMarker(userPoint, { radius: 8, color: "#0d6efd", fillOpacity: 0.8 })
    .addTo(map)
    .bindPopup(textPopup(data.user.label));
  points.push(userPoint);

  // One pin per pharmacy.
  data.pharmacies.forEach(function (pharmacy) {
    const point = [pharmacy.lat, pharmacy.lng];
    L.marker(point).addTo(map).bindPopup(pharmacyPopup(pharmacy));
    points.push(point);
  });

  // Zoom so that every pin is visible.
  map.fitBounds(points, { padding: [30, 30], maxZoom: 15 });

  // Popups are built with textContent, never innerHTML, so a pharmacy
  // name containing HTML cannot inject code into the page.
  function textPopup(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div;
  }

  function pharmacyPopup(pharmacy) {
    const div = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = pharmacy.name;
    const distance = document.createElement("div");
    distance.textContent = pharmacy.distance + " km away";
    const link = document.createElement("a");
    link.href = pharmacy.url;
    link.textContent = "View pharmacy";
    div.append(name, distance, link);
    return div;
  }
})();
