// Pure Venue Radar logic: no DOM access, so it can be unit-tested in Node
// (tests/js/logic.test.mjs). Loaded before core.js; functions are global.

// Accent- and punctuation-insensitive text, e.g. "Montréal" -> "montreal".
function normalizeSearch(value) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, " ").trim();
}

// Every word must match; one- and two-letter words match word starts only,
// so "ai" finds AIES but not "fairness".
function matchesSearch(haystack, tokens) {
  return tokens.every((token) => haystack.includes(token.length <= 2 ? ` ${token}` : token));
}

const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const plural = (count, unit) => `${count} ${unit}${count === 1 ? "" : "s"}`;

// Estimated dates are proxies, so they get one coarse unit instead of a
// spuriously exact "616d 14h" (ADR-044).
function coarseRemaining(diff) {
  const days = Math.floor(diff / DAY_MS);
  if (days < 1) return plural(Math.max(1, Math.round(diff / HOUR_MS)), "hour");
  if (days < 14) return plural(days, "day");
  if (days < 56) return plural(Math.round(days / 7), "week");
  if (days < 730) return plural(Math.round(days / 30.44), "month");
  return plural(Math.round(days / 365.25), "year");
}

// Exact countdowns: "2d 5h", then "5h 20m" on the last day, "43 min" in the
// last hour. Estimated deadlines use coarseRemaining.
function formatRemaining(deadline, now, estimated = false) {
  const diff = Math.max(0, deadline - now);
  if (estimated) return coarseRemaining(diff);
  const days = Math.floor(diff / DAY_MS);
  const hours = Math.floor((diff % DAY_MS) / HOUR_MS);
  const minutes = Math.floor((diff % HOUR_MS) / MINUTE_MS);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return minutes > 0 ? `${minutes} min` : "<1 min";
}

// The visible countdown; "~" marks an estimate or an unannounced cutoff hour.
function countdownText(deadline, now, estimated = false, approximateTime = false) {
  return `${estimated || approximateTime ? "~" : ""}${formatRemaining(deadline, now, estimated)}`;
}

// Screen-reader text for a countdown, e.g. "4 days 14 hours left" or
// "about 3 weeks left, estimated".
function describeRemaining(deadline, now, estimated = false, approximateTime = false) {
  const diff = Math.max(0, deadline - now);
  const days = Math.floor(diff / DAY_MS);
  const hours = Math.floor((diff % DAY_MS) / HOUR_MS);
  const minutes = Math.floor((diff % HOUR_MS) / MINUTE_MS);
  const amount = estimated ? coarseRemaining(diff)
    : days > 0 ? `${plural(days, "day")} ${plural(hours, "hour")}`
    : hours > 0 ? `${plural(hours, "hour")} ${plural(minutes, "minute")}`
    : minutes > 0 ? plural(minutes, "minute") : "less than a minute";
  return `${estimated ? "about " : ""}${amount} left${approximateTime ? ", exact hour unannounced" : ""}${estimated ? ", estimated" : ""}`;
}

const utcFormatter = new Intl.DateTimeFormat("en", {
  month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit",
  hourCycle: "h23", timeZone: "UTC",
});
const localFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  timeZoneName: "short",
});

function describeInstant(time) {
  return `${utcFormatter.format(time)} UTC (your time: ${localFormatter.format(time)})`;
}

function openLabel(type) {
  if (["abstract", "late_abstract", "extended_abstract"].includes(type)) return "Open abstract submissions";
  if (type === "poster") return "Open poster submissions";
  if (type === "discussion_paper") return "Open discussion papers (non-archival)";
  if (type === "journal_paper") return "Open joint journal/paper submissions";
  return "Open paper submissions";
}

function computeSubmissionState(details, conferenceStart, conferenceEnd, confidence, now, types) {
  const end = Date.parse(`${conferenceEnd}T23:59:59Z`);
  const start = Date.parse(`${conferenceStart}T00:00:00Z`);
  if (end < now) return { kind: "past", label: "Edition passed" };
  if (start <= now) return { kind: "ongoing", label: "Closed to new submissions" };
  const milestones = details.flatMap((item) => [
    item,
    ...(item.opens_at ? [{
      type: `${item.type}_opens`,
      time: Date.parse(item.opens_at),
      estimated: item.estimated,
      approximate_time: item.approximate_time,
    }] : []),
  ]);
  milestones.push({
    type: "conference_start", time: start,
    estimated: ["estimated", "not_yet_announced", "stale"].includes(confidence),
  });
  // Closed and unannounced routes retain a chronological schedule fallback.
  const scheduleMilestone = milestones.filter((item) => item.time > now)
    .sort((a, b) => a.time - b.time)[0] || null;
  const submissions = details.filter((deadline) =>
    types.has(deadline.type) && !deadline.gate_for
  );
  const opportunities = submissions.flatMap((deadline) => {
    if (deadline.time <= now) return [];
    const gates = details.filter((item) => item.gate_for === deadline.type);
    if (gates.some((gate) => gate.time <= now)) return [];
    const action = gates.sort((a, b) => a.time - b.time)[0] || deadline;
    return [{
      action,
      estimated: deadline.estimated || gates.some((gate) => gate.estimated),
    }];
  }).sort((a, b) => a.action.time - b.action.time);
  const next = opportunities[0];
  if (next) {
    const estimated = next.estimated;
    const opensAt = Date.parse(next.action.opens_at);
    const scheduled = opensAt > now;
    const open = !scheduled && (opensAt <= now ||
      (next.action.open_observed_on && Date.parse(`${next.action.open_observed_on}T00:00:00Z`) <= now));
    const action = { ...next.action, estimated };
    return {
      kind: estimated ? "estimated" : open ? "open" : scheduled ? "scheduled" : "opportunity",
      label: estimated ? "Submission opportunity (estimated)"
        : open ? openLabel(action.type) : scheduled ? "Scheduled submission" : "Submission opportunity",
      description: estimated ? "Submission timing or eligibility is estimated; check the organizer's call."
        : open ? "Opening evidence is recorded for this submission step."
        : scheduled ? `This submission step opens ${describeInstant(opensAt)}; the countdown targets its deadline.`
        : "A submission deadline is confirmed, but opening information has not been verified.",
      action,
      milestone: action,
    };
  }
  if (submissions.length === 0) {
    return { kind: "unknown", label: "Deadline unannounced", milestone: scheduleMilestone };
  }
  return {
    kind: "closed",
    label: "Closed to new submissions",
    milestone: scheduleMilestone,
  };
}
