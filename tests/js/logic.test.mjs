// Unit tests for assets/logic.js (pure helpers) with Node's built-in runner:
//   node --test tests/js/*.test.mjs
// No dependencies; the browser suites still cover DOM wiring.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../../assets/logic.js', import.meta.url), 'utf8');
const context = vm.createContext({Intl, Date});
vm.runInContext(`${source}\nthis.api = {normalizeSearch, matchesSearch, formatRemaining, countdownText, describeRemaining, openLabel, describeInstant, computeSubmissionState};`, context);
const {normalizeSearch, matchesSearch, formatRemaining, countdownText, describeRemaining, openLabel, describeInstant, computeSubmissionState} = context.api;
const TYPES = new Set(['abstract', 'discussion_paper', 'extended_abstract', 'full_paper', 'journal_paper',
  'late_abstract', 'poster', 'regular_paper', 'resource_paper', 'short_paper', 'special_session_paper', 'workshop_paper']);

test('search folds accents and punctuation', () => {
  assert.equal(normalizeSearch('Montréal, Québec'), 'montreal quebec');
  assert.equal(normalizeSearch('S+SSPR / CNS*'), 's sspr cns');
});

test('every word must match; short words match word starts only', () => {
  const haystack = ` ${normalizeSearch('IEEE CDC 2027 Lisbon Portugal Control & Robotics AIES fairness')} `;
  assert(matchesSearch(haystack, ['lisbon', 'control']));
  assert(matchesSearch(haystack, ['control', 'lisbon']));
  assert(!matchesSearch(haystack, ['lisbon', 'vision']));
  assert(matchesSearch(haystack, ['ai']), 'AIES starts with ai');
  assert(!matchesSearch(' fairness ', ['ai']), 'no infix match for two-letter words');
  assert(matchesSearch(' neurips 2027 ', ['ips']), 'longer tokens keep infix matches');
});

test('exact countdowns sharpen to minutes on the last day', () => {
  const now = Date.parse('2026-10-01T00:00:00Z');
  assert.equal(formatRemaining(now + (2 * 24 + 5) * 3600e3, now), '2d 5h');
  assert.equal(formatRemaining(now + (5 * 60 + 20) * 60e3 + 30e3, now), '5h 20m');
  assert.equal(formatRemaining(now + 3 * 3600e3, now), '3h 0m');
  assert.equal(formatRemaining(now + 43 * 60e3 + 59e3, now), '43 min');
  assert.equal(formatRemaining(now + 30e3, now), '<1 min');
  assert.equal(formatRemaining(now - 60e3, now), '<1 min', 'never negative');
  assert.equal(describeRemaining(now + (5 * 60 + 1) * 60e3, now), '5 hours 1 minute left');
  assert.equal(describeRemaining(now + 43 * 60e3, now), '43 minutes left');
  assert.equal(describeRemaining(now + 20e3, now), 'less than a minute left');
});

test('estimated countdowns use one coarse unit', () => {
  const now = Date.parse('2026-10-01T00:00:00Z');
  const days = (count) => now + count * 24 * 3600e3 + 5 * 3600e3;
  assert.equal(countdownText(days(5), now, true), '~5 days');
  assert.equal(countdownText(days(1), now, true), '~1 day');
  assert.equal(countdownText(days(21), now, true), '~3 weeks');
  assert.equal(countdownText(days(150), now, true), '~5 months');
  assert.equal(countdownText(days(616), now, true), '~20 months');
  assert.equal(countdownText(days(800), now, true), '~2 years');
  assert.equal(countdownText(now + 3 * 3600e3, now, true), '~3 hours');
  assert.equal(countdownText(now + 30 * 60e3, now, true), '~1 hour', 'an estimate never claims minutes');
  assert.equal(describeRemaining(now + 30 * 60e3, now, true), 'about 1 hour left, estimated');
  assert.equal(describeRemaining(days(21), now, true), 'about 3 weeks left, estimated');
  // A confirmed day with an unannounced hour keeps exact units behind the tilde.
  assert.equal(countdownText(days(4), now, false, true), '~4d 5h');
  assert.equal(countdownText(days(4), now), '4d 5h');
});

test('open labels follow the contribution type', () => {
  assert.equal(openLabel('late_abstract'), 'Open abstract submissions');
  assert.equal(openLabel('poster'), 'Open poster submissions');
  assert.equal(openLabel('regular_paper'), 'Open paper submissions');
});

test('instants are described in UTC with the viewer time', () => {
  assert.match(describeInstant(Date.parse('2026-10-10T20:00:00Z')), /^Oct 10, 2026, 20:00 UTC \(your time: .+\)$/);
});

// Same route fixtures as tests/submission_behavior.mjs, without a browser.
const now = Date.parse('2026-10-07T12:00:00Z');
const makeDeadline = (type, at, extra = {}) => ({type, time: Date.parse(at), estimated: false, approximate_time: false, ...extra});
const paper = extra => makeDeadline('full_paper', '2026-11-01T12:00:00Z', extra);
const gate = extra => makeDeadline('abstract', '2026-10-20T12:00:00Z', {gate_for: 'full_paper', ...extra});
const futureOpening = '2026-10-10T12:00:00Z';
const pastOpening = '2026-10-01T12:00:00Z';
const fixtures = [
  ['unknown opening', [paper()], 'opportunity', 'full_paper'],
  ['scheduled opening', [paper({opens_at: futureOpening})], 'scheduled', 'full_paper'],
  ['published open', [paper({opens_at: pastOpening})], 'open', 'full_paper'],
  ['observed open', [paper({open_observed_on: '2026-10-05'})], 'open', 'full_paper'],
  ['estimated open date', [paper({estimated: true, opens_at: pastOpening})], 'estimated', 'full_paper'],
  ['estimated paper after confirmed gate', [gate(), paper({estimated: true})], 'estimated', 'abstract'],
  ['estimated mandatory gate', [gate({estimated: true}), paper()], 'estimated', 'abstract'],
  ['mandatory abstract', [gate(), paper()], 'opportunity', 'abstract'],
  ['gate opening unknown despite paper opening', [gate(), paper({opens_at: pastOpening})], 'opportunity', 'abstract'],
  ['mandatory gate scheduled', [gate({opens_at: futureOpening}), paper()], 'scheduled', 'abstract'],
  ['passed mandatory abstract', [gate({time: now - 1}), paper()], 'closed', null],
  ['exactly expired abstract', [gate({time: now}), paper()], 'closed', null],
  ['expired paper', [paper({time: now})], 'closed', null],
  ['independent paper track', [gate({time: now - 1}), paper(), makeDeadline('short_paper', '2026-11-12T12:00:00Z')], 'opportunity', 'short_paper'],
  ['organizer and production milestones first', [makeDeadline('workshop_proposal', '2026-10-08T12:00:00Z'), makeDeadline('camera_ready', '2026-10-09T12:00:00Z'), paper()], 'opportunity', 'full_paper'],
  ['only post-submission activity', [paper({time: now - 1}), makeDeadline('paper_update', '2026-10-09T12:00:00Z'), makeDeadline('camera_ready', '2026-10-10T12:00:00Z')], 'closed', null],
  ['organizer proposal without paper information', [makeDeadline('workshop_proposal', '2026-10-08T12:00:00Z')], 'unknown', null],
  ['ARR commitment alone', [makeDeadline('commitment', '2026-10-08T12:00:00Z')], 'unknown', null],
  ['deadline unannounced', [], 'unknown', null],
  ...['workshop_paper', 'poster', 'extended_abstract', 'discussion_paper', 'journal_paper', 'resource_paper', 'special_session_paper']
    .map(type => [type, [makeDeadline(type, '2026-11-01T12:00:00Z')], 'opportunity', type]),
];

for (const [name, details, kind, action] of fixtures) {
  test(`route: ${name}`, () => {
    const state = computeSubmissionState(details, '2027-06-01', '2027-06-03', 'confirmed', now, TYPES);
    assert.equal(state.kind, kind);
    assert.equal(state.action?.type ?? null, action);
    if (state.action) assert.equal(state.action, state.milestone, 'summary and countdown share the action');
  });
}

test('meeting start and end close every route', () => {
  const details = [paper()];
  assert.equal(computeSubmissionState(details, '2026-10-01', '2026-10-09', 'confirmed', now, TYPES).kind, 'ongoing');
  assert.equal(computeSubmissionState(details, '2026-09-01', '2026-09-03', 'confirmed', now, TYPES).kind, 'past');
});
