// Unit tests for assets/logic.js (pure helpers) with Node's built-in runner:
//   node --test tests/js/*.test.mjs
// No dependencies; the browser suites still cover DOM wiring.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../../assets/logic.js', import.meta.url), 'utf8');
const context = vm.createContext({Intl, Date});
vm.runInContext(`${source}\nthis.api = {normalizeSearch, matchesSearch, formatRemaining, openLabel, describeInstant, computeSubmissionState};`, context);
const {normalizeSearch, matchesSearch, formatRemaining, openLabel, describeInstant, computeSubmissionState} = context.api;
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

test('countdowns use days and hours', () => {
  const now = Date.parse('2026-10-01T00:00:00Z');
  assert.equal(formatRemaining(now + (2 * 24 + 5) * 3600e3, now), '2d 5h');
  assert.equal(formatRemaining(now + 3 * 3600e3, now), '3h');
  assert.equal(formatRemaining(now + 10 * 60e3, now), '<1h');
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
