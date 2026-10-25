  // —— 公式排版：文本里的 $…$（行内）/ $$…$$（独立一行）按 TeX 语法离线转成 MathML，
  //    浏览器用数学字体按论文格式排版。支持 ^ _ {} \frac \sqrt \hat \bar \tilde \vec \mathbf \mathrm \text
  //    \operatorname \mathcal \mathbb \left \right \class{色类}{…}、希腊字母与常用符号；也认 ∇ ᵀ ² ₀ x̂ ᾱ 等 Unicode 写法。
  const TEX = (() => {
    const GREEK = { alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ϵ', varepsilon: 'ε', zeta: 'ζ', eta: 'η', theta: 'θ', iota: 'ι', kappa: 'κ', lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π', rho: 'ρ', sigma: 'σ', tau: 'τ', upsilon: 'υ', phi: 'ϕ', varphi: 'φ', chi: 'χ', psi: 'ψ', omega: 'ω', ell: 'ℓ',
      Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π', Sigma: 'Σ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω' };
    const OPS = { cdot: '⋅', times: '×', div: '÷', pm: '±', mp: '∓', le: '≤', leq: '≤', ge: '≥', geq: '≥', ne: '≠', neq: '≠', approx: '≈', sim: '∼', equiv: '≡', propto: '∝',
      in: '∈', notin: '∉', subset: '⊂', cup: '∪', cap: '∩', to: '→', rightarrow: '→', leftarrow: '←', gets: '←', Rightarrow: '⇒', Leftarrow: '⇐', iff: '⇔', mapsto: '↦',
      infty: '∞', nabla: '∇', partial: '∂', sum: '∑', prod: '∏', int: '∫', top: '⊤', mid: '∣', forall: '∀', exists: '∃', circ: '∘', odot: '⊙', otimes: '⊗', oplus: '⊕',
      land: '∧', wedge: '∧', lor: '∨', vee: '∨', neg: '¬', lnot: '¬',
      lfloor: '⌊', rfloor: '⌋', lceil: '⌈', rceil: '⌉', langle: '⟨', rangle: '⟩', lVert: '‖', rVert: '‖', Vert: '‖', lvert: '|', rvert: '|', '|': '‖', '{': '{', '}': '}',
      ldots: '…', cdots: '⋯', dots: '…', '#': '#', '%': '%', '&': '&', _: '_', '$': '$' };
    const FN = new Set('max min exp log ln sin cos tan tanh sigmoid arg det diag std var sup inf lim softmax argmin argmax'.split(' '));
    const ACC = { hat: 'ˆ', widehat: 'ˆ', bar: '―', overline: '―', tilde: '˜', widetilde: '˜', vec: '→', dot: '˙', ddot: '¨' };
    const SPACE = { ',': '0.17em', ':': '0.22em', ';': '0.28em', ' ': '0.28em', quad: '1em', qquad: '2em', '!': '-0.17em' };
    const SUP = { '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', '⁺': '+', '⁻': '-', 'ᵀ': '\\top ', 'ⁱ': 'i', 'ⁿ': 'n', 'ᵈ': 'd', 'ᵗ': 't' };
    const SUB = { '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9', '₊': '+', '₋': '-', 'ₖ': 'k', 'ᵢ': 'i', 'ⱼ': 'j', 'ₜ': 't', 'ₙ': 'n', 'ₘ': 'm', 'ₓ': 'x' };
    const COMB = { '̂': 'ˆ', '̄': '―', '̅': '―', '̃': '˜', '̇': '˙', '⃗': '→' };
    const PRE = { 'ᾱ': 'ᾱ', 'ᾰ': 'ᾰ' };
    const x = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const styled = (s, A, a, D) => [...s].map(c => c >= 'A' && c <= 'Z' ? String.fromCodePoint(A + c.charCodeAt(0) - 65)
      : c >= 'a' && c <= 'z' ? String.fromCodePoint(a + c.charCodeAt(0) - 97) : D && c >= '0' && c <= '9' ? String.fromCodePoint(D + c.charCodeAt(0) - 48) : c).join('');
    const CAL = { B: 'ℬ', E: 'ℰ', F: 'ℱ', H: 'ℋ', I: 'ℐ', L: 'ℒ', M: 'ℳ', R: 'ℛ' };
    const BB = { C: 'ℂ', H: 'ℍ', N: 'ℕ', P: 'ℙ', Q: 'ℚ', R: 'ℝ', Z: 'ℤ' };
    const cache = new Map();

    function convert(src, display) {
      const key = (display ? 'D' : 'I') + src;
      if (cache.has(key)) return cache.get(key);
      let s = src.replace(/[ᾱᾰ]/g, c => PRE[c]), i = 0;
      const peek = () => s[i];
      const skipWs = () => { while (i < s.length && /\s/.test(s[i])) i++; };
      const readName = () => {
        if (/[A-Za-z]/.test(s[i])) { const m = /^[A-Za-z]+/.exec(s.slice(i))[0]; i += m.length; return m; }
        return s[i++] || '';
      };
      const readRaw = () => { // \text{…} 等的原文参数
        skipWs();
        if (s[i] !== '{') return s[i++] || '';
        let d = 0, j = i;
        for (; j < s.length; j++) { if (s[j] === '{') d++; else if (s[j] === '}' && --d === 0) break; }
        const t = s.slice(i + 1, j); i = j + 1; return t;
      };
      const arg = () => { skipWs(); const a = atom(); return a == null ? '<mrow></mrow>' : a; };
      const mrow = list => list.length === 1 ? list[0] : `<mrow>${list.join('')}</mrow>`;
      const sub = t => convertInner(t);
      // 不在 \left…\right 里的括号保持原高，不随分式拉伸
      const mo = c => c === '/' ? '<mo lspace="0" rspace="0">/</mo>' : /^[()[\]{}|‖⌊⌋⌈⌉⟨⟩]$/.test(c) ? `<mo stretchy="false">${x(c)}</mo>` : `<mo>${x(c)}</mo>`;

      const delim = () => { skipWs(); let d = s[i++] || '.'; if (d === '\\') { const m = readName(); d = OPS[m] || m; } return d === '.' ? '' : `<mo>${x(d)}</mo>`; };
      function seq(stop, inLeft) {
        const out = [];
        while (i < s.length) {
          skipWs();
          if (i >= s.length) break;
          if (stop && s[i] === stop) { i++; break; }
          if (inLeft && s.startsWith('\\right', i)) break;
          const a = atom();
          if (a == null) continue;
          out.push(scripts(a));
          if (/^<mi>[A-Za-z]{2,}<\/mi>$/.test(a)) { skipWs(); if (s[i] !== '(') out.push('<mspace width="0.17em"></mspace>'); } // \max c 之间留细空
        }
        return out;
      }
      function scripts(base) {
        let lo = null, hi = null;
        for (;;) {
          const c = s[i];
          if (c === '^') { i++; hi = arg(); }
          else if (c === '_') { i++; lo = arg(); }
          else if (c === "'") { let p = ''; while (s[i] === "'") { p += '′'; i++; } hi = `<mo>${p}</mo>`; }
          else if (c && COMB[c]) { base = `<mover accent="true">${base}<mo>${COMB[c]}</mo></mover>`; i++; }
          else if (c && SUP[c]) { let t = ''; while (SUP[s[i]]) t += SUP[s[i++]]; hi = sub(t); }
          else if (c && SUB[c]) { let t = ''; while (SUB[s[i]]) t += SUB[s[i++]]; lo = sub(t); }
          else if (c && /\s/.test(c) && /^\s*[\^_]/.test(s.slice(i))) skipWs();
          else break;
        }
        if (lo && hi) return `<msubsup>${base}${lo}${hi}</msubsup>`;
        if (lo) return `<msub>${base}${lo}</msub>`;
        if (hi) return `<msup>${base}${hi}</msup>`;
        return base;
      }
      function atom() {
        const c = s[i];
        if (c === '{') { i++; return mrow(seq('}')); }
        if (c === '}') { i++; return null; }
        if (c === '\\') {
          i++;
          const n = readName();
          if (n in GREEK) return /[A-Z]/.test(n[0]) ? `<mi mathvariant="normal">${GREEK[n]}</mi>` : `<mi>${GREEK[n]}</mi>`;
          if (n in SPACE) return `<mspace width="${SPACE[n]}"></mspace>`;
          if (FN.has(n)) return `<mi>${n}</mi>`;
          if (n in ACC) return `<mover accent="true">${arg()}<mo>${ACC[n]}</mo></mover>`;
          if (n in OPS) return mo(OPS[n]);
          switch (n) {
            case 'frac': case 'dfrac': case 'tfrac': { const a = arg(); return `<mfrac>${a}${arg()}</mfrac>`; }
            case 'sqrt': return `<msqrt>${arg()}</msqrt>`;
            case 'text': case 'textrm': case 'mbox': return `<mtext>${x(readRaw())}</mtext>`;
            case 'mathrm': case 'operatorname': { const t = readRaw(); return t.length === 1 ? `<mi mathvariant="normal">${x(t)}</mi>` : `<mi>${x(t)}</mi>`; }
            case 'mathbf': return `<mi>${x(styled(readRaw(), 0x1D400, 0x1D41A, 0x1D7CE))}</mi>`;
            case 'boldsymbol': case 'bm': return `<mi>${x(styled(readRaw(), 0x1D468, 0x1D482, 0x1D7CE))}</mi>`;
            case 'mathcal': return `<mi>${[...readRaw()].map(ch => CAL[ch] || styled(ch, 0x1D49C, 0x1D4B6)).join('')}</mi>`;
            case 'mathbb': return `<mi>${[...readRaw()].map(ch => BB[ch] || styled(ch, 0x1D538, 0x1D552, 0x1D7D8)).join('')}</mi>`;
            case 'class': { const cls = readRaw().replace(/[^\w -]/g, ''); return `<mrow class="${cls}">${arg()}</mrow>`; }
            case 'left': {
              const open = delim(), inner = seq(null, true);
              const close = s.startsWith('\\right', i) ? (i += 6, delim()) : '';
              return `<mrow>${open}${inner.join('')}${close}</mrow>`;
            }
            case 'right': case 'big': case 'Big': case 'bigl': case 'bigr': case 'Bigl': case 'Bigr': return delim() || null;
            default: return `<mtext>\\${x(n)}</mtext>`;
          }
        }
        let m;
        if ((m = /^\d+(?:\.\d+)?/.exec(s.slice(i)))) { i += m[0].length; return `<mn>${m[0]}</mn>`; }
        if (/[A-Za-z]/.test(c)) { i++; return `<mi>${c}</mi>`; }
        if (/[α-ωϵϕℓ]/.test(c)) { i++; return `<mi>${c}</mi>`; }
        if (/[Α-Ω]/.test(c)) { i++; return `<mi mathvariant="normal">${c}</mi>`; }
        if (/[　-鿿＀-￯]/.test(c)) { // 中文说明文字
          m = /^[　-鿿＀-￯]+/.exec(s.slice(i))[0]; i += m.length; return `<mtext>${x(m)}</mtext>`;
        }
        i++;
        if (c === '-') return '<mo>−</mo>';
        if (c === '*') return '<mo>∗</mo>';
        if (c === '~') return '<mspace width="0.28em"></mspace>';
        if (c === '·') return '<mo>⋅</mo>';
        if (c === '∑' || c === '∏') return `<mo>${c}</mo>`;
        return mo(c);
      }
      function convertInner(t) { const [s0, i0] = [s, i]; s = t; i = 0; const r = mrow(seq()); s = s0; i = i0; return r; }

      const body = mrow(seq());
      const out = `<math${display ? ' display="block"' : ''}>${body}</math>`;
      cache.set(key, out);
      return out;
    }

    // 把一个文本节点里的 $…$ / $$…$$ 换成 MathML；返回是否替换
    const SKIP = '.code-card, script, style, textarea, math, svg, title, .no-tex';
    function typesetText(node) {
      const t = node.nodeValue;
      if (!t || t.indexOf('$') < 0) return false;
      const host = node.parentElement;
      if (!host || host.closest(SKIP)) return false;
      const re = /\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g;
      let html = '', last = 0, hit = false, mm;
      while ((mm = re.exec(t))) {
        hit = true;
        html += x(t.slice(last, mm.index)) + (mm[1] != null ? convert(mm[1].trim(), true) : convert(mm[2].trim(), false));
        last = re.lastIndex;
      }
      if (!hit) return false;
      html += x(t.slice(last));
      const tpl = document.createElement('template');
      tpl.innerHTML = html;
      node.replaceWith(tpl.content);
      return true;
    }
    function typeset(root) {
      if (!root) return;
      if (root.nodeType === 3) { typesetText(root); return; }
      if (root.nodeType !== 1 && root.nodeType !== 11) return;
      if (root.nodeType === 1 && root.closest(SKIP)) return;
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), list = [];
      while (w.nextNode()) if (w.currentNode.nodeValue.indexOf('$') >= 0) list.push(w.currentNode);
      list.forEach(typesetText);
    }
    // DEMO 直接写 innerHTML / textContent 的内容由 MutationObserver 兜底排版；render 结束时同步冲刷一次
    const handle = recs => { for (const r of recs) { if (r.type === 'characterData') typeset(r.target); else r.addedNodes.forEach(typeset); } };
    const mo = new MutationObserver(handle);
    mo.observe(document.body, { childList: true, subtree: true, characterData: true });
    const flush = () => handle(mo.takeRecords());
    return { convert, typeset, flush };
  })();
  // 带公式的 innerHTML 写入：按原始字符串判断是否变化（排版后 innerHTML 已不同于源串）
  function setHTML(node, html) {
    html = html == null ? '' : String(html);
    if (node._raw === html) return false;
    node._raw = html;
    node.innerHTML = html;
    TEX.typeset(node);
    return true;
  }
