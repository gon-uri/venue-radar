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
    // Land colours come from the CSS tokens, so the map follows the colour scheme (ADR-057).
    const landStyle = () => {
      const tokens = getComputedStyle(document.documentElement);
      return {color: tokens.getPropertyValue('--map-coast').trim(), weight: .7,
        fillColor: tokens.getPropertyValue('--map-land').trim(), fillOpacity: 1};
    };
    const land = L.geoJSON(venueMapData.land, {interactive: false, style: landStyle}).addTo(conferenceMap);
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => land.setStyle(landStyle()));
    document.addEventListener('venue-radar:themechange', () => land.setStyle(landStyle()));
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
  // ADR-061: the index beside the map groups cities by region, busiest first.
  const regionOrder = ['Europe', 'North America', 'Asia', 'South America', 'Oceania', 'Africa'];
  const regionLists = new Map();
  regionOrder.forEach((region) => {
    const section = document.createElement('div');
    section.className = 'city-group';
    section.setAttribute('role', 'group');
    const head = document.createElement('div');
    head.className = 'city-group-head';
    section.append(head);
    regionLists.set(region, section);
  });
  const ordered = [...byCity.values()].sort((left, right) =>
    right.length - left.length || left[0].label.localeCompare(right[0].label));
  ordered.forEach((group) => {
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
    const parts = city.label.split(', ');
    const name = document.createElement('span');
    name.className = 'city-name';
    name.textContent = parts[0];
    const country = document.createElement('span');
    country.className = 'city-country';
    country.textContent = parts.length > 1 ? parts[parts.length - 1] : '';
    const count = document.createElement('span');
    count.className = 'city-count';
    count.textContent = String(group.length);
    button.append(name, country, count);
    button.setAttribute('aria-label', `${city.label}, ${group.length} upcoming conference${group.length === 1 ? '' : 's'}`);
    button.dataset.search = normalizeSearch(city.label);
    button.addEventListener('click', () => {
      conferenceMap.setView(marker.getLatLng(), Math.max(3, conferenceMap.getZoom()), {animate: false});
      marker.openPopup();
    });
    const highlight = (on) => marker.getElement()?.classList.toggle('is-hot', on);
    button.addEventListener('mouseenter', () => highlight(true));
    button.addEventListener('mouseleave', () => highlight(false));
    button.addEventListener('focus', () => highlight(true));
    button.addEventListener('blur', () => highlight(false));
    (regionLists.get(city.region) || regionLists.get('Europe')).append(button);
  });
  regionLists.forEach((section, region) => {
    const cities = section.querySelectorAll('.map-city-link').length;
    if (!cities) return;
    section.firstChild.textContent = region;
    const n = document.createElement('span');
    n.textContent = ` ${cities}`;
    section.firstChild.append(n);
    section.setAttribute('aria-label', `${region}, ${cities} cit${cities === 1 ? 'y' : 'ies'}`);
    list.append(section);
  });
  document.querySelector('#city-filter').placeholder = `Filter ${byCity.size} cit${byCity.size === 1 ? 'y' : 'ies'}`;
  document.querySelector('#city-index-label').dataset.count = String(byCity.size);
  filterCityIndex();
  syncCityIndexLabel();
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

// Instant tooltips for [data-tip] (ADR-047): native `title` tips wait about a
// second, some embedded browsers never draw them, and phones have no hover.
// One shared bubble opens on hover, keyboard focus or tap, follows its target
// while the page scrolls, and closes on Escape, a tap elsewhere or leaving.
function initializeTips() {
  const bubble = document.createElement('div');
  bubble.className = 'tip-bubble';
  bubble.id = 'tip-bubble';
  bubble.setAttribute('role', 'tooltip');
  bubble.hidden = true;
  document.body.append(bubble);
  let owner = null;
  const hide = () => {
    if (!owner) return;
    owner.removeAttribute('aria-describedby');
    owner = null;
    bubble.hidden = true;
  };
  const place = () => {
    const margin = 8;
    const box = owner.getBoundingClientRect();
    if (box.bottom < 0 || box.top > window.innerHeight) { hide(); return; }
    const width = bubble.offsetWidth;
    const height = bubble.offsetHeight;
    const left = Math.min(Math.max(margin, box.left + box.width / 2 - width / 2), window.innerWidth - width - margin);
    const below = box.bottom + 6;
    const top = below + height + margin > window.innerHeight && box.top - height - 6 > margin ? box.top - height - 6 : below;
    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;
  };
  const show = (target) => {
    if (owner === target) return;
    hide();
    owner = target;
    bubble.textContent = target.dataset.tip;
    bubble.hidden = false;
    target.setAttribute('aria-describedby', bubble.id);
    place();
  };
  const tipFor = (event) => event.target.closest?.('[data-tip]');
  document.addEventListener('mouseover', (event) => { const target = tipFor(event); if (target) show(target); });
  document.addEventListener('mouseout', (event) => {
    const target = tipFor(event);
    if (target && target === owner && !target.contains(event.relatedTarget) && document.activeElement !== target) hide();
  });
  document.addEventListener('focusin', (event) => { const target = tipFor(event); if (target) show(target); });
  document.addEventListener('focusout', (event) => { if (tipFor(event) === owner) hide(); });
  document.addEventListener('click', (event) => { const target = tipFor(event); if (target) show(target); else hide(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') hide(); });
  window.addEventListener('scroll', () => { if (owner) place(); }, {passive: true, capture: true});
  window.addEventListener('resize', hide);
}

// ADR-058: from 1200px the filters form a left rail. Its controls are the
// existing More filters panel, so the panel is opened (its summary is hidden
// by CSS); below 1200px the ADR-049 bar and collapsed panel are unchanged.
(() => {
  const rail = matchMedia('(min-width: 1200px)');
  const details = document.querySelector('#filter-details');
  if (!details) return;
  let openedByRail = false;
  const sync = () => {
    if (rail.matches && !details.open) { details.open = true; openedByRail = true; }
    else if (!rail.matches && openedByRail) { details.open = false; openedByRail = false; }
  };
  sync();
  rail.addEventListener('change', sync);
})();

// ADR-059: a three-way colour theme (system, light, dark), remembered per
// browser. The head script applies a saved choice before the first paint.
(() => {
  const button = document.querySelector('#theme-toggle');
  if (!button) return;
  const order = ['system', 'light', 'dark'];
  const describe = {system: 'follows your system', light: 'light', dark: 'dark'};
  const current = () => document.documentElement.dataset.theme || 'system';
  const show = (choice) => {
    const next = order[(order.indexOf(choice) + 1) % order.length];
    button.dataset.themeChoice = choice;
    button.title = `Colour theme: ${describe[choice]}`;
    button.setAttribute('aria-label', `Colour theme: ${describe[choice]}. Switch to ${describe[next]}`);
  };
  show(current());
  button.addEventListener('click', () => {
    const choice = order[(order.indexOf(current()) + 1) % order.length];
    if (choice === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = choice;
    try {
      if (choice === 'system') localStorage.removeItem('venue-radar:theme');
      else localStorage.setItem('venue-radar:theme', choice);
    } catch (error) { /* private mode: the choice lasts for this page only */ }
    show(choice);
    document.dispatchEvent(new Event('venue-radar:themechange'));
  });
})();

// ADR-059: "/" jumps to search unless the reader is typing somewhere.
document.addEventListener('keydown', (event) => {
  if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey || event.defaultPrevented) return;
  const target = event.target;
  if (target.closest?.('input, textarea, select, [contenteditable=""], [contenteditable="true"]')) return;
  const search = document.querySelector('#search');
  if (!search || !search.offsetParent) return;
  event.preventDefault();
  search.focus();
  search.select();
});

// ADR-059: the 1200px+ rail can collapse to a strip, remembered per browser.
// The strip shows how many filters are active.
(() => {
  const button = document.querySelector('#rail-toggle');
  const count = document.querySelector('#rail-count');
  if (!button) return;
  const setCollapsed = (collapsed, remember) => {
    document.body.classList.toggle('rail-collapsed', collapsed);
    button.setAttribute('aria-expanded', String(!collapsed));
    button.title = collapsed ? 'Show filters' : 'Hide filters';
    button.querySelector('.rail-toggle-label').textContent = collapsed ? 'Show filters' : 'Hide filters';
    if (remember) try { localStorage.setItem('venue-radar:rail', collapsed ? 'collapsed' : 'open'); } catch (error) { /* not remembered */ }
  };
  let saved = null;
  try { saved = localStorage.getItem('venue-radar:rail'); } catch (error) { /* default: open */ }
  setCollapsed(saved === 'collapsed', false);
  button.addEventListener('click', () => setCollapsed(!document.body.classList.contains('rail-collapsed'), true));
  const active = () => {
    const families = [...document.querySelectorAll('[data-family-toggle]:checked')].map((input) => input.dataset.familyToggle);
    const topics = [...document.querySelectorAll('[data-topic-family]:checked')].filter((input) => !families.includes(input.dataset.topicFamily));
    const others = document.querySelectorAll('[data-filter-group]:not([data-filter-group="topics"]):checked').length;
    return (document.querySelector('#search').value.trim() ? 1 : 0) + families.length + topics.length + others;
  };
  const update = () => {
    const n = active();
    count.hidden = n === 0;
    count.textContent = String(n);
    button.setAttribute('aria-label', `${button.title}${n ? ` (${n} active)` : ''}`);
  };
  const controls = document.querySelector('.controls');
  ['input', 'change', 'click'].forEach((type) => controls.addEventListener(type, () => setTimeout(update, 0)));
  addEventListener('popstate', update);
  update();
})();

// ADR-059: on phones, More filters opens as a full-screen sheet. Filters still
// apply at once; Close and "Show N conferences" just close the sheet.
(() => {
  const details = document.querySelector('#filter-details');
  const summary = details?.querySelector(':scope > summary');
  const sheet = details?.querySelector('.filter-content');
  const apply = details?.querySelector('.sheet-apply');
  const resultCount = document.querySelector('#result-count');
  if (!details || !sheet) return;
  const phone = matchMedia('(max-width: 760px)');
  const isSheet = () => phone.matches && details.open;
  const label = () => {
    const shown = (resultCount?.textContent || '').match(/^(\d+)/);
    apply.textContent = shown ? `Show ${shown[1]} conference${shown[1] === '1' ? '' : 's'}` : 'Show results';
  };
  const sync = (focusInside) => {
    const open = isSheet();
    document.body.classList.toggle('sheet-open', open);
    if (open) {
      sheet.setAttribute('role', 'dialog');
      sheet.setAttribute('aria-modal', 'true');
      sheet.setAttribute('aria-label', 'More filters');
      label();
      if (focusInside) sheet.querySelector('.sheet-close').focus();
    } else {
      ['role', 'aria-modal', 'aria-label'].forEach((name) => sheet.removeAttribute(name));
    }
  };
  details.addEventListener('toggle', () => sync(document.activeElement === summary));
  phone.addEventListener('change', () => sync(false));
  sheet.querySelectorAll('[data-sheet-close]').forEach((button) => button.addEventListener('click', () => {
    details.open = false;
    summary.focus();
  }));
  document.addEventListener('keydown', (event) => {
    if (!isSheet()) return;
    if (event.key === 'Escape') { details.open = false; summary.focus(); return; }
    if (event.key !== 'Tab') return;
    const items = [...sheet.querySelectorAll('button, input, select, a[href], summary')].filter((item) => item.offsetParent !== null);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  if (resultCount) new MutationObserver(() => { if (isSheet()) label(); }).observe(resultCount, {childList: true, characterData: true, subtree: true});
  sync(false);
})();

// ADR-059: an optional Agenda layout for Upcoming Deadlines. It reuses the
// same filtered, sorted rows; this only adds a date margin and "This week /
// Next 30 days / Later" headings. Table stays the default and the no-JS view.
(() => {
  const panel = document.querySelector('#panel-deadlines');
  const buttons = [...document.querySelectorAll('.view-switch [data-view]')];
  if (!panel || !buttons.length) return;
  const DAY = 24 * 60 * 60 * 1000;
  const groups = [['week', 'This week', 7 * DAY], ['month', 'Next 30 days', 30 * DAY], ['later', 'Later', Infinity]];
  const isAgenda = () => panel.classList.contains('agenda-view');
  window.renderAgenda = (now = Date.now()) => {
    const body = panel.querySelector('tbody');
    body.querySelectorAll('.agenda-group').forEach((row) => row.remove());
    // core.js runs after this script; until its first render there are no states.
    if (!isAgenda() || typeof stateByRow === 'undefined') return;
    const rows = [...body.querySelectorAll('[data-deadline-group]')];
    const seen = new Set();
    rows.forEach((row) => {
      const time = row.querySelector('[data-deadline-row]:not([hidden]) time');
      const [month = '', day = ''] = (time?.textContent || '').replace(',', '').split(' ');
      row.dataset.agendaDay = day;
      row.dataset.agendaMonth = month.slice(0, 3);
      if (row.hidden) return;
      const action = stateByRow.get(row)?.action;
      const left = action ? action.time - now : Infinity;
      const [key, label] = groups.find(([, , limit]) => left < limit);
      if (seen.has(key)) return;
      seen.add(key);
      const heading = document.createElement('tr');
      heading.className = 'agenda-group';
      heading.innerHTML = '<th colspan="9" scope="colgroup"></th>';
      heading.firstChild.textContent = label;
      body.insertBefore(heading, row);
    });
  };
  const setView = (view, remember) => {
    panel.classList.toggle('agenda-view', view === 'agenda');
    buttons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
    const params = new URLSearchParams(location.search);
    if (view === 'agenda') params.set('view', 'agenda'); else params.delete('view');
    const text = params.toString().replace(/%2C/g, ',');
    try { history.replaceState(history.state, '', `${location.pathname}${text ? `?${text}` : ''}${location.hash}`); } catch (error) { /* file:// */ }
    if (remember) try { localStorage.setItem('venue-radar:view', view); } catch (error) { /* not remembered */ }
    window.renderAgenda();
  };
  let start = new URLSearchParams(location.search).get('view');
  if (!start) try { start = localStorage.getItem('venue-radar:view'); } catch (error) { /* table */ }
  setView(start === 'agenda' ? 'agenda' : 'table', false);
  buttons.forEach((button) => button.addEventListener('click', () => setView(button.dataset.view, true)));
})();

// ADR-061: filter box for the city index (local to the index; not a page filter).
function filterCityIndex() {
  const input = document.querySelector('#city-filter');
  if (!input) return;
  const tokens = normalizeSearch(input.value).split(' ').filter(Boolean);
  let shown = 0;
  document.querySelectorAll('#map-cities .city-group').forEach((section) => {
    let visible = 0;
    section.querySelectorAll('.map-city-link').forEach((button) => {
      const match = tokens.every((token) => button.dataset.search.includes(token));
      button.hidden = !match;
      if (match) visible += 1;
    });
    section.hidden = visible === 0;
    shown += visible;
  });
  document.querySelector('#city-index-empty').hidden = shown > 0 || !document.querySelector('#map-cities').childElementCount;
}
// Phones: the index starts collapsed under the map ("Show N host cities").
function syncCityIndexLabel() {
  const toggle = document.querySelector('#city-index-toggle');
  const label = document.querySelector('#city-index-label');
  if (!toggle || !label) return;
  const open = toggle.getAttribute('aria-expanded') === 'true';
  const n = label.dataset.count || '';
  label.textContent = open ? 'Hide host cities' : `Show ${n} host cit${n === '1' ? 'y' : 'ies'}`;
}
(() => {
  const input = document.querySelector('#city-filter');
  const toggle = document.querySelector('#city-index-toggle');
  if (!input || !toggle) return;
  input.addEventListener('input', filterCityIndex);
  toggle.addEventListener('click', () => {
    toggle.setAttribute('aria-expanded', String(toggle.getAttribute('aria-expanded') !== 'true'));
    document.querySelector('#city-index').classList.toggle('is-open', toggle.getAttribute('aria-expanded') === 'true');
    syncCityIndexLabel();
  });
  syncCityIndexLabel();
})();
