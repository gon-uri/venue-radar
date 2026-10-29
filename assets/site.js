function initializeMobileCards() {
  // The filter panel's responsive default is set by an inline script right
  // after the panel, before first paint, to avoid a mobile layout shift.
  document.querySelectorAll('[data-filter-row]').forEach((row) => {
    const button = row.querySelector('.mobile-info-toggle');
    const view = row.hasAttribute('data-deadline-group') ? 'deadlines' : 'conferences';
    const detailIds = [...row.querySelectorAll('.mobile-detail')].map((cell, index) => {
      cell.id = `${view}-${row.dataset.edition}-detail-${index}`;
      return cell.id;
    });
    row.dataset.mobileExpanded = 'false';
    button.setAttribute('aria-controls', detailIds.join(' '));
    button.addEventListener('click', () => {
      const expanded = row.dataset.mobileExpanded !== 'true';
      row.dataset.mobileExpanded = String(expanded);
      button.setAttribute('aria-expanded', String(expanded));
      const label = expanded ? 'Less info' : 'More info';
      button.querySelector('[data-mobile-info-label]').textContent = label;
      button.setAttribute('aria-label', `${label} for ${row.querySelector('a').textContent.trim()}`);
    });
  });
  document.documentElement.classList.add('mobile-cards-ready');
}

function syncTopicParents() {
  document.querySelectorAll('[data-family-toggle]').forEach((parent) => {
    const children = [...document.querySelectorAll(`[data-topic-family="${parent.dataset.familyToggle}"]`)];
    const selected = children.filter((child) => child.checked).length;
    parent.checked = selected === children.length;
    parent.indeterminate = selected > 0 && selected < children.length;
  });
}

// Selected families and leaves, read once per filter pass.
function topicFilterContext() {
  const families = new Map();
  document.querySelectorAll('[data-topic-family]:checked').forEach((input) => {
    const group = families.get(input.dataset.topicFamily) || [];
    group.push(input.value);
    families.set(input.dataset.topicFamily, group);
  });
  return {
    entries: [...families.entries()].map(([family, leaves]) => ({
      family,
      leaves,
      whole: document.querySelector(`[data-family-toggle="${family}"]`).checked,
    })),
    all: document.querySelector('#topic-match').value === 'all',
  };
}

// Whole families match central identities; partial selections match the
// curated topic union (ADR-030). `cache` holds the row's parsed sets.
function venueTopicMatch(row, context = topicFilterContext(), cache = null) {
  if (!context.entries.length) return true;
  const topics = cache ? cache.topics : new Set(row.dataset.topics.split(' '));
  const centralFamilies = cache ? cache.families : new Set((row.dataset.families || '').split(' '));
  const matches = context.entries.map(({family, leaves, whole}) => (
    whole ? centralFamilies.has(family) : leaves.some((topic) => topics.has(topic))
  ));
  return context.all ? matches.every(Boolean) : matches.some(Boolean);
}

function feedUrls(path) {
  const base = document.querySelector('#calendar-menu')?.dataset.siteUrl || location.href;
  const https = new URL(path, base).href;
  const webcal = https.replace(/^https:/, 'webcal:');
  return {https, webcal, google: `https://calendar.google.com/calendar/render?cid=${webcal}`};
}

function setFeedActions(actions, path) {
  const urls = feedUrls(path);
  actions.querySelector('[data-feed-google]').href = urls.google;
  actions.querySelector('[data-feed-webcal]').href = urls.webcal;
  actions.querySelector('[data-feed-download]').setAttribute('href', path);
  actions.querySelector('[data-copy-feed]').dataset.copyFeed = urls.https;
}

async function copyFeedLink(button) {
  const url = button.dataset.copyFeed;
  const original = button.dataset.label || (button.dataset.label = button.textContent);
  try {
    await navigator.clipboard.writeText(url);
    button.textContent = 'Copied';
  } catch (error) {
    window.prompt('Copy this calendar address:', url);
  }
  setTimeout(() => { button.textContent = original; }, 2000);
}

function initializeCalendarMenu() {
  const menu = document.querySelector('#calendar-menu');
  if (!menu) return;
  let opener = null;
  const syncPickers = () => menu.querySelectorAll('[data-feed-select]').forEach((select) => {
    setFeedActions(select.closest('.feed-row').querySelector('[data-feed-actions]'), select.value);
  });
  menu.querySelectorAll('[data-feed-select]').forEach((select) => {
    select.addEventListener('change', syncPickers);
  });
  // Browsers restore <select> values after scripts run on back/forward
  // navigation; re-sync the links so they always match the visible choice.
  window.addEventListener('pageshow', syncPickers);
  menu.querySelectorAll('[data-copy-feed]').forEach((button) => {
    button.addEventListener('click', () => copyFeedLink(button));
  });
  const closeMenu = (returnFocus) => {
    menu.open = false;
    const target = opener && opener.isConnected ? opener : menu.querySelector('summary');
    opener = null;
    if (returnFocus) target.focus();
  };
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.open) closeMenu(menu.contains(document.activeElement));
  });
  // Close when keyboard focus leaves, so the panel never covers focused controls.
  menu.addEventListener('focusout', (event) => {
    if (menu.open && event.relatedTarget && !menu.contains(event.relatedTarget)) closeMenu(false);
  });
  menu.addEventListener('toggle', () => {
    if (!menu.open) opener = null;
  });
  document.addEventListener('click', (event) => {
    if (menu.open && !menu.contains(event.target)) closeMenu(false);
  });
  // A row's "Series" link opens the menu with that series selected; without
  // JavaScript it simply downloads the series feed.
  document.querySelectorAll('[data-subscribe-series]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const select = menu.querySelector('#feed-series');
      const option = select.querySelector(`[data-series-slug="${link.dataset.subscribeSeries}"]`);
      if (!option) return;
      event.preventDefault();
      event.stopPropagation();
      select.value = option.value;
      select.dispatchEvent(new Event('change'));
      menu.open = true;
      opener = link;
      menu.scrollIntoView({block: 'nearest'});
      select.focus({preventScroll: true});
    });
  });
}

let conferenceMap;
let cityMarkers;
let lastMapSignature;
const worldMapBounds = [[-60, -180], [80, 180]];

function resetConferenceMap() {
  conferenceMap.closePopup();
  conferenceMap.fitBounds(worldMapBounds, {padding: [12, 12], animate: false});
}

let mapUnavailable = false;

function showMapUnavailable() {
  mapUnavailable = true;
  document.querySelector('#conference-map').hidden = true;
  const message = document.querySelector('#map-empty');
  message.textContent = 'The map could not load; the table below lists every conference.';
  message.hidden = false;
}

function updateConferenceMap() {
  // Leaflet loads after the page logic; the map is drawn once it exists.
  if (document.querySelector('#panel-conferences').hidden || mapUnavailable || !window.L) return;
  try {
    drawConferenceMap();
  } catch (error) {
    showMapUnavailable();
  }
}

function drawConferenceMap() {
  if (!conferenceMap) {
    const animate = !matchMedia('(prefers-reduced-motion: reduce)').matches;
    conferenceMap = L.map('conference-map', {
      crs: L.CRS.EPSG4326, minZoom: -1, maxZoom: 7, zoomSnap: .25,
      scrollWheelZoom: false, worldCopyJump: false,
      zoomAnimation: animate, fadeAnimation: animate, markerZoomAnimation: animate,
      // Leave enough room for popup auto-pan at the full-world zoom.
      maxBounds: [[-180, -360], [180, 360]], maxBoundsViscosity: .8,
    }).fitBounds(worldMapBounds, {padding: [12, 12]});
    L.geoJSON(venueMapData.land, {interactive: false, style: {
      color: '#bdccce', weight: .7, fillColor: '#e3ebeb', fillOpacity: 1,
    }}).addTo(conferenceMap);
    conferenceMap.attributionControl.addAttribution('Land: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');
    cityMarkers = L.layerGroup().addTo(conferenceMap);
    conferenceMap.on('resize', resetConferenceMap);
    const reset = L.control({position: 'topleft'});
    reset.onAdd = () => {
      const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control-reset');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'leaflet-reset-world';
      button.title = 'Reset world view';
      button.setAttribute('aria-label', 'Reset world view');
      button.innerHTML = venueMapData.resetIcon;
      button.addEventListener('click', resetConferenceMap);
      container.append(button);
      L.DomEvent.disableClickPropagation(container);
      return container;
    };
    reset.addTo(conferenceMap);
  }
  conferenceMap.invalidateSize();
  const now = Date.now();
  const visibleIds = new Set([...document.querySelectorAll('[data-conference-row]')]
    .filter((row) => !row.hidden).map((row) => row.dataset.edition));
  const events = venueMapData.events.filter((event) =>
    Date.parse(`${event.start}T00:00:00Z`) > now && visibleIds.has(event.id));
  const signature = events.map((event) => event.id).join('|');
  if (signature === lastMapSignature) return;
  lastMapSignature = signature;
  cityMarkers.clearLayers();
  const byCity = new Map();
  events.forEach((event) => {
    const group = byCity.get(event.city) || [];
    group.push(event);
    byCity.set(event.city, group);
  });
  const list = document.querySelector('#map-cities');
  list.replaceChildren();
  byCity.forEach((group) => {
    const city = group[0];
    const popup = document.createElement('div');
    popup.className = 'city-popup';
    const heading = document.createElement('strong');
    heading.textContent = city.label;
    popup.append(heading);
    const entries = document.createElement('ul');
    group.forEach((event) => {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = event.url;
      link.textContent = event.title;
      const dates = document.createElement('time');
      dates.dateTime = event.start;
      const formatter = new Intl.DateTimeFormat('en', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'});
      dates.textContent = `${formatter.format(new Date(event.start))} - ${formatter.format(new Date(event.end))}`;
      item.append(link, dates);
      entries.append(item);
    });
    popup.append(entries);
    const marker = L.marker([city.lat, city.lon], {keyboard: true,
      title: `${city.label}: ${group.map((event) => event.title).join(', ')}`,
      alt: `${city.label}, ${group.length} upcoming conference${group.length === 1 ? '' : 's'}`,
      icon: L.divIcon({className: 'city-marker', iconSize: [12, 12], iconAnchor: [6, 6]}),
    }).bindPopup(popup, {maxWidth: 290, maxHeight: 180, autoPanPadding: [12, 12]}).addTo(cityMarkers);
    marker.on('mouseover', () => marker.openPopup());
    marker.on('add', () => {
      marker.getElement().setAttribute('aria-label', marker.options.alt);
    });
    marker.getElement()?.setAttribute('aria-label', marker.options.alt);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'map-city-link';
    button.textContent = `${city.label} (${group.length})`;
    button.addEventListener('click', () => {
      conferenceMap.setView(marker.getLatLng(), Math.max(3, conferenceMap.getZoom()), {animate: false});
      marker.openPopup();
    });
    list.append(button);
  });
  document.querySelector('#map-count').textContent = `${events.length} confirmed editions in ${byCity.size} cities`;
  document.querySelector('#map-empty').hidden = events.length > 0;
}

function loadCommunityComments() {
  if (document.querySelector('.giscus script')) return;
  const script = document.createElement('script');
  script.src = 'https://giscus.app/client.js';
  const settings = {
    repo: 'gon-uri/venue-radar', 'repo-id': 'R_kgDOTQKmZg',
    category: 'Announcements', 'category-id': 'DIC_kwDOTQKmZs4DHLTi',
    mapping: 'specific', term: 'Venue Radar community', strict: '1',
    'reactions-enabled': '1', 'emit-metadata': '0', 'input-position': 'top',
    theme: 'light', lang: 'en', loading: 'lazy',
  };
  Object.entries(settings).forEach(([key, value]) => script.setAttribute(`data-${key}`, value));
  script.crossOrigin = 'anonymous';
  script.async = true;
  const container = document.querySelector('.giscus');
  const fallback = () => {
    if (container.querySelector('iframe, .giscus-fallback')) return;
    const link = document.createElement('a');
    link.className = 'giscus-fallback';
    link.href = 'https://github.com/gon-uri/venue-radar/discussions';
    link.textContent = 'Comments could not load here; join the discussion on GitHub.';
    container.append(link);
  };
  script.addEventListener('error', fallback);
  setTimeout(fallback, 10000);
  container.append(script);
}
