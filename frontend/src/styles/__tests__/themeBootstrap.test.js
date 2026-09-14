/**
 * Regression gate for the pre-paint theme bootstrap.
 *
 * The bug this guards against: the theme used to be applied by JavaScript from
 * a React passive effect, which runs after the first paint, so every load
 * flashed light before darkening.
 *
 * jsdom can never reproduce that — it does not load public/index.html, and its
 * CSSOM drops var() from inline styles, so no rendering assertion here could
 * fail on the real bug. These tests therefore assert the *contract* that keeps
 * the fix in place, reading the two files off disk. Only a browser (see the
 * Playwright/DevTools filmstrip in the MR) can prove the painted frames.
 */

import fs from 'fs';
import path from 'path';

import {
  applyTheme,
  prefersDarkScheme,
  readStoredTheme,
  resolveInitialTheme,
  storeThemeChoice,
  THEME_STORAGE_KEY,
} from '../theme';

const FRONTEND_ROOT = path.resolve(__dirname, '../../..');
const INDEX_HTML = fs.readFileSync(path.join(FRONTEND_ROOT, 'public/index.html'), 'utf8');
const THEME_CSS = fs.readFileSync(path.join(FRONTEND_ROOT, 'src/styles/theme.css'), 'utf8');

/** Pull the declarations of one rule block out of a stylesheet. */
const blockFor = (css, selector) => {
  const at = css.indexOf(selector + ' {');
  if (at === -1) return null;
  return css.slice(at, css.indexOf('}', at));
};

/** Token names declared inside a block, e.g. ['--primary', ...]. */
const tokensIn = (block) => (block.match(/^\s*(--[\w-]+):/gm) || []).map((m) => m.trim().replace(':', ''));

describe('pre-paint theme bootstrap (public/index.html)', () => {
  it('stamps the theme before the render-blocking stylesheet', () => {
    // A parser-inserted script after a pending <link rel=stylesheet> is blocked
    // until that sheet loads. If the boot script ever moves below the Bootstrap
    // link, the decision waits on a cross-origin CDN round trip.
    expect(INDEX_HTML.indexOf('<script>')).toBeLessThan(INDEX_HTML.indexOf('rel="stylesheet"'));
  });

  it('sets data-theme and data-bs-theme on the document element', () => {
    expect(INDEX_HTML).toContain("setAttribute('data-theme'");
    expect(INDEX_HTML).toContain("setAttribute('data-bs-theme'");
  });

  it('reads the same storage key, and the same values, as theme.js', () => {
    expect(INDEX_HTML).toContain("getItem('isDarkTheme')");
    expect(THEME_STORAGE_KEY).toBe('isDarkTheme');
    expect(INDEX_HTML).toContain("stored === 'true'");
    expect(INDEX_HTML).toContain("stored === 'false'");
    // JSON.stringify is what writes the value; it must produce those strings.
    expect(JSON.stringify(true)).toBe('true');
    expect(JSON.stringify(false)).toBe('false');
  });

  it('guards the storage read so private mode falls through to the OS', () => {
    expect(INDEX_HTML).toContain('try {');
    expect(INDEX_HTML).toContain('prefers-color-scheme: dark');
  });

  it('contains no percent sign, which CRA would interpolate', () => {
    // InterpolateHtmlPlugin rewrites %TOKEN% sequences anywhere in this file.
    const script = INDEX_HTML.slice(INDEX_HTML.indexOf('<script>'), INDEX_HTML.indexOf('</script>'));
    expect(script).not.toContain('%');
  });

  it('never overrides an explicit light choice with the OS preference', () => {
    // The CSS fallback must be guarded. An unconditional dark media query (or a
    // bare <meta name="color-scheme" content="light dark">) inverts the flash
    // for a light-choosing user on a dark OS.
    expect(INDEX_HTML).toContain("html:not([data-theme='light'])");
    expect(INDEX_HTML).not.toContain('name="color-scheme"');
  });

  it('does not freeze transitions without releasing them', () => {
    // A `transition: none` latch is only safe with matching release code. If
    // the stamp comes back, the release must come with it.
    if (INDEX_HTML.includes('data-theme-boot')) {
      const indexJs = fs.readFileSync(path.join(FRONTEND_ROOT, 'src/index.js'), 'utf8');
      expect(indexJs).toContain('data-theme-boot');
    }
  });
});

describe('static theme tokens (src/styles/theme.css)', () => {
  const light = blockFor(THEME_CSS, ':root');
  const dark = blockFor(THEME_CSS, ":root[data-theme='dark']");

  it('declares both palettes', () => {
    expect(light).not.toBeNull();
    expect(dark).not.toBeNull();
  });

  it('defines an identical token set in both palettes', () => {
    const lightTokens = tokensIn(light).sort();
    const darkTokens = tokensIn(dark).sort();
    expect(darkTokens).toEqual(lightTokens);
    expect(lightTokens.length).toBeGreaterThan(30);
  });

  it('declares color-scheme for both palettes', () => {
    expect(light).toContain('color-scheme: light');
    expect(dark).toContain('color-scheme: dark');
  });

  // Pre-existing debt, deliberately NOT fixed alongside the flash: these four
  // are referenced but have never been declared, so the 13 declarations using
  // them currently draw nothing. Defining them changes rendered pixels, which
  // does not belong in a flash fix -- it needs its own visual review.
  //
  // The assertion below is an allowlist rather than a deletion so that a NEW
  // undeclared token still fails the build. Shrink this list as they are
  // adopted; it should reach [] and then the allowlist can go.
  const KNOWN_UNDECLARED = ['--bg-light', '--border-light', '--hover-bg', '--primary-light'];

  it('defines every token the app consumes, bar the known-undeclared four', () => {
    const declared = new Set(tokensIn(light));
    const srcDir = path.join(FRONTEND_ROOT, 'src');
    const walk = (dir) =>
      fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) return walk(full);
        return /\.(js|css)$/.test(entry.name) ? [full] : [];
      });
    const used = new Set();
    walk(srcDir).forEach((file) => {
      // Strip block comments first: the prose in these files uses a var()
      // placeholder to explain the fix, which is not a real consumption site.
      const text = fs.readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
      (text.match(/var\((--[\w-]+)/g) || []).forEach((m) => used.add(m.replace('var(', '')));
    });
    const undeclared = [...used].filter((token) => !declared.has(token)).sort();
    expect(undeclared).toEqual(KNOWN_UNDECLARED);
  });

  it('keeps the duplicated ground colours in step with index.html', () => {
    // These two literals exist twice on purpose (index.html must paint before
    // this stylesheet exists). This test is the only thing stopping them from
    // drifting apart silently.
    expect(light).toContain('--background: #f8fafc');
    expect(dark).toContain('--background: #1e293b');
    expect(INDEX_HTML).toContain('background-color: #f8fafc');
    expect(INDEX_HTML).toContain('background-color: #1e293b');
  });

  it('qualifies the document ground by attribute in BOTH palettes', () => {
    // index.html's `html[data-theme='dark']` is specificity (0,1,1). A bare
    // `html` rule here would be (0,0,1) and would lose to it in dark mode only
    // -- decoupling --background from the canvas in one palette but not the
    // other, which is invisible until someone retunes the dark background.
    expect(THEME_CSS).toContain("html[data-theme='light'],\nhtml[data-theme='dark'] {");
    expect(THEME_CSS).toContain('background-color: var(--background)');
  });

  it('keeps the palettes out of JavaScript', () => {
    const themeJs = fs.readFileSync(path.join(FRONTEND_ROOT, 'src/styles/theme.js'), 'utf8');
    expect(themeJs).not.toContain('setProperty');
    expect(themeJs).not.toContain('themeVariables');
  });
});

describe('theme state (src/styles/theme.js)', () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    document.documentElement.removeAttribute('data-bs-theme');
  });

  it('reports no stored choice when nothing is stored', () => {
    expect(readStoredTheme()).toBeNull();
  });

  it('round-trips an explicit choice', () => {
    storeThemeChoice(true);
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('true');
    expect(readStoredTheme()).toBe(true);
    storeThemeChoice(false);
    expect(readStoredTheme()).toBe(false);
  });

  it('treats a junk stored value as no choice', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'banana');
    expect(readStoredTheme()).toBeNull();
  });

  it('falls back to the OS preference when no choice is stored', () => {
    expect(resolveInitialTheme()).toBe(prefersDarkScheme());
  });

  it('prefers an explicit choice over the OS preference', () => {
    storeThemeChoice(true);
    expect(resolveInitialTheme()).toBe(true);
  });

  it('applies the theme as one attribute swap, not inline properties', () => {
    applyTheme(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark');
    expect(document.documentElement.getAttribute('style')).toBeNull();

    applyTheme(false);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});
