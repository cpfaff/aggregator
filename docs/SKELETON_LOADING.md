# Skeleton Loading

**Component:** `src/components/ui/Skeleton.js`
**Tokens:** `src/styles/theme.css` (`--skeleton-base`, `--skeleton-highlight`)
**Animation:** `src/styles/global.css` (`shimmer` keyframe, `.skeleton-shimmer`)
**Status:** Reference

A skeleton is a **content-shaped placeholder** shown while async data loads. It
is a silhouette of the real content — same dimensions, same arrangement — so
when the data resolves there is **zero layout shift**. We use one shared
`<Skeleton>` atom across every async-data surface instead of a spinner, because
a content-shaped placeholder communicates *what* is loading and *where* it will
land, which a generic spinner cannot.

---

## Why skeletons, not spinners

| | Spinner | Skeleton |
|---|---|---|
| Communicates layout | No | Yes — mirrors the final shape |
| Layout shift on resolve | Common | None (dimensions match) |
| Perceived speed | Slower | Faster (progress feels structural) |
| Reduced-motion friendly | Spins regardless | Degrades to a calm pulse |

The 32px ring spinner has been removed from the migrated data surfaces. The
`spin` keyframe is **kept** for genuinely indeterminate, in-place actions —
submit buttons and the login flow — which are out of scope here.

---

## Design rules

1. **Match the silhouette.** A skeleton must resemble the content it replaces:
   a grid of cards → a grid of card-shaped blocks; a stat → a big number block
   over a label block. Reuse the real layout's container, grid, and spacing.
2. **No layout shift (no CLS).** Size each bar to the resolved content's box.
   Render the skeleton *inside the same wrapper* the content will occupy.
3. **No spinner → skeleton flash.** Show the skeleton from the first render of
   the loading state. Never show a spinner first and swap to a skeleton.
4. **Announce once.** Each `<Skeleton>` is a single `role="status"` /
   `aria-busy` region named "Loading…"; its visual bars are `aria-hidden`, so
   assistive tech announces the load once, not once per bar.
5. **Respect motion preferences.** The shimmer is defined on the
   `.skeleton-shimmer` class so a `prefers-reduced-motion: reduce` media query
   can swap the travelling sweep for a gentle `pulse`. Never inline the
   animation — an inline style cannot be overridden by the media query.
6. **Theme via tokens.** Bars draw from `--skeleton-base` (resting fill) and
   `--skeleton-highlight` (sweep), defined for both light and dark in
   `theme.css`. Never hard-code skeleton greys.

---

## API

```jsx
import Skeleton from '../ui/Skeleton';

<Skeleton />                                  // one rect bar, full width
<Skeleton variant="text" count={3} />         // 3 lines, last one shorter
<Skeleton variant="circle" width={48} />      // 48×48 avatar circle
<Skeleton width={120} height={32} radius="0.5rem" />
```

| Prop | Type | Default | Notes |
|---|---|---|---|
| `variant` | `'rect' \| 'text' \| 'circle'` | `'rect'` | Silhouette shape. `text` stacks lines and shortens the last; `circle` is fully rounded. |
| `width` | `number \| string` | `'100%'` (`'2.5rem'` for circle) | Number → `px`; string used verbatim (`'80%'`, `'8rem'`). |
| `height` | `number \| string` | `'1rem'` rect / `'0.85em'` text / `width` for circle | Number → `px`; string verbatim. |
| `count` | `number` | `1` | Number of stacked bars (text lines). |
| `radius` | `number \| string` | per variant | Border-radius override. |
| `gap` | `number \| string` | `'0.5rem'` | Space between stacked bars. |
| `className` | `string` | `''` | Extra class(es) on the wrapper region. |
| `style` | `object` | `{}` | Extra inline style on the wrapper region. |
| `ariaLabel` | `string` | `'Loading…'` | Accessible name of the status region. |

Unknown props spread onto the wrapper `<div>`.

---

## Building a surface skeleton

Compose atoms inside the **same container** the real content uses. Example — a
provider card grid placeholder that matches the loaded grid 1:1:

```jsx
{isLoading ? (
  <div style={gridStyle} aria-label="Loading providers">
    {Array.from({ length: 6 }).map((_, i) => (
      <div key={i} style={cardStyle}>
        <Skeleton variant="text" width="60%" height="1.25rem" />
        <Skeleton variant="text" count={2} />
        <Skeleton width="40%" height="0.75rem" />
      </div>
    ))}
  </div>
) : (
  <div style={gridStyle}>{providers.map(renderCard)}</div>
)}
```

---

## Testing pattern

Mirror the never-resolving-promise pattern (`Providers.test.js`). Assert the
skeleton is present while the API promise is unresolved and gone after it
resolves:

```js
test('shows a skeleton while loading', () => {
  apiRequest.mockReturnValue(new Promise(() => {})); // never resolves
  render(<Surface />);
  expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
});

test('skeleton is gone after data loads', async () => {
  apiRequest.mockResolvedValue({ ok: true, json: async () => ({ data: [] }) });
  render(<Surface />);
  await waitFor(() =>
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument()
  );
});
```

Use `getAllByTestId` / `queryAllByTestId` for surfaces that render multiple
skeletons; `data-testid="skeleton-bar"` targets the individual bars.

---

## Where it's used

Migrated to a content-shaped skeleton (the 32px ring removed):

| Surface | Silhouette |
|---|---|
| Providers grid | 6 provider-card placeholders in the real grid |
| Provider detail | breadcrumb + detail card + 3 dataset rows |
| StatCard | number-shaped block (drives LandingPage + dashboards) |
| Public stats dashboard | header + StatCard grid + 2 chart cards |
| Admin dashboard | breadcrumb + title + StatCard grid + chart cards |
| Provider statistics | header + 2 timeline-chart cards |
| User management | 6 user-card placeholders (avatar, roles, actions) |
| `TimeSeriesChart`, `PieChart`, `MultiLineTimeSeriesChart` | in-card chart silhouette |

The `spin` keyframe is intentionally **kept** for indeterminate in-place
actions that are *not* data surfaces: `Button` (submit), the `Login` flow.

Left as plain inline states by design:

- **`App.js` auth bootstrap** (`Loading user data…`) — gates every protected
  route before any page renders, so there is no single content shape to mimic;
  a skeleton would have to guess the silhouette of an unknown destination.
- **`BarChart`** — has no callers, so its (now-dormant) loading state was not
  migrated.
- Out of scope entirely: form-submit buttons, the Login spinner, the
  DatasetCard harvest badge, the static Changelog.
