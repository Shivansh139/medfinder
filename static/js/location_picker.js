/*
 * MediFind location picker (uses Leaflet + OpenStreetMap).
 *
 * It looks for a <div id="location-map"> on the page and reads settings
 * from its data- attributes:
 *   data-lat, data-lng   saved location (empty if not set yet)
 *   data-editable        "true" on the profile form, "false" on the dashboard
 *
 * In editable mode it keeps the latitude/longitude form inputs
 * (#id_latitude, #id_longitude) in sync with the marker.
 * The server still validates the values; this script is only a helper.
 */
(function () {
  "use strict";

  const mapElement = document.getElementById("location-map");
  if (!mapElement) {
    return; // no map on this page
  }

  // Centre of India and a zoom that shows the whole country.
  const DEFAULT_CENTER = [20.5937, 78.9629];
  const DEFAULT_ZOOM = 5;
  // Zoom close enough to see individual streets.
  const STREET_ZOOM = 16;

  const editable = mapElement.dataset.editable === "true";
  const savedLat = parseFloat(mapElement.dataset.lat);
  const savedLng = parseFloat(mapElement.dataset.lng);
  const hasSavedLocation = !isNaN(savedLat) && !isNaN(savedLng);

  // 1. Create the map.
  const map = L.map(mapElement).setView(
    hasSavedLocation ? [savedLat, savedLng] : DEFAULT_CENTER,
    hasSavedLocation ? STREET_ZOOM : DEFAULT_ZOOM
  );

  // 2. Add the OpenStreetMap tiles (the map pictures).
  //    The attribution credit is required by OpenStreetMap's licence.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    // OSM's tile usage policy requires each tile request to say which site
    // it comes from (the HTTP "Referer" header). Django's default policy
    // ("same-origin") removes it, and OSM then blocks the tiles.
    // This sends only our site's address (e.g. http://localhost:8000/),
    // never the full page path, and only for map tiles.
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(map);

  let marker = null;

  // Read-only mode (dashboard): just show the marker and stop.
  if (!editable) {
    if (hasSavedLocation) {
      L.marker([savedLat, savedLng]).addTo(map);
    }
    return;
  }

  // ----- Everything below is for the editable profile form -----

  const latInput = document.getElementById("id_latitude");
  const lngInput = document.getElementById("id_longitude");
  const statusText = document.getElementById("location-status");

  // Put the marker at `latlng` and copy the numbers into the form inputs.
  function setLocation(latlng, recenter) {
    // The database stores 6 decimal places (about 10 cm), so round to that.
    latInput.value = latlng.lat.toFixed(6);
    lngInput.value = latlng.lng.toFixed(6);

    if (marker) {
      marker.setLatLng(latlng);
    } else {
      // draggable: the user can drag the pin to fine-tune the position.
      marker = L.marker(latlng, { draggable: true }).addTo(map);
      marker.on("dragend", function () {
        setLocation(marker.getLatLng().wrap(), false);
      });
    }

    if (recenter) {
      map.setView(latlng, STREET_ZOOM);
    }
  }

  // Show the saved location (if any) as a draggable marker.
  if (hasSavedLocation) {
    setLocation(L.latLng(savedLat, savedLng), false);
  }

  // 3. Clicking on the map moves the marker there.
  //    wrap() keeps longitude between -180 and 180 if the map was scrolled sideways.
  map.on("click", function (event) {
    setLocation(event.latlng.wrap(), false);
  });

  // 4. Typing numbers by hand moves the marker too.
  function onInputChange() {
    const lat = parseFloat(latInput.value);
    const lng = parseFloat(lngInput.value);
    if (!isNaN(lat) && !isNaN(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
      setLocation(L.latLng(lat, lng), true);
    }
  }
  latInput.addEventListener("change", onInputChange);
  lngInput.addEventListener("change", onInputChange);

  // 5. "Use my current location" button (browser geolocation, free, no API key).
  //    The browser asks the user for permission first.
  const locateButton = document.getElementById("use-my-location");
  locateButton.addEventListener("click", function () {
    if (!navigator.geolocation) {
      statusText.textContent = "Your browser cannot share its location.";
      return;
    }
    statusText.textContent = "Finding your location…";
    navigator.geolocation.getCurrentPosition(
      function (position) {
        setLocation(L.latLng(position.coords.latitude, position.coords.longitude), true);
        statusText.textContent = "Location found. Drag the pin if it is not exact.";
      },
      function (error) {
        // The browser tells us WHY it failed with an error code.
        if (error.code === error.PERMISSION_DENIED) {
          statusText.textContent =
            "Location permission is blocked. Allow location for this site in your " +
            "browser settings (padlock icon next to the address), or click the map instead.";
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          statusText.textContent =
            "Your device could not find its location. Check that location services " +
            "are turned on, or click the map instead.";
        } else {
          statusText.textContent = "Finding your location took too long. Try again, or click the map instead.";
        }
      },
      // Give up after 15 seconds instead of waiting forever.
      { timeout: 15000 }
    );
  });

  // 6. "Clear location" button removes the marker and empties the inputs.
  const clearButton = document.getElementById("clear-location");
  clearButton.addEventListener("click", function () {
    if (marker) {
      map.removeLayer(marker);
      marker = null;
    }
    latInput.value = "";
    lngInput.value = "";
    statusText.textContent = "Location cleared. Save to confirm.";
  });
})();
