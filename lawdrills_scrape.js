// Law Drills (Practice Works) wrong-answer scraper.
// Run in Chrome on a COMPLETED set's review page: app.practice.works/practice/set/<id>
// (javascript_tool, top-level await). It writes a JSON object into the page's
// <main> as a <pre>; read it back with get_page_text, then merge it into
// lawdrills_mistakes.json (keyed by set_id + q). Reload the page afterwards.
// Returns "NOT_DONE" when the set has not been sat yet (no score panel).
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  await sleep(2000);
  const aside = document.querySelector('aside');
  if (!aside || !/Score/.test(aside.innerText)) return 'NOT_DONE';
  const AL = aside.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const title = AL[2] || '';
  const score = (AL[AL.indexOf('Score') + 1] || '') + ' ' + (AL[AL.indexOf('Correct') + 1] || '');
  // Subject per question number, from the Topic sort (top-level UPPERCASE heads)
  const topic = [...document.querySelectorAll('[role=radio]')].find(r => r.innerText.trim() === 'Topic');
  const subj = {};
  if (topic) {
    topic.click(); await sleep(1000);
    for (let i = 0; i < 6; i++) {
      const c = [...aside.querySelectorAll('[aria-expanded="false"]')];
      if (!c.length) break; c.forEach(x => x.click()); await sleep(400);
    }
    const L = aside.innerText.split('\n').map(s => s.trim());
    let cur = '';
    for (const s of L.slice(L.indexOf('Topic'))) {
      if (/^[A-Z][A-Z ,&'’-]{6,}$/.test(s)) cur = s;
      const m = s.match(/^(\d+)\.$/); if (m) subj[m[1]] = cur;
    }
  }
  const before = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  const clean = t => (t || '').replace(/Tell me more/g, '').replace(/\s+/g, ' ').trim();
  const btns = [...document.querySelectorAll('button[aria-label*="jump to question"]')]
    .filter(b => !/, correct/.test(b.getAttribute('aria-label')));
  const out = [];
  for (const b of btns) {
    const lab = b.getAttribute('aria-label');
    const n = lab.match(/Question (\d+)/)[1];
    b.click(); await sleep(900);
    const m = document.querySelector('main');
    const opts = [...m.querySelectorAll('[aria-label^="Option "]')];
    const ps = [...m.querySelectorAll('p')].filter(p => !opts.some(o => o.contains(p)));
    const stem = ps.filter(p => opts.length && before(p, opts[0]))
      .map(p => clean(p.innerText)).filter(t => t && !/^Q\d+ — /.test(t)).join(' ');
    const fb = i => ps.filter(p => before(opts[i], p) && (i + 1 >= opts.length || before(p, opts[i + 1])))
      .map(p => clean(p.innerText)).join(' ');
    let picked = '', correct = '', why = '', pickedFb = '';
    opts.forEach((o, i) => {
      const c = o.className.toString(), t = clean(o.innerText);
      if (c.includes('destructive')) { picked = t; pickedFb = fb(i); }
      if (c.includes('border-success')) { correct = t; why = fb(i); }
    });
    out.push({ q: +n, status: /incorrect/.test(lab) ? 'wrong' : 'unanswered',
               subject: subj[n] || '', stem, picked, correct, why, picked_feedback: pickedFb });
  }
  const res = { set_id: location.pathname.split('/').pop(), title, score: score.trim(), mistakes: out };
  const pre = document.createElement('pre'); pre.style.whiteSpace = 'pre-wrap';
  pre.textContent = JSON.stringify(res, null, 1);
  const m0 = document.querySelector('main'); m0.replaceChildren(pre);
  return 'OK ' + out.length;
})()
