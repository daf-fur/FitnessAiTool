---
name: Fitness Agent
description: A conversational fitness companion for workout planning, exercise swaps, and progress review
colors:
  training-paper: "#f4efe9"
  canvas-strong: "#ece2d5"
  chalk-white: "#f9f5f1"
  chalk-strong: "#efe4d5"
  field-notes-black: "#1f1d1a"
  worn-suede: "#615b55"
  pressed-linen: "#d7c9b7"
  field-sage: "#546b52"
  deep-forest: "#3f553f"
  sage-whisper: "#e4ebdf"
  terracotta: "#8f5147"
  signal-green: "#738c67"
typography:
  display:
    fontFamily: '"Iowan Old Style", "Georgia", "Times New Roman", serif'
    fontSize: "clamp(3.2rem, 6vw, 6rem)"
    fontWeight: 500
    lineHeight: 0.92
    letterSpacing: "-0.07em"
  headline:
    fontFamily: '"Iowan Old Style", "Georgia", "Times New Roman", serif'
    fontSize: "clamp(2rem, 3vw, 2.7rem)"
    fontWeight: 500
    letterSpacing: "-0.05em"
  body:
    fontFamily: '"Helvetica Neue", "Segoe UI", sans-serif'
    fontSize: "1rem"
    lineHeight: 1.7
  label:
    fontFamily: '"Helvetica Neue", "Segoe UI", sans-serif'
    fontSize: "0.66rem"
    fontWeight: 600
    letterSpacing: "0.12em"
rounded:
  brand: "8px"
  bubble: "14px"
  panel: "18px"
  pill: "999px"
spacing:
  xs: "10px"
  sm: "15px"
  md: "18px"
  lg: "32px"
components:
  msg-user:
    backgroundColor: "{colors.sage-whisper}"
    rounded: "{rounded.bubble}"
    padding: "15px 18px"
  msg-assistant:
    backgroundColor: "rgba(255,255,255,0.4)"
    rounded: "{rounded.bubble}"
    padding: "15px 18px"
  button-send:
    backgroundColor: "{colors.field-sage}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "12px 18px"
  button-send-hover:
    backgroundColor: "{colors.deep-forest}"
  button-reset:
    backgroundColor: "transparent"
    textColor: "{colors.field-notes-black}"
    rounded: "{rounded.pill}"
    padding: "9px 14px"
  prompt-chip:
    backgroundColor: "rgba(255,255,255,0.18)"
    textColor: "{colors.field-notes-black}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
---

# Design System: Fitness Agent

## Overview

**Creative North Star: "The Field Notes"**

The Fitness Agent is built on the aesthetic of a well-kept training notebook: warm paper, reliable ink, sparing use of a muted green accent that feels more field than gym. The visual language draws from analog tools — the parchment warmth of the background, the tight-tracked uppercase labels of a form sheet, the serif typography that appears only for editorial moments — while staying fully functional as a modern web application.

The key tension the design resolves: a fitness tool should feel capable without feeling clinical. This system achieves that through material warmth (the earthy palette), editorial authority (the serif display type), and restraint in decoration (Field Sage appears on fewer than three elements per screen). The result is a surface that a user would feel comfortable spending focused time inside — not a dashboard to check, but a desk to sit at.

Density is medium. Panels are generous but bounded. The two-column workspace gives the brief sidebar and conversation panel distinct territories without crowding either. Every component breathes at `18px` internal padding.

**Key Characteristics:**
- Warm earthy palette rooted in organic neutrals, not corporate blue
- Serif used only at editorial scale — hero heading and brief panel title
- Field Sage accent is scarce: brand mark, hero span, send button only
- Structural shadows signal hierarchy; they are warm, not cool
- Pill radius for interactive controls; panel radius for containers; never mixed
- Uppercase tracked labels form a secondary typographic register across all metadata

## Colors

An earthy, analog palette built on warm neutrals with a single muted green accent. No blue, no pure white, no saturated color.

### Primary
- **Field Sage** (`#546b52`): The sole accent. Used on the send button background, brand mark border/tint, and the hero h1 accent span. Its restraint is structural — appearing on three elements maximum per screen is what gives it authority.
- **Deep Forest** (`#3f553f`): Field Sage's hover state and the brand mark's text color. Never used as a standalone fill on a new element.

### Secondary
- **Sage Whisper** (`#e4ebdf`): User message bubble background. The softest expression of the accent family — signals "your voice" without using Field Sage's full weight.
- **Signal Green** (`#738c67`): Connection status dot only. A lighter sage that reads as a live indicator without competing with the accent.

### Neutral
- **Training Paper** (`#f4efe9`): Page background. The warmest surface — the field notebook's paper.
- **Canvas Strong** (`#ece2d5`): Stronger background step, available for hover states on the background tier.
- **Chalk White** (`#f9f5f1`): Panel surface — slightly lighter than the page, creates the card lift without white.
- **Chalk Strong** (`#efe4d5`): Stronger panel variant.
- **Field Notes Black** (`#1f1d1a`): Primary text. Near-black with a warm undertone — never pure `#000`.
- **Worn Suede** (`#615b55`): Secondary text, all labels, meta information, helper copy. The palette's warm gray.
- **Pressed Linen** (`#d7c9b7`): All borders and dividers — horizontal rules, card outlines, input underlines, topbar edge.
- **Terracotta** (`#8f5147`): Error state only — message bubbles, status text. A muted fired-clay red that reads as warning without screaming.

### Named Rules
**The One Accent Rule.** Field Sage appears on the send button, the brand mark, and the hero h1 accent span — three placements. Adding a fourth is a system violation. Sage Whisper (the user bubble) and Signal Green (the status dot) are related tones in service roles, not accent expansions.

**The No-Cool-Neutral Rule.** Every gray in this system has a warm undertone (Field Notes Black, Worn Suede, Pressed Linen). Do not substitute a neutral gray (`#888`, `#ccc`, `#f5f5f5`) — the warmth is load-bearing.

## Typography

**Display Font:** Iowan Old Style (with Georgia, Times New Roman fallback)
**Body Font:** Helvetica Neue (with Segoe UI fallback)

**Character:** Editorial contrast. Serif appears only at scale — the hero heading and the brief panel title — where it reads as an authorial moment. All operational text (labels, messages, input, buttons) uses the clean sans. The pairing signals when content is being *read* versus *acted on*.

### Hierarchy
- **Display** (Iowan Old Style, weight 500, `clamp(3.2rem, 6vw, 6rem)`, line-height 0.92, letter-spacing -0.07em): Hero heading only. Tightly tracked and compressed, with the accent span in Deep Forest.
- **Headline** (Iowan Old Style, weight 500, `clamp(2rem, 3vw, 2.7rem)`, letter-spacing -0.05em): Brief panel `h2` only. Scaled down from Display but maintaining the serif authority.
- **Body** (Helvetica Neue, 1rem, line-height 1.7): Message content, input text, lead paragraph, helper copy. Max line length on the hero paragraph is `620px`.
- **Label** (Helvetica Neue, 0.64–0.78rem, letter-spacing 0.12–0.16em, uppercase): All metadata, section labels, brand name, brand tag, button text, panel header, profile field. The uppercase tracked register is the system's secondary voice.

### Named Rules
**The Field Notes Rule.** Serif is an editorial instrument, not a hierarchy decoration. It appears only on the two largest headings (Display and Headline) — the places where a user pauses to orient. Every other text element, including subheadings and section labels, uses the sans. Introducing serif at body or label scale breaks the register contrast.

**The Tracked Label Rule.** Every UI label, metadata string, or button text uses `letter-spacing: 0.12–0.16em` and `text-transform: uppercase`. This creates a consistent secondary voice across the entire interface. Copy that is instructional or conversational never uses tracking.

## Layout

Two-column workspace grid within a `min(1200px, calc(100% - 30px))` container, centered with `margin: 0 auto`. The brief sidebar is fixed-range (`minmax(220px, 280px)`) with the content column taking the remainder (`minmax(0, 1fr)`), separated by a `32px` gap.

The topbar spans the full container width and is separated from the workspace by a `1px` Pressed Linen border with a fading gradient overlay on the pseudo-element. Below the workspace, the composer (`#composer`) is a separate full-width flex row with a `1px` border-top divider, keeping input and messages visually separated.

**Responsive behavior:** At `820px`, the grid collapses to a single column; the brief panel reorders to `order: 2` (below the content). At `640px`, container edge padding tightens to `calc(100% - 20px)`, the brand tag hides, the profile field label hides, and the hero h1 reduces to `2.8rem`.

The message list (`#messages`) is a bounded scroll region: `min-height: 300px`, `max-height: 450px`, `overflow-y: auto`. New messages scroll via `requestAnimationFrame` (not `scrollIntoView`) to avoid layout jank.

## Elevation & Depth

**Structural and warm.** Shadows in this system signal hierarchy — panels lift off the page, the send button lifts off the composer row — rather than adding decoration. All shadows use the warm ink shadow token (`rgba(31, 29, 26, 0.07)`) or its green-tinted variant for the send button. No cool-gray or blue-tinted shadows.

### Shadow Vocabulary
- **Panel ambient** (`0 4px 18px var(--shadow)`): Brief sidebar panel. A wide, low-opacity lift that reads as material depth.
- **Panel prominent** (`0 8px 24px var(--shadow)`): Conversation panel. Slightly taller than the brief panel, establishing it as the primary surface.
- **Message micro** (`0 2px 8px rgba(31, 29, 26, 0.02)`): Message bubbles. Barely perceptible — just enough to lift the bubble off the messages surface.
- **Send button** (`0 8px 18px rgba(84, 107, 82, 0.12)`): Green-tinted shadow under the filled send button, connecting the button's color to its depth. Intensifies to `0 10px 20px rgba(84, 107, 82, 0.18)` on hover.
- **Signal dot ring** (`0 0 0 3px rgba(115, 140, 103, 0.12)`): Soft ring around the status dot — a glow, not a shadow.

### Named Rules
**The Warm Shadow Rule.** Every shadow in this system is tinted warm (`rgba(31, 29, 26, ...)`) or green (`rgba(84, 107, 82, ...)`). A cool-gray shadow (`rgba(0, 0, 0, ...)`) is a system violation — it reads as a different product.

## Shapes

Four radius values, each assigned to a component family. They do not mix.

- **Brand mark** (8px): The brand mark square in the topbar. Slightly softer than a hard square but not as generous as a card.
- **Message bubble** (14px): Both user and assistant message bubbles. Comfortably rounded without approaching pill territory.
- **Panel** (18px): Brief sidebar and conversation panel. The largest container radius — generous, card-like.
- **Pill** (999px): All interactive controls — send button, reset button, prompt chips. Pill radius is reserved for clickable elements, not containers.

**The Radius Assignment Rule.** Containers use `14px` (bubble) or `18px` (panel). Controls use `999px` (pill). Brand mark uses `8px`. Nothing else. Do not round a container to `999px` or make a button `18px`.

## Components

### Topbar
- **Character:** Orientation strip — brand on the left, profile and reset on the right. Low height, high information density. Everything tracked uppercase.
- **Layout:** Flex, space-between, `22px 0 18px` padding, `1px` Pressed Linen border-bottom with a fading gradient overlay.
- **Brand Mark:** 34×34px square, 8px radius, Field Sage border at 40% opacity, Field Sage tint background at 7%, Deep Forest text, weight 700, tracked uppercase.
- **Profile Input:** Borderless, underline-only (`1px` Pressed Linen border-bottom), transparent background, `130px` wide. The underline-only treatment keeps it visually lightweight in the topbar.
- **Reset Button:** Pill, ghost (transparent bg, Pressed Linen border). Hover: border shifts to Field Sage, background tints 4% olive.

### Brief Panel (Sidebar)
- **Character:** A coach's pre-session card. Serif title, tabular brief list, ambient shadow.
- **Shape:** 18px radius, Chalk White background at 16% white overlay, `0 4px 18px` shadow, Pressed Linen border.
- **h2:** Iowan Old Style, `clamp(2rem, 3vw, 2.7rem)`, weight 500, -0.05em tracking. The only Headline-scale typography in the system.
- **Brief List:** Full-width list, Pressed Linen top/bottom borders. Each row: label in Worn Suede tracked uppercase at 0.66rem, value in Field Notes Black at 0.98rem weight 600.

### Hero Section
- **Character:** Editorial welcome — display heading with an accent span, lead paragraph, quick-prompt chips.
- **h1:** Display scale serif with the second line's `<span>` in Deep Forest, tight line-height (0.92), -0.07em tracking.
- **Eyebrow:** Label register (0.7rem, weight 600, 0.14em tracking, uppercase, Worn Suede).
- **Lead:** Body text at 1.05rem, Worn Suede, `max-width: 620px`, line-height 1.65.

### Prompt Chips
- **Character:** Ghost pills that invite but don't demand. A whisper, not a call-to-action.
- **Style:** Pill (999px), `rgba(255,255,255,0.18)` background, Pressed Linen border, `10px 16px` padding.
- **Hover:** Lift 1px (`translateY(-1px)`), border shifts to Field Sage at 45% opacity, background tints 4% olive, micro shadow `0 4px 10px rgba(31,29,26,0.04)`.
- **Transition:** 0.18s ease-out on transform, border-color, background, box-shadow.

### Message Bubbles
- **Character:** Contained surfaces that distinguish speaker without decorating the conversation.
- **Shape:** 14px radius, `15px 18px` padding, `1px` Pressed Linen border, micro shadow.
- **User:** Sage Whisper (`#e4ebdf`) background, Field Sage border at 20% opacity, `align-self: flex-end`.
- **Assistant:** `rgba(255,255,255,0.4)` background, `align-self: flex-start`.
- **Pending:** Same as assistant, `opacity: 0.72`, `border-style: dashed`. Text cycles through thinking messages every 1200ms.
- **Error:** Terracotta border at 25% opacity, Terracotta background at 4%, Terracotta text color.
- **Max width:** `min(760px, 84%)` desktop; `90%` at 640px breakpoint.

### Composer Input + Send Button
- **Character:** The input disappears; the button declares intent.
- **Input (`#input`):** Borderless, underline-only (Pressed Linen), transparent background, `12px 0 10px` padding, full width. Placeholder at 50% Field Notes Black opacity.
- **Send Button:** Pill (999px), Field Sage background, white text, `0.72rem` uppercase tracked label, `min-width: 110px`, `0 8px 18px` green shadow. Hover: Deep Forest background, 1px lift, shadow intensifies.
- **Focus:** All interactive elements use `outline: 2px solid var(--accent)` at `3px` offset — a consistent Field Sage focus ring.

### Signal Dot
- **Character:** A live status indicator that reads immediately without text.
- **Style:** 9px circle, Signal Green fill, `0 0 0 3px rgba(115,140,103,0.12)` ring shadow. No animation at rest; the status label changes via `innerHTML` on state transitions.

## Do's and Don'ts

### Do:
- **Do** use Iowan Old Style only for the Display heading and the Headline brief title — those two placements, nothing else.
- **Do** reserve Field Sage for the three designated placements: send button, brand mark, hero h1 accent span.
- **Do** keep all borders and dividers in Pressed Linen (`#d7c9b7`) — the line color is a system-wide invariant.
- **Do** tint all shadows warm (`rgba(31, 29, 26, ...)`) or olive-green for the send button — never cool gray.
- **Do** use pill radius (999px) for interactive controls and panel radius (18px) for containers; assign by component type, not by feel.
- **Do** apply the uppercase tracked label register (0.12–0.16em letter-spacing, `text-transform: uppercase`) to all metadata, labels, eyebrows, and button text.

### Don't:
- **Don't** introduce a pure white (`#ffffff`) background or a neutral gray — the warmth of Training Paper and Chalk White is the system's material identity.
- **Don't** use a cool-tinted or pure-black shadow — it reads as a foreign component.
- **Don't** use the serif font below Headline scale. No serif body text, no serif labels, no serif button text.
- **Don't** add a fourth accent placement beyond the three specified. Sage Whisper (user bubble) and Signal Green (status dot) are related tones in dedicated roles, not license to expand the accent's footprint.
- **Don't** apply `border-radius: 18px` to interactive controls or `999px` to containers — the radius assignment by component family is load-bearing.
- **Don't** add decorative uppercase tracking to conversational or instructional text — the tracked label register belongs to metadata and UI chrome only.
