/*
 * Theme state. Owns exactly one decision — which palette is active — and
 * nothing about what the palettes contain.
 *
 * The colours live in theme.css as static custom properties. This module used
 * to hold them as a JavaScript object and write all 33 of them onto
 * document.documentElement.style from a React effect, which ran after the
 * first paint and produced a visible light-to-dark flash on every load.
 *
 * The flip side of that move: the very first stamp of `data-theme` is NOT done
 * here. It is done by the inline boot script in public/index.html, during head
 * parsing, before anything paints. This module only keeps the attribute in
 * sync afterwards. The storage contract below is shared with that script and
 * the two must agree.
 */

export const THEME_STORAGE_KEY = 'isDarkTheme';

/**
 * The user's explicit choice, or null if they have never chosen.
 *
 * Guarded: localStorage throws in some private-browsing modes, and the stored
 * value can be anything if it was hand-edited. Anything that is not exactly
 * 'true' or 'false' counts as "no choice", which falls through to the OS.
 */
export const readStoredTheme = () => {
  let stored = null;
  try {
    stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  } catch (error) {
    return null;
  }
  if (stored === 'true') return true;
  if (stored === 'false') return false;
  return null;
};

/** Whether the OS is currently asking for a dark UI. */
export const prefersDarkScheme = () =>
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-color-scheme: dark)').matches;

/**
 * The palette that should be active right now: the explicit choice if there is
 * one, otherwise the OS preference. Mirrors the boot script's branches exactly,
 * so React's first render agrees with what is already on <html>.
 */
export const resolveInitialTheme = () => {
  const stored = readStoredTheme();
  return stored === null ? prefersDarkScheme() : stored;
};

/** Record an explicit choice. Silently ignored if storage is unavailable. */
export const storeThemeChoice = (isDarkTheme) => {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(isDarkTheme));
  } catch (error) {
    /* private mode / storage blocked: the theme still applies for this page */
  }
};

/**
 * Put the palette in force.
 *
 * One attribute swap, not 33 property writes — every colour is already in the
 * stylesheet, keyed on this attribute. `data-bs-theme` is set alongside so
 * Bootstrap's own dark variables track the app.
 */
export const applyTheme = (isDarkTheme) => {
  const theme = isDarkTheme ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-bs-theme', theme);
};

/**
 * Follow the OS while the user has no explicit choice.
 *
 * @param   {(isDark: boolean) => void} onChange
 * @returns {() => void} unsubscribe
 */
export const subscribeToSystemTheme = (onChange) => {
  if (typeof window.matchMedia !== 'function') return () => {};
  const query = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = (event) => {
    // An explicit choice always wins; only drive the theme while there is none.
    if (readStoredTheme() === null) onChange(event.matches);
  };
  // addListener is the pre-2019 Safari spelling; kept as a fallback.
  if (typeof query.addEventListener === 'function') {
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }
  query.addListener(handler);
  return () => query.removeListener(handler);
};
