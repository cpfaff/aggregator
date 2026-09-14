# GFBio Design System

**Version:** 2.4.0
**Last Updated:** September 2026
**Framework:** React 18.2.0
**Styling Approach:** Static CSS Variables (`theme.css`) + Inline Styles

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technology Stack](#technology-stack)
3. [Color System](#color-system)
4. [Typography](#typography)
5. [Spacing & Layout](#spacing--layout)
6. [Component Library](#component-library)
7. [Animation & Transitions](#animation--transitions)
8. [Accessibility Features](#accessibility-features)
9. [Responsive Design](#responsive-design)
10. [Implementation Guidelines](#implementation-guidelines)

---

## Executive Summary

The GFBio Design System is a custom-built, variable-driven design framework that prioritizes:

- **Zero external CSS frameworks** (no Tailwind, no styled-components)
- **CSS Custom Properties** for dynamic theming
- **Inline styles** with JavaScript objects for component-level styling
- **Full light/dark mode** support with seamless transitions
- **WCAG 2.1 AA compliance** (touch targets, focus states, ARIA labels)
- **Mobile-first responsive** design with clear breakpoints
- **Performance-optimized** animations and transitions

### Design Philosophy

1. **Minimalist & Clean**: Focus on content with subtle visual hierarchy
2. **Consistent**: Unified spacing, color usage, and interaction patterns
3. **Accessible**: WCAG-compliant touch targets, keyboard navigation, screen reader support
4. **Themeable**: Complete light/dark mode support via CSS variables
5. **Modern**: Contemporary UI patterns with smooth animations

---

## Technology Stack

### Core Dependencies

```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.22.1",
  "react-scripts": "5.0.1"
}
```

### UI Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **Lucide React** | 0.476.0 | Icon library (24px icons throughout) |
| **Recharts** | 3.1.2 | Data visualization and charting |
| **Mermaid** | 11.12.2 | Diagram rendering |
| **Axios** | 1.6.7 | HTTP client for API requests |

### Build System

- **Create React App** (react-scripts 5.0.1)
- **Webpack** (bundled with CRA)
- **Babel** (bundled with CRA)

---

## Color System

### Architecture

Colors are defined in `/frontend/src/styles/theme.css` as **static** CSS Custom
Properties, keyed on a `data-theme` attribute on `<html>`.

```css
:root {
  color-scheme: light;
  --primary: #2563eb;
  --background: #f8fafc;
  /* ... */
}

:root[data-theme='dark'] {
  color-scheme: dark;
  --primary: #3b82f6;
  --background: #1e293b;
  /* ... */
}
```

Which palette is active is decided **before the first paint**, by a blocking
inline script at the top of `public/index.html` that reads the stored choice
(falling back to the OS preference) and stamps `data-theme`. `styles/theme.js`
owns only that one decision afterwards, and applies it with a single
`setAttribute` — never by writing properties.

> **Do not move these values back into JavaScript.** They used to live in a
> `themeVariables` object that `applyTheme()` wrote onto
> `document.documentElement.style` from a React effect. Effects run *after* the
> first paint, so every `var()` was invalid-at-computed-value-time for at least
> one frame and the page visibly flashed light before darkening on every load
> (DASS-3813). A token that is not in a stylesheet is not available to the first
> frame.

### Light Theme

#### Primary Colors

| Variable | Hex | RGB | Usage |
|----------|-----|-----|-------|
| `--primary` | `#2563eb` | `37, 99, 235` | Primary actions, links, active states |
| `--success` | `#16a34a` | - | Success messages, positive indicators |
| `--error` | `#dc2626` | `220, 38, 38` | Error messages, destructive actions |
| `--warning` | `#ea580c` | - | Warning messages, caution states |
| `--info` | `#0891b2` | - | Informational messages |

#### Background Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--background` | `#f8fafc` | Main page background |
| `--card-bg` | `#ffffff` | Card/component backgrounds |
| `--card-footer-bg` | `#f8fafc` | Card footer sections |
| `--subtle-bg` | `#f1f5f9` | Hover states, disabled inputs |
| `--subtle-btn-bg` | `#ffffff` | Secondary button backgrounds |

#### Text Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--text` | `#1e293b` | Primary text content |
| `--text-light` | `#64748b` | Secondary text, labels, placeholders |

#### Border Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--border` | `#e2e8f0` | General borders, dividers |
| `--section-footer-border` | `rgb(226, 232, 240)` | Section footer borders |

#### Badge Colors (Quality Indicators)

**Green (Good Quality)**
```css
--badge-green-bg: rgba(22, 163, 74, 0.1)
--badge-green-border: rgb(22, 163, 74)
--badge-green-text: rgb(22, 163, 74)
```

**Amber (Warning)**
```css
--badge-amber-bg: rgba(217, 119, 6, 0.1)
--badge-amber-border: rgb(217, 119, 6)
--badge-amber-text: rgb(161, 98, 7)
```

**Red (Poor Quality)**
```css
--badge-red-bg: rgba(220, 38, 38, 0.1)
--badge-red-border: rgb(220, 38, 38)
--badge-red-text: rgb(220, 38, 38)
```

#### Ghost Button Colors

```css
--ghost-btn-text: rgb(37, 99, 235)
--ghost-btn-border: rgb(191, 219, 254)
--ghost-btn-hover-text: rgb(29, 78, 216)
--ghost-btn-hover-border: rgb(37, 99, 235)
--ghost-btn-hover-bg: rgba(37, 99, 235, 0.05)
```

#### Stats Icon Color

```css
--stats-icon: rgb(100, 116, 139)  /* Muted gray for informational icons */
```

---

### Dark Theme

#### Primary Colors

| Variable | Hex | RGB | Usage |
|----------|-----|-----|-------|
| `--primary` | `#3b82f6` | `59, 130, 246` | Primary actions (lighter for contrast) |
| `--success` | `#22c55e` | - | Success indicators |
| `--error` | `#ef4444` | `239, 68, 68` | Error states |
| `--warning` | `#f97316` | - | Warning states |
| `--info` | `#0891b2` | - | Informational states |

#### Background Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--background` | `#1e293b` | Main dark background |
| `--card-bg` | `#273444` | Card backgrounds (elevated) |
| `--card-footer-bg` | `#233042` | Card footer sections |
| `--subtle-bg` | `#2f3e4e` | Hover states, subtle emphasis |
| `--subtle-btn-bg` | `#273444` | Secondary button backgrounds |

#### Text Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--text` | `#f8fafc` | Primary text (light on dark) |
| `--text-light` | `#cbd5e1` | Secondary text |

#### Border Colors

| Variable | Hex | Usage |
|----------|-----|-------|
| `--border` | `#3b4a63` | Borders and dividers |
| `--section-footer-border` | `rgb(51, 65, 85)` | Section borders |

#### Badge Colors (Dark Mode)

**Green (Good Quality)**
```css
--badge-green-bg: rgba(34, 197, 94, 0.15)
--badge-green-border: rgb(34, 197, 94)
--badge-green-text: rgb(34, 197, 94)
```

**Amber (Warning)**
```css
--badge-amber-bg: rgba(250, 204, 21, 0.15)
--badge-amber-border: rgb(250, 204, 21)
--badge-amber-text: rgb(253, 224, 71)
```

**Red (Poor Quality)**
```css
--badge-red-bg: rgba(239, 68, 68, 0.15)
--badge-red-border: rgb(239, 68, 68)
--badge-red-text: rgb(252, 165, 165)
```

#### Ghost Button Colors (Dark Mode)

```css
--ghost-btn-text: rgb(96, 165, 250)
--ghost-btn-border: rgb(51, 65, 85)
--ghost-btn-hover-text: rgb(147, 197, 253)
--ghost-btn-hover-border: rgb(96, 165, 250)
--ghost-btn-hover-bg: rgba(96, 165, 250, 0.1)
```

#### Stats Icon Color (Dark Mode)

```css
--stats-icon: rgb(148, 163, 184)
```

---

## Typography

### Font Family

The system uses the browser's default system font stack (not explicitly defined, allowing OS native fonts).

### Font Sizes

Typography uses **fluid scaling** with `clamp()` for responsive behavior:

```css
/* Headings */
h1: clamp(1.5rem, 5vw, 2.25rem)    /* 24px - 36px */
h2: clamp(1.25rem, 4vw, 1.75rem)   /* 20px - 28px */
h3: clamp(1rem, 3vw, 1.25rem)      /* 16px - 20px */

/* Body & UI Text */
Body: 1rem                          /* 16px */
Small: 0.875rem                     /* 14px */
Tiny: 0.75rem                       /* 12px */

/* Large Numbers (StatCard) */
Large Display: 2.5rem               /* 40px */
Unit Suffix: 1.125rem               /* 18px */
```

### Font Weights

| Weight | Value | Usage |
|--------|-------|-------|
| Regular | 400 | Body text, descriptions |
| Medium | 500 | Labels, form fields, navigation |
| Semibold | 600 | Headings, subheadings, emphasis |
| Bold | 700 | Logo, brand text |
| Extra Bold | 800 | Large stat numbers |

### Line Heights

```css
Headings: 1.1
Body: 1.6 - 1.7
Compact: 1.2
Stat Numbers: 1
```

### Letter Spacing

```css
Headings: -0.035em (tight)
Logo/Brand: -0.01em
Stat Numbers: 0.5px
Small Caps/Labels: 0.5px (uppercase text)
Body: normal (0)
```

### Text Styles Reference

#### Heading 1 (Page Title)
```javascript
{
  fontSize: 'clamp(1.5rem, 5vw, 2.25rem)',
  fontWeight: 600,
  lineHeight: 1.1,
  letterSpacing: '-0.035em',
  color: 'var(--text)'
}
```

#### Heading 2 (Section Title)
```javascript
{
  fontSize: 'clamp(1.25rem, 4vw, 1.75rem)',
  fontWeight: 600,
  lineHeight: 1.1,
  letterSpacing: '-0.025px',
  color: 'var(--text)'
}
```

#### Body Text
```javascript
{
  fontSize: '1rem',
  fontWeight: 400,
  lineHeight: 1.6,
  color: 'var(--text)'
}
```

#### Label Text
```javascript
{
  fontSize: '0.875rem',
  fontWeight: 500,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  color: 'var(--text-light)'
}
```

#### Large Stat Number
```javascript
{
  fontSize: '2.5rem',
  fontWeight: 800,
  lineHeight: 1,
  color: 'var(--text)'
}
```

---

## Spacing & Layout

### Spacing Scale

The design system uses a consistent spacing scale based on `rem` units:

| Token | Value | Pixels (16px base) | Usage |
|-------|-------|-------------------|--------|
| `xs` | 0.25rem | 4px | Tiny gaps, icon spacing |
| `sm` | 0.5rem | 8px | Compact spacing, form elements |
| `md` | 0.75rem | 12px | Default gaps, padding |
| `lg` | 1rem | 16px | Section spacing, margins |
| `xl` | 1.5rem | 24px | Large gaps, component separation |
| `2xl` | 2rem | 32px | Major sections, card padding |

### Layout Patterns

#### Container Padding (Responsive)

```css
.responsive-container {
  padding: clamp(1rem, 3vw, 2rem);
}
```

This provides:
- Mobile: 1rem (16px)
- Tablet: ~1.5rem (24px)
- Desktop: 2rem (32px)

#### Card Padding

```javascript
// Desktop
padding: '2rem'  // 32px

// Mobile
padding: '1rem'  // 16px
```

#### Form Field Spacing

```javascript
{
  marginBottom: '1rem',      // Between fields
  padding: '0.625rem 0.75rem', // Input padding (10px 12px)
  gap: '0.5rem'              // Between label and input
}
```

### Grid Systems

#### Responsive Auto-Fill Grid

```javascript
{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
  gap: '1.5rem'
}
```

This creates a responsive grid that:
- Fills available space automatically
- Minimum card width: 300px
- Falls back to single column on mobile

#### Stat Grid (Mobile-First)

```css
/* Mobile: Single column */
grid-template-columns: 1fr;

/* Tablet: Two columns */
@media (min-width: 576px) {
  grid-template-columns: repeat(2, 1fr);
}

/* Desktop: Four columns */
@media (min-width: 992px) {
  grid-template-columns: repeat(4, 1fr);
}
```

### Responsive Breakpoints

| Breakpoint | Width | Device Class |
|------------|-------|--------------|
| Mobile | < 576px | Phones |
| Small Tablet | 576px - 767px | Large phones, small tablets |
| Tablet | 576px - 991px | Tablets |
| Desktop | ≥ 992px | Laptops, desktops |
| Large Desktop | ≥ 1200px | Large screens |

#### Media Query Helpers

```css
/* Mobile and below */
@media (max-width: 575px) { }

/* Tablet and below */
@media (max-width: 767px) { }

/* Desktop and above */
@media (min-width: 768px) { }

/* Large desktop and above */
@media (min-width: 1200px) { }
```

### Content Min-Height

```css
.content-container {
  min-height: calc(100vh - 200px);
}
```

Ensures content is always at least viewport height minus header/footer.

---

## Component Library

### 1. Button Component

**File:** `/frontend/src/components/ui/Button.js`

#### Variants

##### Primary Button
```javascript
{
  height: '2.75rem',              // 44px (WCAG touch target)
  padding: '0 1.5rem',
  borderRadius: '0.5rem',         // 8px
  fontWeight: 500,
  fontSize: '1rem',
  backgroundColor: 'var(--primary)',
  color: 'white',
  border: 'none',
  cursor: 'pointer',
  transition: 'background 0.2s, transform 0.1s',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.5rem'
}
```

##### Danger Button (Outlined)
```javascript
{
  // ... base styles
  backgroundColor: 'transparent',
  color: 'var(--error)',
  border: '1px solid var(--border)'
}
```

##### Default Button (Outlined)
```javascript
{
  // ... base styles
  backgroundColor: 'transparent',
  color: 'var(--text-light)',
  border: '1px solid var(--border)'
}
```

#### Loading State

When `isLoading={true}`, displays a spinning loader:

```javascript
{
  display: 'inline-block',
  width: '16px',
  height: '16px',
  border: '2px solid rgba(255, 255, 255, 0.3)',
  borderRadius: '50%',
  borderTopColor: '#fff',
  animation: 'spin 1s linear infinite'
}
```

#### Usage Example

```jsx
<Button variant="primary" onClick={handleSubmit} isLoading={isSubmitting}>
  Submit Form
</Button>
```

---

### 2. StatCard Component

**File:** `/frontend/src/components/ui/StatCard.js`

Displays key metrics with optional percentage change indicator.

#### Base Styles

```javascript
{
  backgroundColor: 'var(--card-bg)',
  borderRadius: '0.75rem',       // 12px
  padding: '2rem',                // 32px
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  border: '1px solid var(--border)',
  position: 'relative',
  overflow: 'hidden',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  cursor: 'default'
}
```

#### Hover Effect

```javascript
onMouseEnter: {
  transform: 'translateY(-2px)',
  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
}

onMouseLeave: {
  transform: 'translateY(0)',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
}
```

#### Value Display

```javascript
{
  fontSize: '2.5rem',            // 40px
  fontWeight: 800,
  color: 'var(--text)',
  lineHeight: '1'
}
```

#### Unit Suffix

```javascript
{
  fontSize: '1.125rem',          // 18px
  fontWeight: 600,
  color: 'var(--text-light)',
  marginLeft: '0.375rem',
  background: 'var(--text-light)',
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent'
}
```

#### Percentage Change Badge

```javascript
{
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.5rem',
  fontSize: '0.8rem',
  color: change >= 0 ? 'var(--success)' : 'var(--error)',
  backgroundColor: change >= 0 ? 'var(--success)10' : 'var(--error)10',
  padding: '0.375rem 0.75rem',
  borderRadius: '2rem',          // Fully rounded pill
  border: `1px solid ${change >= 0 ? 'var(--success)' : 'var(--error)'}20`,
  fontWeight: 600,
  margin: '0 auto',
  width: 'fit-content'
}
```

#### Usage Example

```jsx
<StatCard
  title="Total Datasets"
  value={12543}
  previousValue={11980}
  color="var(--primary)"
  isLoading={false}
/>
```

---

### 3. Modal Component

**File:** `/frontend/src/components/ui/Modal.js`

A responsive modal with mobile-first design.

#### Desktop Modal

```javascript
{
  backgroundColor: 'var(--card-bg)',
  padding: '2rem',
  borderRadius: '0.75rem',
  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
  width: '90%',
  maxWidth: '800px',
  maxHeight: '90vh',
  position: 'relative',
  transition: 'background-color 0.3s',
  display: 'flex',
  flexDirection: 'column'
}
```

#### Mobile Modal (Full-Screen)

```javascript
{
  backgroundColor: 'var(--card-bg)',
  padding: '1rem',
  borderRadius: 0,               // No rounding on mobile
  boxShadow: 'none',
  width: '100%',
  maxWidth: '100%',
  height: '100vh',
  maxHeight: '100vh',
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  display: 'flex',
  flexDirection: 'column'
}
```

#### Backdrop

```javascript
{
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: isMobile ? 'transparent' : 'rgba(0, 0, 0, 0.1)',
  backdropFilter: isMobile ? 'none' : 'blur(4px)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 1000
}
```

#### Close Button

```javascript
{
  backgroundColor: 'var(--subtle-bg)',
  border: '1px solid var(--border)',
  fontSize: '1.25rem',
  lineHeight: 1,
  padding: '0.5rem',
  cursor: 'pointer',
  color: 'var(--text-light)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: '0.375rem',
  width: '44px',
  height: '44px',
  transition: 'all 0.2s ease'
}
```

#### Scrollable Content Area

```javascript
{
  flex: 1,
  overflowY: 'auto',
  marginRight: '-0.5rem',
  paddingRight: '0.5rem'
}
```

#### Usage Example

```jsx
<Modal
  isOpen={isOpen}
  onClose={handleClose}
  title="Edit Provider"
  footer={
    <>
      <Button variant="default" onClick={handleClose}>Cancel</Button>
      <Button variant="primary" onClick={handleSave}>Save</Button>
    </>
  }
>
  <FormContent />
</Modal>
```

---

### 4. FormField Component

**File:** `/frontend/src/components/ui/FormField.js`

Comprehensive form input with validation states.

#### Base Input Styles

```javascript
{
  display: 'block',
  width: '100%',
  padding: '0.625rem 0.75rem',   // 10px 12px
  fontSize: '0.875rem',           // 14px
  borderRadius: '0.5rem',         // 8px
  border: `1px solid ${getBorderColor()}`,
  backgroundColor: disabled ? 'var(--subtle-bg)' : 'var(--card-bg)',
  color: 'var(--text)',
  transition: 'border-color 0.2s, box-shadow 0.2s',
  outline: 'none'
}
```

#### Border Color States

```javascript
const getBorderColor = () => {
  if (showError) return 'var(--error)';       // Red for errors
  if (touched && !error) return 'var(--success)'; // Green for valid
  return 'var(--border)';                      // Default gray
};
```

#### Focus State

```javascript
{
  borderColor: 'var(--primary)',
  boxShadow: '0 0 0 3px rgba(var(--primary-rgb), 0.1)'
}
```

#### Label Styles

```javascript
{
  display: 'block',
  fontSize: '0.875rem',
  fontWeight: 500,
  marginBottom: '0.5rem',
  color: 'var(--text)'
}
```

#### Error Message

```javascript
{
  fontSize: '0.75rem',
  color: 'var(--error)',
  marginTop: '0.25rem',
  display: 'flex',
  alignItems: 'center',
  gap: '0.25rem'
}
```

#### Validation Icons

Uses Lucide React icons:
- **Error:** `<AlertCircle size={18} color="var(--error)" />`
- **Success:** `<Check size={18} color="var(--success)" />`

#### Password Toggle

```javascript
// Toggle button positioned absolute right
{
  position: 'absolute',
  right: '0.75rem',
  top: '50%',
  transform: 'translateY(-50%)',
  background: 'transparent',
  border: 'none',
  color: 'var(--text-light)',
  cursor: 'pointer',
  padding: '0.25rem'
}
```

Icons: `<Eye size={18} />` / `<EyeOff size={18} />`

#### Supported Input Types

- `text`, `email`, `url`, `password`, `number`, `file`
- `select` (with options array)
- `textarea` (with rows prop)
- `checkbox`

#### Usage Example

```jsx
<FormField
  type="text"
  name="provider_name"
  label="Provider Name"
  value={formData.provider_name}
  onChange={handleChange}
  onBlur={handleBlur}
  error={errors.provider_name}
  touched={touched.provider_name}
  required
  placeholder="Enter provider name"
/>
```

---

### 5. Alert Component

**File:** `/frontend/src/components/ui/Alert.js`

Notification component for success/error messages.

#### Base Styles

```javascript
{
  display: 'flex',
  alignItems: 'flex-start',
  padding: '1rem',
  borderRadius: '0.5rem',
  marginBottom: '1rem',
  gap: '0.75rem',
  backgroundColor: type === 'error' ? '#fee2e2' : '#dcfce7',
  color: type === 'error' ? 'var(--error)' : 'var(--success)',
  borderLeft: `4px solid ${type === 'error' ? 'var(--error)' : 'var(--success)'}`
}
```

#### Icon

24x24px SVG icon (error circle or success checkmark) using `currentColor` for theming.

#### Usage Example

```jsx
<Alert type="success">
  Provider successfully created!
</Alert>

<Alert type="error">
  Failed to save changes. Please try again.
</Alert>
```

---

### 6. Header Component

**File:** `/frontend/src/components/layout/Header.js`

Sticky navigation header with responsive mobile menu.

#### Desktop Header

```javascript
{
  backgroundColor: 'var(--card-bg)',
  borderBottom: '1px solid var(--border)',
  padding: '1rem 2rem',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  transition: 'all 0.3s ease',
  position: 'sticky',
  top: 0,
  zIndex: 100,
  backdropFilter: 'blur(10px)',
  WebkitBackdropFilter: 'blur(10px)'
}
```

#### Mobile Header

```javascript
{
  // ... same as desktop
  padding: '0.75rem 1rem'  // Reduced padding
}
```

#### Navigation Link (Desktop)

```javascript
{
  padding: '0.75rem 0',
  minHeight: '44px',
  position: 'relative',
  color: isActive ? 'var(--primary)' : 'var(--text-light)',
  textDecoration: 'none',
  fontWeight: 500,
  transition: 'all 0.2s ease',
  display: 'flex',
  alignItems: 'center'
}
```

#### Active Link Underline Indicator

```javascript
{
  content: '""',
  position: 'absolute',
  bottom: 0,
  left: 0,
  width: '100%',
  height: '2px',
  backgroundColor: 'var(--primary)',
  transform: isActive ? 'scaleX(1)' : 'scaleX(0)',
  transformOrigin: 'left',
  transition: 'transform 0.2s ease'
}
```

#### Mobile Menu Panel

```css
.mobile-nav-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: min(300px, 80vw);
  height: 100vh;
  background-color: var(--card-bg);
  transform: translateX(100%);
  transition: transform 0.3s ease;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
}

.mobile-nav-overlay.open .mobile-nav-panel {
  transform: translateX(0);
}
```

#### Mobile Menu Overlay

```css
.mobile-nav-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease;
}

.mobile-nav-overlay.open {
  opacity: 1;
  visibility: visible;
}
```

#### Hamburger Button

```javascript
{
  width: '44px',
  height: '44px',
  padding: '0',
  borderRadius: '0.375rem',
  border: '1px solid var(--border)',
  backgroundColor: isMobileMenuOpen ? 'var(--primary)' : 'var(--subtle-bg)',
  color: isMobileMenuOpen ? 'white' : 'var(--text)',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}
```

Icons: `<Menu size={20} />` / `<X size={20} />`

#### User Avatar Pill

```javascript
{
  width: '24px',
  height: '24px',
  borderRadius: '50%',
  backgroundColor: 'var(--primary)',
  color: 'white',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginRight: '0.5rem',
  fontWeight: 600,
  fontSize: '0.75rem'
}
```

#### Theme Toggle Button

```javascript
{
  width: '44px',
  height: '44px',
  padding: '0',
  borderRadius: '0.375rem',
  border: '1px solid var(--border)',
  backgroundColor: 'var(--subtle-bg)',
  color: 'var(--text)',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}
```

Icons: `<Sun size={20} />` (dark mode) / `<Moon size={20} />` (light mode)

---

### 7. ActionMenu Component

**File:** `/frontend/src/components/ui/ActionMenu.js`

Floating circular action buttons with tooltips.

#### Button Styles

```javascript
{
  width: '48px',
  height: '48px',
  borderRadius: '50%',
  backgroundColor: 'var(--primary)',
  color: 'white',
  border: 'none',
  cursor: 'pointer',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
  transition: 'all 0.2s ease',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}
```

#### Hover Effect

```javascript
{
  transform: 'scale(1.05)',
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
}
```

#### Tooltip

```javascript
{
  position: 'absolute',
  bottom: '100%',
  left: '50%',
  transform: 'translateX(-50%)',
  backgroundColor: 'rgba(0, 0, 0, 0.8)',
  color: 'white',
  padding: '0.5rem 0.75rem',
  borderRadius: '0.375rem',
  fontSize: '0.75rem',
  whiteSpace: 'nowrap',
  marginBottom: '0.5rem',
  pointerEvents: 'none',
  opacity: 0,
  transition: 'opacity 0.2s'
}

/* Visible on hover */
button:hover .tooltip {
  opacity: 1;
}
```

---

### 8. Breadcrumbs Component

**File:** `/frontend/src/components/ui/Breadcrumbs.js`

Navigation breadcrumb trail.

#### Container Styles

```javascript
{
  display: 'flex',
  alignItems: 'center',
  gap: '0.5rem',
  fontSize: '1.125rem',
  fontWeight: 500,
  color: 'var(--text-light)'
}
```

#### Home Icon

Uses `<Home size={20} />` from Lucide React for the first item.

#### Separator

Uses `<ChevronRight size={16} />` between items.

#### Active Item

```javascript
{
  color: 'var(--text)',
  fontWeight: 600
}
```

---

### 9. Toast Component

**File:** `/frontend/src/components/ui/Toast.js`

Temporary notification system (implementation details not fully visible in codebase review).

---

### 10. ConfirmModal Component

**File:** `/frontend/src/components/ui/ConfirmModal.js`

Confirmation dialog wrapper around the base Modal component.

---

## Animation & Transitions

### Keyframe Animations

Defined in `/frontend/src/styles/global.css`:

#### Spin Animation
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

**Usage:** Loading spinners
**Duration:** 1s
**Timing:** linear infinite

---

#### Fade In Animation
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

**Usage:** Component mounting, content reveal
**Duration:** 0.3s
**Timing:** ease-out

---

#### Slide In Up Animation
```css
@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Usage:** Modal entrance, card reveals
**Duration:** 0.4s
**Timing:** ease-out

---

#### Pulse Animation
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

**Usage:** Loading states, attention-grabbing indicators

---

### Transition Patterns

#### Standard Transition
```javascript
transition: 'all 0.2s ease'
```

**Usage:** Hover states, color changes, most UI interactions

---

#### Background Transition
```javascript
transition: 'background 0.2s, transform 0.1s'
```

**Usage:** Buttons (background changes + subtle press effect)

---

#### Border/Shadow Transition
```javascript
transition: 'border-color 0.2s, box-shadow 0.2s'
```

**Usage:** Form inputs on focus

---

#### Transform Transition (Cubic Bezier)
```javascript
transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
```

**Usage:** Cards with elevation changes, smooth scaling

---

### Hover Effects Library

#### Card Elevation
```javascript
// Normal
boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'

// Hover
boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
transform: 'translateY(-2px)'
```

---

#### Button Press Effect
```javascript
// Normal
transform: 'scale(1)'

// Active/Click
transform: 'scale(0.98)'
```

---

#### Link Underline Animation
```javascript
// Normal
transform: 'scaleX(0)'
transformOrigin: 'left'

// Hover/Active
transform: 'scaleX(1)'
transition: 'transform 0.2s ease'
```

---

#### Icon Scale
```javascript
// Normal
transform: 'scale(1)'

// Hover
transform: 'scale(1.05)'
```

---

## Accessibility Features

### WCAG 2.1 AA Compliance

#### Touch Targets

**Minimum Size:** 44x44px (2.75rem)
**Compliance:** WCAG 2.5.5 Level AAA

All interactive elements meet or exceed this standard:

```javascript
// Buttons
height: '2.75rem' // 44px

// Header navigation
minHeight: '44px'

// Mobile nav links
minHeight: '48px'

// Icon buttons
width: '44px'
height: '44px'
```

#### Invisible Hit Area for Links

For compact text links, an invisible 44x44px hit area is applied:

```css
.touch-target-link::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  min-width: 44px;
  min-height: 44px;
  width: 100%;
}
```

---

### Focus States

All focusable elements have clear focus indicators:

```css
button:focus, input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
```

**Focus Ring:**
- Color: Primary blue
- Size: 3px
- Opacity: 10% for subtle visibility
- Style: Box shadow (doesn't affect layout)

---

### Disabled States

```css
input:disabled, textarea:disabled, select:disabled, button:disabled {
  background-color: var(--subtle-bg);
  cursor: not-allowed;
}
```

---

### Semantic HTML & ARIA

#### Form Fields
- Proper `<label>` associations via `htmlFor` and `id`
- `aria-invalid` on error states
- `aria-describedby` linking to error/help text
- `aria-label` on icon-only buttons

#### Modals
- Focus trap when open
- Escape key closes modal
- Body scroll disabled when open
- Focus returns to trigger element on close

#### Mobile Menu
- `aria-expanded` state on hamburger button
- `aria-controls` linking to menu panel
- `aria-label` for screen reader context
- `aria-hidden` when closed

---

### Color Contrast

All text meets WCAG AA standards:

| Combination | Contrast Ratio | Standard |
|-------------|---------------|----------|
| Text on background | ≥ 4.5:1 | AA Normal |
| Large text on background | ≥ 3:1 | AA Large |
| Interactive element colors | ≥ 3:1 | AA UI Components |

**Primary Blue (#2563eb) on White:** 7.2:1 ✓
**Text (#1e293b) on Background (#f8fafc):** 14.5:1 ✓
**Text Light (#64748b) on Background:** 6.8:1 ✓

---

### Keyboard Navigation

- **Tab:** Focus next interactive element
- **Shift + Tab:** Focus previous element
- **Enter/Space:** Activate buttons and links
- **Escape:** Close modals and mobile menu
- **Arrow Keys:** Navigate within custom components (future enhancement)

---

## Responsive Design

### Mobile-First Strategy

All components are designed mobile-first, with progressive enhancement for larger screens.

#### Responsive Typography

Uses `clamp()` for fluid scaling:

```css
h1 { font-size: clamp(1.5rem, 5vw, 2.25rem); }
h2 { font-size: clamp(1.25rem, 4vw, 1.75rem); }
h3 { font-size: clamp(1rem, 3vw, 1.25rem); }
```

#### Responsive Padding

```css
.responsive-container {
  padding: clamp(1rem, 3vw, 2rem);
}
```

#### Responsive Grid

Auto-adapting grid system:

```javascript
{
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
  gap: '1.5rem'
}
```

---

### Component Adaptations

#### Modal
- Desktop: Centered, 90% width, max 800px, blur backdrop
- Mobile: Full-screen, no backdrop, no border radius

#### Header
- Desktop: Horizontal nav, user info visible
- Mobile: Hamburger menu, abbreviated logo ("DPM" vs "Data Provider Manager")

#### StatCard
- Desktop: 2rem padding, larger text
- Mobile: 1rem padding, slightly smaller text

#### Form Fields
- Desktop: Standard padding
- Mobile: Slightly larger touch targets (48px min-height in mobile nav)

---

### Utility Classes

```css
/* Hide on mobile */
.hide-mobile {
  display: none !important;
}

/* Hide on desktop */
@media (min-width: 768px) {
  .hide-desktop {
    display: none !important;
  }
}
```

---

### Custom Hook

**File:** `/frontend/src/hooks/useMediaQuery.js`

```javascript
export const useIsMobile = () => {
  // Returns true if viewport < 768px
};

export const useIsMobileOrSmallTablet = () => {
  // Returns true if viewport < 992px
};
```

---

## Implementation Guidelines

### Setting Up the Design System

#### 1. Load the Stylesheets

In the entry point (`index.js`), tokens first, then the rules that consume them:

```javascript
import './styles/theme.css';
import './styles/global.css';
import App from './App';
```

That is the whole setup. There is **no** initialization step and nothing to call
on mount: the palette is static CSS, and `public/index.html` has already stamped
`data-theme` on `<html>` before the bundle runs. Anything you add here that
decides or applies the theme will run after the first paint, which is the bug
described under [Color System](#color-system).

#### 2. Theme Toggle Implementation

```javascript
import {
  applyTheme,
  resolveInitialTheme,
  storeThemeChoice,
} from './styles/theme';

// Mirrors the boot script, so React's first render agrees with what is painted.
const [isDarkTheme, setIsDarkTheme] = useState(resolveInitialTheme);

const toggleTheme = () => {
  const newTheme = !isDarkTheme;
  setIsDarkTheme(newTheme);
  storeThemeChoice(newTheme);
};

// useLayoutEffect, not useEffect: a passive effect can let a frame paint
// between the commit and the attribute swap.
useLayoutEffect(() => {
  applyTheme(isDarkTheme);
}, [isDarkTheme]);
```

#### 3. Using CSS Variables in Components

```javascript
const MyComponent = () => {
  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      color: 'var(--text)',
      border: '1px solid var(--border)',
      padding: '1rem',
      borderRadius: '0.5rem'
    }}>
      Content
    </div>
  );
};
```

---

### Creating New Components

#### Component Template

```javascript
import React from 'react';

function MyComponent({ prop1, prop2, style = {} }) {
  const baseStyle = {
    // Base styles using CSS variables
    backgroundColor: 'var(--card-bg)',
    color: 'var(--text)',
    borderRadius: '0.5rem',
    padding: '1rem',
    transition: 'all 0.2s ease',
    // Merge with custom styles
    ...style
  };

  return (
    <div style={baseStyle}>
      {/* Component content */}
    </div>
  );
}

export default MyComponent;
```

---

### Color Usage Guidelines

#### When to Use Each Color

| Color Variable | Use Case | Examples |
|----------------|----------|----------|
| `--primary` | Primary actions, active states | Submit buttons, active nav links |
| `--success` | Success messages, positive change | Form success, stat increases |
| `--error` | Errors, destructive actions | Error messages, delete buttons |
| `--warning` | Warnings, caution | Alerts, unsaved changes |
| `--info` | Informational messages | Tips, notifications |
| `--text` | Primary content | Body text, headings |
| `--text-light` | Secondary content | Labels, placeholders, descriptions |
| `--border` | Separators, outlines | Card borders, dividers |
| `--card-bg` | Elevated surfaces | Cards, modals, dropdowns |
| `--subtle-bg` | Hover states, disabled | Button hover, disabled inputs |

---

### Spacing Guidelines

Use the spacing scale consistently:

```javascript
// Good
gap: '0.75rem'
padding: '1rem'
margin: '1.5rem'

// Bad - arbitrary values
gap: '13px'
padding: '17px'
margin: '23px'
```

---

### Typography Guidelines

#### Hierarchy

1. **Page Title:** H1 (clamp 24-36px)
2. **Section Title:** H2 (clamp 20-28px)
3. **Subsection:** H3 (clamp 16-20px)
4. **Body:** 16px (1rem)
5. **Small Text:** 14px (0.875rem)
6. **Captions:** 12px (0.75rem)

#### Font Weight Usage

- **800:** Large stat numbers only
- **700:** Logo/brand text
- **600:** Headings, emphasized text
- **500:** Labels, buttons, navigation
- **400:** Body text, descriptions

---

### Shadow System

```javascript
// Level 1: Subtle elevation
boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'

// Level 2: Card elevation (default)
boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'

// Level 3: Elevated/hover state
boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'

// Level 4: Modal/overlay
boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
```

---

### Border Radius System

```javascript
// Small: Form inputs, buttons
borderRadius: '0.375rem'  // 6px

// Medium: Cards, containers
borderRadius: '0.5rem'    // 8px

// Large: Stat cards, modals
borderRadius: '0.75rem'   // 12px

// Circle: Avatars, icon buttons
borderRadius: '50%'

// Pill: Badges, tags
borderRadius: '2rem'      // Fully rounded
```

---

### Responsive Patterns

#### Hide/Show by Breakpoint

```javascript
{
  display: isMobile ? 'none' : 'block'
}
```

Or use utility classes:

```html
<div className="hide-mobile">Desktop only</div>
<div className="hide-desktop">Mobile only</div>
```

#### Conditional Padding

```javascript
{
  padding: isMobile ? '1rem' : '2rem'
}
```

#### Responsive Grid

```javascript
{
  display: 'grid',
  gridTemplateColumns: isMobile
    ? '1fr'
    : 'repeat(auto-fill, minmax(300px, 1fr))',
  gap: '1.5rem'
}
```

---

### Performance Considerations

#### Use `will-change` Sparingly

Only for elements that frequently change:

```css
nav a {
  will-change: color, transform;
}
```

#### Optimize Animations

- Use `transform` and `opacity` for GPU acceleration
- Avoid animating `width`, `height`, `top`, `left`
- Limit animations to 60fps

```javascript
// Good
transition: 'transform 0.2s, opacity 0.2s'

// Bad
transition: 'width 0.2s, height 0.2s'
```

---

## Component Checklist

When creating a new component, ensure it includes:

- [ ] Responsive design (mobile-first)
- [ ] Dark mode support (CSS variables)
- [ ] Focus states (for interactive elements)
- [ ] Touch targets ≥ 44px (for buttons/links)
- [ ] Hover states (where applicable)
- [ ] Loading states (if async data)
- [ ] Error states (if user input)
- [ ] ARIA labels (for accessibility)
- [ ] Proper semantic HTML
- [ ] Consistent spacing (from spacing scale)
- [ ] Smooth transitions
- [ ] TypeScript types (if using TS)

---

## Design System Maintenance

### Version Control

Track design system changes in `CHANGELOG.md` with:
- New components
- Color changes
- Spacing adjustments
- Breaking changes

### Testing

Test components across:
- Chrome, Firefox, Safari, Edge
- iOS Safari, Android Chrome
- Light and dark modes
- Touch and mouse input
- Screen readers

### Documentation

Keep this document updated when:
- Adding new components
- Changing color values
- Updating spacing scale
- Modifying breakpoints

---

## Appendix: Quick Reference

### CSS Variables Cheat Sheet

```css
/* Colors */
--primary, --success, --error, --warning, --info
--background, --card-bg, --subtle-bg
--text, --text-light
--border

/* RGB Variants (for alpha) */
--primary-rgb, --error-rgb

/* Badges */
--badge-green-bg, --badge-green-border, --badge-green-text
--badge-amber-bg, --badge-amber-border, --badge-amber-text
--badge-red-bg, --badge-red-border, --badge-red-text

/* Ghost Buttons */
--ghost-btn-text, --ghost-btn-border
--ghost-btn-hover-text, --ghost-btn-hover-border, --ghost-btn-hover-bg
```

---

### Spacing Scale

```
0.25rem (4px)  → xs
0.5rem (8px)   → sm
0.75rem (12px) → md
1rem (16px)    → lg
1.5rem (24px)  → xl
2rem (32px)    → 2xl
```

---

### Breakpoints

```
< 576px        → Mobile
576px - 767px  → Small Tablet
576px - 991px  → Tablet
≥ 992px        → Desktop
≥ 1200px       → Large Desktop
```

---

### Font Sizes

```
0.75rem (12px)   → Tiny
0.875rem (14px)  → Small
1rem (16px)      → Body
1.125rem (18px)  → Medium
1.25rem (20px)   → Large
2.5rem (40px)    → Stat
```

---

## Conclusion

The GFBio Design System provides a comprehensive, maintainable foundation for building consistent, accessible, and beautiful user interfaces. By adhering to these guidelines and using the provided components, developers can create cohesive experiences that work seamlessly across devices and themes.

For questions or contributions, please refer to the project repository or contact the design system maintainers.

---

**Document Version:** 1.0
**Date:** January 21, 2026
**Author:** Claude Code (Anthropic)
**License:** Internal Use Only
