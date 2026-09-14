import React from 'react';

/**
 * Skeleton — a content-shaped loading placeholder.
 *
 * Render one or more shimmer bars whose dimensions match the real content
 * they stand in for, so resolving the data causes zero layout shift. Compose
 * several <Skeleton> atoms to build a silhouette of a card, row, or stat.
 *
 * Accessibility: the wrapper is a `role="status"` / `aria-busy` live region
 * with an accessible "Loading…" name; the visual bars are aria-hidden so a
 * screen reader announces the load once, not once per bar.
 *
 * Motion: the shimmer animation is supplied by the `.skeleton-shimmer` class
 * (see styles/global.css), which a `prefers-reduced-motion` media query
 * downgrades to a gentle pulse. Colours come from the `--skeleton-base` /
 * `--skeleton-highlight` theme tokens, so light and dark both work.
 *
 * @param {object}        props
 * @param {'rect'|'text'|'circle'} [props.variant='rect']  Silhouette shape.
 * @param {number|string} [props.width]   Bar width. Number → px; string verbatim.
 * @param {number|string} [props.height]  Bar height. Number → px; string verbatim.
 * @param {number}        [props.count=1] How many stacked bars (text lines).
 * @param {number|string} [props.radius]  Border-radius override.
 * @param {number|string} [props.gap='0.5rem'] Space between stacked bars.
 * @param {string}        [props.className] Extra class(es) on the wrapper.
 * @param {object}        [props.style]   Extra inline style on the wrapper.
 * @param {string}        [props.ariaLabel='Loading…'] Accessible name.
 */
const toCss = (value) => (typeof value === 'number' ? `${value}px` : value);

function Skeleton({
  variant = 'rect',
  width,
  height,
  count = 1,
  radius,
  gap = '0.5rem',
  className = '',
  style = {},
  ariaLabel = 'Loading…',
  ...rest
}) {
  const isCircle = variant === 'circle';
  const isText = variant === 'text';

  const resolvedWidth = width ?? (isCircle ? (height ?? '2.5rem') : '100%');
  const resolvedHeight =
    height ?? (isCircle ? (width ?? '2.5rem') : isText ? '0.85em' : '1rem');
  const resolvedRadius = radius ?? (isCircle ? '50%' : isText ? '0.25rem' : '0.375rem');

  const lines = Math.max(1, count);

  // The last line of a multi-line text block is shorter, like a real paragraph.
  const barWidth = (index) =>
    isText && lines > 1 && index === lines - 1 ? '65%' : toCss(resolvedWidth);

  return (
    <div
      data-testid="skeleton"
      role="status"
      aria-busy="true"
      aria-label={ariaLabel}
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap,
        width: isCircle ? 'fit-content' : undefined,
        ...style,
      }}
      {...rest}
    >
      {Array.from({ length: lines }).map((_, index) => (
        <span
          key={index}
          data-testid="skeleton-bar"
          aria-hidden="true"
          className="skeleton-shimmer"
          style={{
            display: 'block',
            width: barWidth(index),
            height: toCss(resolvedHeight),
            borderRadius: resolvedRadius,
            flexShrink: 0,
          }}
        />
      ))}
    </div>
  );
}

export default Skeleton;
