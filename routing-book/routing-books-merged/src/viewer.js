// Merged-book viewer: renders one chapter at a time from <template> elements.
// Route format: #<book>/<chapter>[/<anchor>]. Chapter HTML lives in <template id="t--<book>--<chapter>">.
(function () {
  'use strict';

  const LIBRARY = JSON.parse(document.getElementById('library-data').textContent);
  const sideEl = document.getElementById('side');
  const mainEl = document.getElementById('main');
  const toggleEl = document.querySelector('.v-toggle');
  const searchEl = document.querySelector('.v-search');
  const COPY_RESET_MS = 1200;
  const PROMPT_PATTERNS = [
    /^RP\/\d.*?[#$]\s?(.*)$/,               // IOS-XR
    /^[\w.-]+@[\w.-]+[>#%]\s?(.*)$/,        // Junos
    /^[\w-]+(?:\(config[^)]*\))?[>#]\s?(.*)$/, // IOS / EOS
  ];

  const flatChapters = LIBRARY.flatMap((b) => b.chapters.map((c) => ({ book: b, chapter: c })));

  function escapeHtml(text) {
    return text.replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  }

  function renderSide(current) {
    const html = LIBRARY.map((b) => {
      const isOpen = current && current.book.id === b.id ? ' open' : '';
      const items = b.chapters.map((c) => {
        const isActive = current && current.book.id === b.id && current.chapter.id === c.id;
        const secs = isActive
          ? c.sections.map((s) => `<li><a class="v-sec" href="#${b.id}/${c.id}/${s.anchor}">${escapeHtml(s.title)}</a></li>`).join('')
          : '';
        return `<li data-search="${escapeHtml((c.title + ' ' + b.title).toLowerCase())}"><a href="#${b.id}/${c.id}"${isActive ? ' class="active"' : ''}>${escapeHtml(c.title)}</a>${secs}</li>`;
      }).join('');
      return `<details${isOpen}><summary>${escapeHtml(b.title)}</summary><ol>${items}</ol></details>`;
    }).join('');
    sideEl.innerHTML = `<p><a href="#">ホーム (全 ${LIBRARY.length} 冊)</a></p>${html}`;
    applySearch();
  }

  function applySearch() {
    const q = searchEl.value.trim().toLowerCase();
    sideEl.querySelectorAll('li[data-search]').forEach((li) => {
      li.classList.toggle('v-hidden', q !== '' && !li.dataset.search.includes(q));
    });
    if (q) sideEl.querySelectorAll('details').forEach((d) => { d.open = true; });
  }

  function renderHome() {
    const books = LIBRARY.map((b) => `<li><a href="#${b.id}/${b.chapters[0].id}">${escapeHtml(b.title)}</a> — ${b.chapters.length} 章</li>`).join('');
    mainEl.innerHTML = `<div class="v-home"><h1>ルーティング技術書 合本</h1><p>${LIBRARY.length} 冊・${flatChapters.length} 章を 1 ファイルにまとめたものです。左の目次から章を選んでください。</p><ul>${books}</ul></div>`;
    renderSide(null);
    window.scrollTo(0, 0);
  }

  function paneText(pre) {
    return pre.innerText.split('\n').map((line) => {
      const m = PROMPT_PATTERNS.map((p) => line.match(p)).find(Boolean);
      return m ? m[m.length - 1] : line;
    }).filter((line) => line.trim() !== '').join('\n');
  }

  function addCopyButtons(root) {
    if (!navigator.clipboard) return;
    root.querySelectorAll('.pane-config').forEach((pane) => {
      const title = pane.querySelector('.pane-title');
      const pre = pane.querySelector('pre');
      if (!title || !pre) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.textContent = 'copy';
      btn.addEventListener('click', () => {
        navigator.clipboard.writeText(paneText(pre))
          .then(() => { btn.textContent = 'copied!'; })
          .catch(() => { btn.textContent = 'failed'; })
          .finally(() => setTimeout(() => { btn.textContent = 'copy'; }, COPY_RESET_MS));
      });
      title.appendChild(btn);
    });
  }

  function renderChapter(pos, anchor) {
    const { book, chapter } = flatChapters[pos];
    const tpl = document.getElementById(`t--${book.id}--${chapter.id}`);
    if (!tpl) {
      mainEl.innerHTML = '<div class="v-home"><p>章が見つかりません。目次から選び直してください。</p></div>';
      return;
    }
    const prev = flatChapters[pos - 1];
    const next = flatChapters[pos + 1];
    const link = (e, label) => `<a href="#${e.book.id}/${e.chapter.id}">${label}</a>`;
    const wrap = document.createElement('div');
    wrap.className = book.scope;
    wrap.appendChild(tpl.content.cloneNode(true));
    const pager = document.createElement('nav');
    pager.className = 'v-pager';
    pager.innerHTML = (prev ? link(prev, `← ${escapeHtml(prev.chapter.title)}`) : '<span></span>') +
                      (next ? link(next, `${escapeHtml(next.chapter.title)} →`) : '<span></span>');
    mainEl.replaceChildren(wrap, pager);
    addCopyButtons(wrap);
    renderSide(flatChapters[pos]);
    const target = anchor ? document.getElementById(anchor) : null;
    if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
  }

  function route() {
    const [bookId, chapterId, anchor] = decodeURIComponent(location.hash.replace(/^#/, '')).split('/');
    sideEl.classList.remove('open');
    toggleEl.setAttribute('aria-expanded', 'false');
    if (!bookId) { renderHome(); return; }
    const pos = flatChapters.findIndex((e) => e.book.id === bookId && (!chapterId || e.chapter.id === chapterId));
    if (pos < 0) { renderHome(); return; }
    const isSameChapter = mainEl.dataset.pos === String(pos);
    if (isSameChapter && anchor) {
      const target = document.getElementById(anchor);
      if (target) { target.scrollIntoView(); return; }
    }
    mainEl.dataset.pos = String(pos);
    renderChapter(pos, anchor);
  }

  toggleEl.addEventListener('click', () => {
    const isOpen = sideEl.classList.toggle('open');
    toggleEl.setAttribute('aria-expanded', String(isOpen));
  });
  searchEl.addEventListener('input', applySearch);
  window.addEventListener('hashchange', route);
  route();
})();
