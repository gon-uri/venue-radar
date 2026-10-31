import assert from 'node:assert/strict';

export async function checkSubmissionBehavior(page) {
  const opportunitiesOnly = await page.locator('#open-only').isChecked();
  await page.locator('#open-only').uncheck();
  const aamas = page.locator('[data-deadline-group][data-edition="aamas-2027"]');
  const mlsys = page.locator('[data-deadline-group][data-edition="mlsys-2027"]');
  const status = row => row.locator('[data-submission-status]');
  const timeLeft = row => row.locator('[data-time-left]');
  const summary = row => row.locator('[data-deadline-row]:visible');
  const setClock = async at => page.evaluate(at => {
    Date.now = () => Date.parse(at);
    applyFilters();
  }, at);
  const checkCountdown = async (row, at) => {
    assert.equal(await summary(row).locator('time').getAttribute('datetime'), at);
    assert.equal(await timeLeft(row).innerText(), await page.evaluate(at =>
      countdownText(Date.parse(at), Date.now()), at));
  };

  await setClock('2026-10-07T12:00:00Z');
  assert.equal(await status(aamas).innerText(), 'Submission opportunity');
  assert.match(await status(aamas).getAttribute('title'), /opening information has not been verified/);
  assert.equal(await summary(aamas).getAttribute('data-deadline-type'), 'late_abstract');
  assert.match(await summary(aamas).innerText(), /Blue Sky Ideas abstract registration/);
  await checkCountdown(aamas, '2026-11-06T11:59:00Z');
  await aamas.locator('.deadline-toggle').click();
  assert(await aamas.locator('[data-deadline-type="full_paper"]').isVisible(), 'Closed main-track details must remain available');
  assert.equal(await aamas.locator('[data-deadline-type="abstract"] [data-deadline-passed]').innerText(), 'Passed');
  await aamas.locator('.deadline-toggle').click();

  assert.equal(await status(mlsys).innerText(), 'Scheduled submission');
  assert.match(await status(mlsys).getAttribute('title'), /opens Oct 19, 2026, 20:00 UTC \(your time: /);
  assert.equal(await summary(mlsys).getAttribute('data-deadline-type'), 'full_paper');
  await checkCountdown(mlsys, '2026-10-30T19:00:00Z');
  await mlsys.locator('.deadline-toggle').click();
  assert(await mlsys.locator('[data-deadline-type="full_paper_opens"]').isVisible());
  await mlsys.locator('.deadline-toggle').click();
  for (const row of [aamas, mlsys]) {
    assert.equal(await status(row).evaluate(label => getComputedStyle(label).color), 'rgb(61, 112, 68)');
  }
  const estimated = page.locator('[data-deadline-group][data-edition="icml-2027"]');
  assert.equal(await status(estimated).innerText(), 'Submission opportunity (estimated)');
  assert.equal(await status(estimated).evaluate(label => getComputedStyle(label).color), 'rgb(118, 83, 33)');
  assert.match(await timeLeft(estimated).innerText(), /^~/);

  await setClock('2026-10-19T19:59:59Z');
  assert.equal(await status(mlsys).innerText(), 'Scheduled submission');
  await setClock('2026-10-19T20:00:00Z');
  assert.equal(await status(mlsys).innerText(), 'Open paper submissions');
  await checkCountdown(mlsys, '2026-10-30T19:00:00Z');

  await setClock('2026-11-06T12:00:00Z');
  assert.equal(await status(aamas).innerText(), 'Closed to new submissions');
  assert.equal(await timeLeft(aamas).innerText(), 'Closed');
  assert.equal(await status(aamas).evaluate(label => getComputedStyle(label).color), 'rgb(138, 62, 66)');
  assert.equal(await summary(aamas).getAttribute('data-deadline-type'), 'short_paper');
  await page.locator('#open-only').check();
  assert(!(await aamas.isVisible()), 'A passed abstract gate must close the future paper route');
  await page.locator('#open-only').uncheck();
  await setClock('2026-10-07T12:00:00Z');

  const cases = await page.evaluate(() => {
    const now = Date.now();
    const makeDeadline = (type, at, extra = {}) => ({
      type, time: Date.parse(at), estimated: false, approximate_time: false, ...extra,
    });
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
      ...['workshop_paper', 'poster', 'extended_abstract', 'discussion_paper', 'journal_paper', 'resource_paper', 'special_session_paper'].map(type =>
        [type, [makeDeadline(type, '2026-11-01T12:00:00Z')], 'opportunity', type]),
    ];
    return fixtures.map(([name, details, expectedKind, expectedAction]) => {
      const row = document.createElement('tr');
      Object.assign(row.dataset, {conferenceStart: '2027-06-01', conferenceEnd: '2027-06-03', confidence: 'confirmed'});
      deadlineData.set(row, details);
      const state = submissionState(row, now);
      deadlineData.delete(row);
      return {name, expectedKind, expectedAction, kind: state.kind, action: state.action?.type || null,
        sameMilestone: !state.action || state.action === state.milestone};
    });
  });
  for (const result of cases) {
    assert.equal(result.kind, result.expectedKind, result.name);
    assert.equal(result.action, result.expectedAction, result.name);
    assert(result.sameMilestone, `${result.name}: summary and countdown must use the same action`);
  }

  // Closed rows keep chronological placement without showing a production countdown.
  await page.evaluate(() => {
    window.submissionFixtureBackups = ['aamas-2027', 'mlsys-2027', 'ida-2027'].map(id => {
      const row = document.querySelector(`[data-deadline-group][data-edition="${id}"]`);
      const original = deadlineData.get(row);
      const time = at => Date.parse(`2026-11-${at}T12:00:00Z`);
      const details = id === 'aamas-2027'
        ? [{type: 'full_paper', time: time('01')}]
        : id === 'mlsys-2027'
          ? [{type: 'full_paper', time: Date.now() - 1}, {type: 'camera_ready', time: time('05')}]
          : [{type: 'full_paper', time: time('10')}];
      deadlineData.set(row, details);
      return [row, original];
    });
    applyFilters();
  });
  assert.equal(await timeLeft(mlsys).innerText(), 'Closed');
  assert.deepEqual(await page.locator('[data-deadline-group]:visible').evaluateAll(rows =>
    rows.map(row => row.dataset.edition).filter(id => ['aamas-2027', 'mlsys-2027', 'ida-2027'].includes(id))),
  ['aamas-2027', 'mlsys-2027', 'ida-2027']);
  await page.evaluate(() => {
    for (const [row, original] of window.submissionFixtureBackups) deadlineData.set(row, original);
    delete window.submissionFixtureBackups;
    Date.now = () => Date.parse('2026-10-06T12:00:00Z');
    applyFilters();
  });
  const renderErrors = await page.locator('[data-deadline-group]').evaluateAll(rows =>
    rows.filter(row => !row.hidden).flatMap(row => {
      const state = stateByRow.get(row);
      const summary = [...row.querySelectorAll('[data-deadline-row]')].find(detail => !detail.hidden);
      const expectedTime = state.kind === 'closed' ? 'Closed' : state.action
        ? countdownText(state.action.time, Date.now(), state.action.estimated, state.action.approximate_time)
        : '\u2014';
      return summary?.dataset.deadlineType === state.milestone.type &&
        Date.parse(summary.querySelector('time').dateTime) === state.milestone.time &&
        row.querySelector('[data-time-left]').textContent === expectedTime
        ? [] : [row.dataset.edition];
    }));
  assert.deepEqual(renderErrors, [], 'Every visible edition must match its selected countdown and collapsed action');
  if (opportunitiesOnly) await page.locator('#open-only').check();
  console.log(`Submission behavior passed: AAMAS/MLSys transitions and ${cases.length} route fixtures.`);
}
