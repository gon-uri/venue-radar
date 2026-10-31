// Venue Radar page wiring: filters, tables, countdowns and menus. Uses the
// pure helpers in logic.js and the map/menu helpers in site.js. Top-level
// names stay global because the browser regression suites call them.

const search = document.querySelector("#search");
const filters = [...document.querySelectorAll("[data-filter-group]")];
const rows = [...document.querySelectorAll("[data-filter-row]")];
const openOnly = document.querySelector("#open-only");
const resultCount = document.querySelector("#result-count");
const showHidden = document.querySelector("#show-hidden");
const filterCount = document.querySelector("#filter-count");
const clearFilters = document.querySelector("#clear-filters");
const tabButtons = [...document.querySelectorAll("[data-tab-target]")];
const tabPanels = [...document.querySelectorAll("[data-tab-panel]")];
const deadlinesBody = document.querySelector("#deadlines-body");
const deadlineGroups = [...document.querySelectorAll("[data-deadline-group]")];
const conferenceRows = [...document.querySelectorAll("[data-conference-row]")];
const upcomingConferenceBody = document.querySelector("#upcoming-conferences-body");
const pastConferenceBody = document.querySelector("#past-conferences-body");
const pastSection = document.querySelector("#past-conferences-section");
const deadlinesEmpty = document.querySelector("#deadlines-empty");
const conferencesEmpty = document.querySelector("#conferences-empty");
const venueConfig = JSON.parse(document.querySelector("#venue-config").textContent);
const submissionTypes = new Set(venueConfig.submissionTypes);
const metadataGroups = ["size", "icore", "ccf", "acceptance"];
const eligibleKinds = ["open", "scheduled", "opportunity", "estimated"];
const deadlineData = new Map(rows.map((row) => [
  row,
  JSON.parse(row.dataset.deadlines || "[]").map((deadline) => ({
    ...deadline,
    time: Date.parse(deadline.at),
  })),
]));
const stateByRow = new Map();
const starredOnly = document.querySelector("#starred-only");
const starKey = "venue-radar:starred";

function loadStarred() {
  try {
    return new Set(JSON.parse(localStorage.getItem(starKey) || "[]"));
  } catch (error) {
    return new Set();
  }
}
let starred = loadStarred();

function saveStarred() {
  try { localStorage.setItem(starKey, JSON.stringify([...starred].sort())); } catch (error) { /* storage blocked */ }
}

function renderStars() {
  document.querySelectorAll("[data-star]").forEach((button) => {
    const on = starred.has(button.dataset.star);
    button.hidden = false;
    button.setAttribute("aria-pressed", String(on));
  });
  const toggle = starredOnly.closest("label");
  toggle.hidden = !starred.size && !starredOnly.checked;
  toggle.querySelector("[data-starred-count]").textContent = `(${starred.size})`;
  const feeds = document.querySelector("[data-starred-feeds]");
  const list = feeds?.querySelector("[data-starred-list]");
  if (list) {
    const names = new Map([...document.querySelectorAll("[data-star]")].map((b) => [b.dataset.star, b.dataset.starName]));
    list.replaceChildren(...[...starred].filter((slug) => names.has(slug)).sort().map((slug) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "feed-link";
      button.textContent = names.get(slug);
      button.addEventListener("click", () => {
        const select = document.querySelector("#feed-series");
        select.value = `series/${slug}.ics`;
        select.dispatchEvent(new Event("change"));
        select.focus();
      });
      return button;
    }));
    feeds.hidden = !list.children.length;
  }
}
const baseMatchByRow = new Map();

const splitSet = (value) => new Set((value || "").split(" ").filter(Boolean));
const rowCache = new Map(rows.map((row) => [row, {
  haystack: ` ${normalizeSearch(row.dataset.search || "")} `,
  topics: splitSet(row.dataset.topics),
  families: splitSet(row.dataset.families),
  groups: Object.fromEntries(metadataGroups.map((group) => [group, splitSet(row.dataset[group])])),
}]));

function selectedValues(group) {
  return filters
    .filter((input) => input.dataset.filterGroup === group && input.checked)
    .map((input) => input.value);
}

// Computed once per pass instead of once per row.
function filterContext() {
  return {
    tokens: normalizeSearch(search.value).split(" ").filter(Boolean),
    groups: metadataGroups.map((group) => [group, new Set(selectedValues(group))])
      .filter(([, values]) => values.size),
    topics: topicFilterContext(),
    starredOnly: starredOnly.checked,
  };
}

function rowMatchesFilters(row, context = filterContext()) {
  const cache = rowCache.get(row);
  return matchesSearch(cache.haystack, context.tokens)
    && context.groups.every(([group, values]) => [...cache.groups[group]].some((value) => values.has(value)))
    && venueTopicMatch(row, context.topics, cache)
    && (!context.starredOnly || starred.has(row.dataset.seriesSlug));
}

function passesOpenOnly(row) {
  return !row.hasAttribute("data-deadline-group") || !openOnly.checked
    || eligibleKinds.includes(stateByRow.get(row)?.kind);
}

// Shows the viewer's local time under each confirmed exact cutoff, unless
// the viewer is already in the deadline's own UTC offset.
function renderLocalTimes() {
  document.querySelectorAll("[data-local-time]").forEach((node) => {
    const row = node.closest("[data-deadline-row]");
    const at = Date.parse(row.querySelector("time").dateTime);
    const clock = row.querySelector(".deadline-clock");
    const sameZone = Number(clock.dataset.offset) === -new Date(at).getTimezoneOffset();
    node.textContent = sameZone ? "" : `Your time: ${localFormatter.format(at)}`;
    node.hidden = sameZone;
  });
}

function submissionState(row, now) {
  return computeSubmissionState(deadlineData.get(row) || [], row.dataset.conferenceStart,
    row.dataset.conferenceEnd, row.dataset.confidence, now, submissionTypes);
}

function updateStatus(row, state) {
  const label = row.querySelector("[data-submission-status]");
  if (!label) return;
  const className = `submission-status status-${state.kind}`;
  if (label.textContent !== state.label) label.textContent = state.label;
  if (label.className !== className) label.className = className;
  if (label.title !== (state.description || "")) label.title = state.description || "";
}

// Moves only rows that are out of place, so a focused control is never
// detached by a re-render (filters, toggles or the minute refresh).
function placeRows(body, orderedRows) {
  const active = document.activeElement;
  let cursor = body.firstElementChild;
  orderedRows.forEach((row) => {
    if (row === cursor) {
      cursor = cursor.nextElementSibling;
      return;
    }
    body.insertBefore(row, cursor);
  });
  if (active && active !== document.activeElement && active.isConnected) {
    active.focus({ preventScroll: true });
  }
}

// Mobile cards show the counted-down action under Time left, because the
// Next milestone column is behind "More info" there.
function renderNextStep(group, state, summaryDetail) {
  const nextStep = group.querySelector("[data-next-step]");
  if (!nextStep) return;
  if (!state.action || !summaryDetail) {
    nextStep.hidden = true;
    return;
  }
  const when = summaryDetail.querySelector("time").textContent;
  const clock = summaryDetail.querySelector(".deadline-clock")?.textContent;
  const local = summaryDetail.querySelector("[data-local-time]");
  const label = summaryDetail.querySelector(".deadline-milestone").textContent;
  const conflict = summaryDetail.querySelector(".deadline-note")?.textContent.replace(/^Note: /, "") || "";
  const parts = [`${clock ? `${when}, ${clock}` : when}${conflict ? "*" : ""}`, state.action.estimated ? "(est.)" : "", label,
    local && !local.hidden ? local.textContent : "", conflict];
  const key = parts.join("|");
  if (nextStep.dataset.key !== key) {
    nextStep.dataset.key = key;
    const date = document.createElement("strong");
    date.textContent = parts[0];
    const what = document.createElement("span");
    what.textContent = `${parts[1] ? parts[1] + " " : ""}${label}`;
    nextStep.replaceChildren(date, what);
    if (parts[3]) {
      const yours = document.createElement("span");
      yours.className = "next-step-local";
      yours.textContent = parts[3];
      nextStep.append(yours);
    }
    if (parts[4]) {
      const note = document.createElement("span");
      note.className = "next-step-local";
      note.textContent = parts[4];
      nextStep.append(note);
    }
  }
  nextStep.hidden = false;
}

// A closed or unannounced edition points to the next tracked edition's call.
function renderSuccessor(group, state) {
  const link = group.querySelector("[data-successor-link]");
  if (!link) return;
  const successorRow = document.getElementById(`deadline-${link.dataset.successor}`);
  const successor = successorRow && stateByRow.get(successorRow);
  const show = ["closed", "unknown"].includes(state.kind) && Boolean(successor?.action);
  link.hidden = !show;
  if (!show) return;
  link.dataset.baseText = link.dataset.baseText || link.textContent;
  // Month and year come from the successor's displayed date, which is in
  // the deadline's own offset ("May 4, 2027" -> "May 2027").
  const detail = [...successorRow.querySelectorAll("[data-deadline-row]")].find((item) =>
    item.dataset.deadlineType === successor.action.type &&
    Date.parse(item.querySelector("time").dateTime) === successor.action.time);
  const [month, , year] = (detail?.querySelector("time").textContent || "").replace(",", "").split(" ");
  const when = month && year ? `${month.slice(0, 3)} ${year}` : "";
  const text = `${link.dataset.baseText}${when ? ` · ${successor.action.estimated ? "~" : ""}${when}` : ""}${successor.action.estimated ? " (est.)" : ""}`;
  if (link.textContent !== text) link.textContent = text;
}

function renderDeadlineGroups(now) {
  const blocks = [];
  deadlineGroups.forEach((group) => {
    const groupId = group.dataset.deadlineGroup;
    const state = stateByRow.get(group);
    const details = [...group.querySelectorAll("[data-deadline-row]")];
    const groupMatches = group.dataset.filterMatch === "true";
    const summaryDetail = details.find((detail) =>
      detail.dataset.deadlineType === state.milestone?.type &&
      Date.parse(detail.querySelector("time").dateTime) === state.milestone.time
    ) || details[0];
    const canExpand = details.length > 1;
    const expanded = canExpand && group.dataset.expanded === "true";
    group.hidden = !groupMatches || !state.milestone || state.kind === "past";
    group.classList.toggle("is-expanded", expanded);
    const timeLeft = group.querySelector("[data-time-left]");
    const remaining = state.kind === "closed" ? "Closed" : state.action
      ? countdownText(state.action.time, now, state.action.estimated, state.action.approximate_time)
      : "\u2014";
    if (timeLeft.textContent !== remaining) timeLeft.textContent = remaining;
    const spoken = state.kind === "closed" ? "Closed to new submissions" : state.action
      ? describeRemaining(state.action.time, now, state.action.estimated, state.action.approximate_time)
      : "No submission deadline announced";
    const spokenNode = group.querySelector("[data-time-left-sr]");
    if (spokenNode && spokenNode.textContent !== spoken) spokenNode.textContent = spoken;
    group.querySelector("[data-time-estimate]").hidden =
      !(state.action?.approximate_time && !state.action.estimated);
    details.forEach((detail) => {
      detail.hidden = !(expanded || detail === summaryDetail);
      const passed = Date.parse(detail.querySelector("time").dateTime) <= now;
      detail.classList.toggle("is-past", passed);
      const marker = detail.querySelector("[data-deadline-passed]");
      if (marker.textContent !== (passed ? "Passed" : "")) marker.textContent = passed ? "Passed" : "";
    });
    renderNextStep(group, state, summaryDetail);
    renderSuccessor(group, state);
    if (!group.hidden) {
      blocks.push({
        sortTime: state.milestone?.time ?? Infinity,
        id: groupId,
        row: group,
      });
    }
  });

  placeRows(deadlinesBody, blocks
    .sort((left, right) => {
      const timeSort = left.sortTime - right.sortTime;
      return timeSort || left.id.localeCompare(right.id);
    })
    .map((block) => block.row));
}

function actionButton(text, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "link-button";
  button.textContent = text;
  button.addEventListener("click", handler);
  return button;
}

function showClosedAndUnannounced() {
  openOnly.checked = false;
  applyFilters();
  openOnly.focus();
}

// Explains an empty view instead of showing a bare table header.
function renderEmptyState(container, show, hiddenCount) {
  container.hidden = !show;
  // The table that follows would only show its header row.
  container.nextElementSibling.hidden = show;
  if (!show) {
    delete container.dataset.key;
    return;
  }
  const key = String(hiddenCount);
  if (container.dataset.key === key) return;
  container.dataset.key = key;
  const message = document.createElement("p");
  message.textContent = hiddenCount
    ? `No open or upcoming submission options match these filters. ${hiddenCount} matching conference${hiddenCount === 1 ? " is" : "s are"} closed or ${hiddenCount === 1 ? "has" : "have"} no announced deadline.`
    : "No conferences match these filters.";
  const actions = document.createElement("p");
  actions.className = "empty-state-actions";
  if (hiddenCount) actions.append(actionButton(hiddenCount === 1 ? "Show it" : "Show them", showClosedAndUnannounced));
  actions.append(actionButton("Clear filters", () => clearFilters.click()));
  const request = document.createElement("a");
  request.href = "https://github.com/gon-uri/venue-radar/issues/new?template=conference-request.yml";
  request.textContent = "Request a conference";
  actions.append(request);
  container.replaceChildren(message, actions);
}

function updateResultCount() {
  const active = document.querySelector('[role="tab"][aria-selected="true"]').dataset.tabTarget;
  const onDeadlines = active === "deadlines";
  const visible = (onDeadlines ? deadlineGroups : conferenceRows)
    .filter((row) => !row.hidden).length;
  const total = onDeadlines
    ? deadlineGroups.filter((row) => stateByRow.get(row)?.milestone).length
    : conferenceRows.length;
  const text = `${visible} of ${total} conferences`;
  if (resultCount.textContent !== text) resultCount.textContent = text;
  const hiddenByOpenOnly = onDeadlines && openOnly.checked ? deadlineGroups.filter((row) => {
    const state = stateByRow.get(row);
    return baseMatchByRow.get(row) && state?.milestone && state.kind !== "past" && !passesOpenOnly(row);
  }).length : 0;
  showHidden.hidden = hiddenByOpenOnly === 0;
  const hiddenText = `Show ${hiddenByOpenOnly} closed or unannounced`;
  if (showHidden.textContent !== hiddenText) showHidden.textContent = hiddenText;
  renderEmptyState(deadlinesEmpty, onDeadlines && visible === 0, hiddenByOpenOnly);
  renderEmptyState(conferencesEmpty, !onDeadlines && visible === 0, 0);
}

// Badge on the (often collapsed) filter panel: how many restrictions apply.
function updateFilterCount(context) {
  let count = context.tokens.length ? 1 : 0;
  count += filters.filter((input) => input.checked && input.dataset.filterGroup !== "topics").length;
  document.querySelectorAll("[data-family-toggle]").forEach((parent) => {
    count += parent.checked ? 1
      : document.querySelectorAll(`[data-topic-family="${parent.dataset.familyToggle}"]:checked`).length;
  });
  filterCount.hidden = count === 0;
  const text = `${count} active`;
  if (filterCount.textContent !== text) filterCount.textContent = text;
}

function applyFilters() {
  syncTopicParents();
  const now = Date.now();
  const context = filterContext();
  rows.forEach((row) => {
    const state = submissionState(row, now);
    stateByRow.set(row, state);
    updateStatus(row, state);
    const base = rowMatchesFilters(row, context);
    baseMatchByRow.set(row, base);
    row.dataset.filterMatch = String(base && passesOpenOnly(row));
  });
  renderDeadlineGroups(now);
  conferenceRows.forEach((row) => {
    const past = ["past", "ongoing"].includes(stateByRow.get(row).kind);
    const target = past ? pastConferenceBody : upcomingConferenceBody;
    if (row.parentElement !== target) target.appendChild(row);
    row.hidden = row.dataset.filterMatch !== "true";
  });
  placeRows(pastConferenceBody, [...pastConferenceBody.children]
    .sort((a, b) => b.dataset.conferenceStart.localeCompare(a.dataset.conferenceStart)));
  pastSection.hidden = ![...pastConferenceBody.children].some((row) => !row.hidden);
  updateResultCount();
  updateFilterCount(context);
  updateConferenceMap();
  writeUrlState();
}

function activateTab(tabId) {
  tabButtons.forEach((button) => {
    const selected = button.dataset.tabTarget === tabId;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  tabPanels.forEach((panel) => {
    panel.hidden = panel.dataset.tabPanel !== tabId;
  });
  updateResultCount();
  openOnly.closest("label").hidden = tabId !== "deadlines";
  updateConferenceMap();
  if (typeof writeUrlState === "function") writeUrlState();
}

tabButtons.forEach((button, index) => {
  button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
  button.addEventListener("keydown", (event) => {
    const targets = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabButtons.length - 1 };
    if (!(event.key in targets)) {
      return;
    }
    event.preventDefault();
    const nextIndex = (targets[event.key] + tabButtons.length) % tabButtons.length;
    tabButtons[nextIndex].focus();
    activateTab(tabButtons[nextIndex].dataset.tabTarget);
  });
});

deadlineGroups.forEach((group) => {
  const button = group.querySelector(".deadline-toggle");
  if (!button) {
    return;
  }
  button.addEventListener("click", () => {
    if (button.disabled || button.hidden) {
      return;
    }
    const expanded = group.dataset.expanded === "true";
    group.dataset.expanded = String(!expanded);
    button.setAttribute("aria-expanded", String(!expanded));
    button.setAttribute(
      "aria-label",
      `${!expanded ? "Hide" : "Show"} milestones for ${group.querySelector("a").textContent.trim()}`,
    );
    renderDeadlineGroups(Date.now());
  });
});

document.querySelectorAll("[data-successor-link]").forEach((link) => {
  link.addEventListener("click", (event) => {
    const target = document.getElementById(`deadline-${link.dataset.successor}`);
    if (!target) return;
    event.preventDefault();
    if (target.hidden) {
      search.value = target.querySelector('td[data-label="Conference"] a').textContent.trim();
      applyFilters();
      if (target.hidden) {
        clearFilters.click();
      }
    }
    const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
    target.classList.add("is-linked");
    setTimeout(() => target.classList.remove("is-linked"), 2400);
    target.querySelector("td a")?.focus({ preventScroll: true });
  });
});

// ---- Shareable state (ADR-040): filters in the query string, rows in the hash.
const urlGroups = { size: "size", icore: "icore", ccf: "ccf", acc: "acceptance" };
const ownedParams = new Set(["q", "families", "topics", ...Object.keys(urlGroups), "match", "all", "starred", "tab"]);
const siteUrl = document.querySelector("#calendar-menu")?.dataset.siteUrl || location.href.split(/[?#]/)[0];

function readUrlState(force = false) {
  const params = new URLSearchParams(location.search);
  // Without parameters the page keeps its defaults (and any restored form state)
  // unless history navigation asks for an exact restore.
  if (!force && ![...ownedParams].some((key) => params.has(key))) return;
  search.value = params.get("q") || "";
  Object.entries(urlGroups).forEach(([key, group]) => {
    const values = new Set((params.get(key) || "").split(",").filter(Boolean));
    filters.filter((input) => input.dataset.filterGroup === group)
      .forEach((input) => { input.checked = values.has(input.value); });
  });
  const families = new Set((params.get("families") || "").split(",").filter(Boolean));
  const topics = new Set((params.get("topics") || "").split(",").filter(Boolean));
  document.querySelectorAll("[data-topic-family]").forEach((input) => {
    input.checked = families.has(input.dataset.topicFamily) || topics.has(input.value);
  });
  document.querySelector("#topic-match").value = params.get("match") === "all" ? "all" : "any";
  openOnly.checked = params.get("all") !== "1";
  // Stars live in this browser; a shared ?starred=1 would otherwise show nothing.
  starredOnly.checked = params.get("starred") === "1" && starred.size > 0;
  if (params.get("tab") === "conferences") activateTab("conferences");
  else if (force) activateTab("deadlines");
}

function writeUrlState() {
  const params = new URLSearchParams(location.search);
  ownedParams.forEach((key) => params.delete(key));
  const query = search.value.trim();
  if (query) params.set("q", query);
  const families = [...document.querySelectorAll("[data-family-toggle]")].filter((input) => input.checked)
    .map((input) => input.dataset.familyToggle);
  if (families.length) params.set("families", families.join(","));
  const topics = [...document.querySelectorAll("[data-topic-family]:checked")]
    .filter((input) => !families.includes(input.dataset.topicFamily)).map((input) => input.value);
  if (topics.length) params.set("topics", topics.join(","));
  Object.entries(urlGroups).forEach(([key, group]) => {
    const values = selectedValues(group);
    if (values.length) params.set(key, values.join(","));
  });
  if (document.querySelector("#topic-match").value === "all") params.set("match", "all");
  if (!openOnly.checked) params.set("all", "1");
  if (document.querySelector("#starred-only")?.checked) params.set("starred", "1");
  const activeTab = document.querySelector('[role="tab"][aria-selected="true"]')?.dataset.tabTarget;
  if (activeTab === "conferences") params.set("tab", "conferences");
  const text = params.toString().replace(/%2C/g, ",");
  const nextSearch = text ? `?${text}` : "";
  // Keep a deep link only until the visitor changes the view; otherwise a
  // reload would follow it again and reset the newer filters.
  const hash = keepHash || nextSearch === location.search ? location.hash : "";
  const next = `${location.pathname}${nextSearch}${hash}`;
  if (next !== `${location.pathname}${location.search}${location.hash}`) {
    try { history.replaceState(history.state, "", next); } catch (error) { /* file:// or sandboxed */ }
  }
}

// True while the page itself is loading or following a deep link.
let keepHash = true;

// "#neurips-2026" opens that edition; "#neurips" opens the series' next edition.
function linkedRow(hash) {
  let key;
  try {
    key = decodeURIComponent(hash.replace(/^#/, ""));
  } catch (error) {
    return null;
  }
  if (!key || !/^[a-z0-9-]+$/.test(key)) return null;
  const direct = document.getElementById(key);
  if (direct?.matches("[data-filter-row]")) return direct;
  const now = Date.now();
  const deadlineRow = document.getElementById(`deadline-${key}`);
  if (deadlineRow) {
    const state = stateByRow.get(deadlineRow);
    return state?.milestone && state.kind !== "past" ? deadlineRow : document.getElementById(`conference-${key}`);
  }
  const editions = deadlineGroups.filter((row) => row.dataset.seriesSlug === key);
  if (!editions.length) return null;
  const withAction = editions.filter((row) => stateByRow.get(row)?.action)
    .sort((a, b) => stateByRow.get(a).action.time - stateByRow.get(b).action.time);
  if (withAction.length) return withAction[0];
  const upcoming = editions.filter((row) => Date.parse(`${row.dataset.conferenceEnd}T23:59:59Z`) >= now)
    .sort((a, b) => a.dataset.conferenceStart.localeCompare(b.dataset.conferenceStart));
  const chosen = upcoming[0] || editions.sort((a, b) => b.dataset.conferenceStart.localeCompare(a.dataset.conferenceStart))[0];
  const state = stateByRow.get(chosen);
  return state?.milestone && state.kind !== "past" ? chosen : document.getElementById(`conference-${chosen.dataset.edition}`);
}

// Element-id hashes become the edition hash, so the browser's own fragment
// scroll cannot undo the centring and focus below, and past editions resolve
// to their archive row.
function canonicalHash() {
  const prefixed = location.hash.match(/^#(?:deadline|conference)-([a-z0-9-]+)$/);
  if (!prefixed || !document.getElementById(`deadline-${prefixed[1]}`) && !document.getElementById(`conference-${prefixed[1]}`)) return;
  try {
    history.replaceState(history.state, "", `${location.pathname}${location.search}#${prefixed[1]}`);
  } catch (error) { /* file:// or sandboxed */ }
}

function followHash() {
  canonicalHash();
  const target = linkedRow(location.hash);
  if (!target) {
    keepHash = false;
    return;
  }
  keepHash = true;
  const onDeadlines = target.hasAttribute("data-deadline-group");
  activateTab(onDeadlines ? "deadlines" : "conferences");
  if (target.hidden) {
    // A shared link must show its conference even if filters would hide it.
    search.value = "";
    filters.forEach((input) => { input.checked = false; });
    starredOnly.checked = false;
    if (onDeadlines && !eligibleKinds.includes(stateByRow.get(target)?.kind)) openOnly.checked = false;
    renderStars();
    applyFilters();
  }
  // Past and ongoing editions live in the collapsed archive.
  const pastSection = document.querySelector("#past-conferences-section");
  if (pastSection?.contains(target)) pastSection.open = true;
  keepHash = false;
  if (onDeadlines && target.dataset.expanded !== "true") target.querySelector(".deadline-toggle")?.click();
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
  target.classList.add("is-linked");
  setTimeout(() => target.classList.remove("is-linked"), 2400);
  target.querySelector("td a")?.focus({ preventScroll: true });
}

async function copyText(button, text) {
  const original = button.dataset.label || (button.dataset.label = button.textContent);
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
  } catch (error) {
    window.prompt("Copy this link:", text);
  }
  setTimeout(() => { button.textContent = original; }, 2000);
}

document.querySelectorAll("[data-copy-link]").forEach((button) => {
  button.hidden = false;
  button.addEventListener("click", () => copyText(button, `${siteUrl}#${button.dataset.copyLink}`));
});
window.addEventListener("hashchange", followHash);
// Back/Forward between rewritten entries: restore the controls from the URL.
window.addEventListener("popstate", () => {
  keepHash = true;
  readUrlState(true);
  renderStars();
  applyFilters();
  followHash();
});

document.querySelectorAll("[data-star]").forEach((button) => {
  button.addEventListener("click", () => {
    const slug = button.dataset.star;
    if (starred.has(slug)) starred.delete(slug); else starred.add(slug);
    saveStarred();
    renderStars();
    applyFilters();
  });
});
starredOnly.addEventListener("change", applyFilters);

search.addEventListener("input", applyFilters);
filters.forEach((input) => input.addEventListener("change", applyFilters));
document.querySelectorAll("[data-family-toggle]").forEach((input) => input.addEventListener("change", () => {
  document.querySelectorAll(`[data-topic-family="${input.dataset.familyToggle}"]`).forEach((child) => { child.checked = input.checked; });
  applyFilters();
}));
document.querySelector("#topic-match").addEventListener("change", applyFilters);
openOnly.addEventListener("change", applyFilters);
showHidden.addEventListener("click", showClosedAndUnannounced);
clearFilters.addEventListener("click", () => {
  search.value = "";
  filters.forEach((input) => { input.checked = false; });
  openOnly.checked = false;
  starredOnly.checked = false;
  document.querySelector("#topic-match").value = "any";
  if (location.hash) {
    try { history.replaceState(history.state, "", location.pathname + location.search); } catch (error) { /* ignore */ }
  }
  applyFilters();
  if (document.querySelector("#filter-details").open) search.focus();
  else clearFilters.focus();
});
initializeMobileCards();
initializeCalendarMenu();
renderLocalTimes();
readUrlState();
renderStars();
applyFilters();
followHash();
// Re-render on each wall-clock minute, so "43 min" never lags, and as soon as
// a tab is shown again (background tabs throttle or suspend timers).
(function tickEachMinute() {
  setTimeout(() => { try { applyFilters(); } finally { tickEachMinute(); } }, MINUTE_MS - (Date.now() % MINUTE_MS) + 50);
})();
document.addEventListener("visibilitychange", () => { if (!document.hidden) applyFilters(); });
window.addEventListener("pageshow", (event) => { if (event.persisted) applyFilters(); });
const commentObserver = new IntersectionObserver((entries) => {
  if (entries.some((entry) => entry.isIntersecting)) { loadCommunityComments(); commentObserver.disconnect(); }
}, {rootMargin: "150px"});
commentObserver.observe(document.querySelector("#community"));
