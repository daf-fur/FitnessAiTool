---
name: Fitness Agent
description: A conversational fitness assistant for workout planning and tracking
colors:
  morning-sky-blue: "#e8f0fe"
  chalk-surface: "#f1f1f1"
  faded-steel: "#888888"
typography:
  body:
    fontFamily: "sans-serif"
    fontSize: "1rem"
    lineHeight: 1.5
rounded:
  sm: "6px"
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "2rem"
components:
  msg-user:
    backgroundColor: "{colors.morning-sky-blue}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.75rem"
  msg-assistant:
    backgroundColor: "{colors.chalk-surface}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.75rem"
---

# Design System: Fitness Agent

## Overview

**Creative North Star: "The Training Journal"**

The Fitness Agent UI is a purposeful tool built around one idea: the conversation *is* the interface. There is no chrome to navigate, no sidebar to manage, no dashboard to interpret — just a clean exchange between the user and their fitness coach. The design serves this by removing itself: a centered, narrow column, quiet neutral bubbles, and a persistent input at the bottom.

Density is low by intention. Message bubbles breathe with comfortable padding, the form sits close to the content without crowding it, and nothing competes for attention beyond the words on screen. The aesthetic is closer to a well-kept training notebook than a gym app — reliable, efficient, and devoid of motivational noise.

The restrained visual register is not austerity for its own sake. It signals that the product trusts its content. The coach's voice, the user's questions, and the exercise data are the substance; the UI is the container.

**Key Characteristics:**
- Single-column, conversation-first layout
- Color used only to distinguish speaker roles, never decoratively
- Flat, zero-elevation system
- Refined and restrained interactive controls
- No visual hierarchy beyond the chat exchange itself

## Colors

Two role-coded surfaces and one muted state — the palette's restraint is the design.

### Primary
- **Morning Sky Blue** (`#e8f0fe`): User message bubble background. A desaturated periwinkle that signals "this is your voice" without competing with the content. Its Google-blue lineage reads as familiar and trustworthy, not branded.

### Neutral
- **Chalk Surface** (`#f1f1f1`): Assistant message bubble background. Matte near-white that recedes, letting the agent's text do all the work.
- **Faded Steel** (`#888888`): Pending/thinking state text. Applied as an italic color only — signals "in-progress, not content" without introducing a new visual register.

**The Two-Surface Rule.** The palette holds two speaker surfaces and one muted state. Introducing a third accent or decorating beyond role-coding breaks the system's distinguishing logic.

## Typography

**Body Font:** `sans-serif` (resolves to the platform's system-ui stack — SF Pro on macOS/iOS, Segoe UI on Windows, Roboto on Android)

**Character:** The UI defers to the platform's native typeface, reinforcing the tool-like, functional register of the Training Journal. There is no imposed typographic personality — familiarity is the point.

### Hierarchy
- **Body** (default weight, 1rem, 1.5 line-height): The entire UI runs at one text size. Message content, input text, and button labels share this single level. No decorative size scaling beyond the browser's native `h2` for the page heading.
- **Pending / Label** (default weight, 1rem, italic): The `.pending` state uses italic only — same size, Faded Steel color. Communicates wait state within the existing scale.

**The Single-Scale Rule.** One text size, one stack. The heading (`h2`) is the sole exception, using the browser default. Any new element should fit this level without introduction of a display size or secondary font.

## Layout

Single-column, centered, constrained. The content area is capped at `700px` and centered with `2rem auto` margin, giving comfortable breathing room on wider screens. Horizontal padding (`0 1rem`) prevents edge-to-edge rendering on mobile.

The message list grows downward; new messages scroll smoothly into view (`scrollIntoView({ behavior: "smooth" })`). The form sits directly below the message list with `1rem` top margin. The text input fills all available horizontal space (`flex: 1`), with the Send button at its natural width, separated by a `0.5rem` gap.

No grid, no breakpoints, no layout shifts. The `max-width` constraint simply stops applying below `700px`, and the `0 1rem` padding keeps the layout from feeling claustrophobic on small screens.

## Elevation & Depth

Completely flat. No box-shadows, no elevation layers, no translucency. Depth is conveyed entirely through background-color contrast: Morning Sky Blue and Chalk Surface read as distinct surfaces against the white page. No surface lifts on hover or focus.

**The Zero-Shadow Rule.** Shadows are not part of this system. If a future component requires perceived depth, reach for a slightly darker background tint — never a shadow.

## Shapes

Gently rounded message bubbles (6px radius) are the only shape in the vocabulary. The value is conservative — enough to soften the hard rectangle without drawing attention to its own curvature. Input fields and buttons use browser-default styling with no radius override.

**The One-Radius Rule.** `6px` is the only custom radius value. Do not introduce `0` (sharp) or larger values (12px+) without a specific functional reason. Shape consistency belongs to the restrained character.

## Components

### Message Bubbles
- **Character:** Role-coded surfaces that recede into the conversation. The bubble's only job is to distinguish speaker.
- **Shape:** Gently curved (6px radius)
- **User:** Morning Sky Blue (`#e8f0fe`) background, right-aligned text, `0.5rem 0.75rem` padding
- **Assistant:** Chalk Surface (`#f1f1f1`) background, default left-aligned text, same padding
- **Pending State:** Same as assistant bubble; text color shifts to Faded Steel (`#888`) with italic — no size change

### Input / Text Field
- **Style:** Browser-default stroke, no custom background, `0.5rem` padding, `flex: 1` to fill the form row
- **Focus:** Browser-default focus ring — no custom treatment needed
- **Character:** The lowest-profile element on the page; invisible until needed

### Buttons
- **Character:** Refined and restrained. Controls serve the chat without competing with it.
- **Style:** Browser-default styling — no custom background, no padding override, no radius
- **Send:** Natural width beside the input in the flex row
- **Reset:** Below the form; styled identically to Send; a secondary action, not a destructive one

## Do's and Don'ts

### Do:
- **Do** use only the two speaker-role surfaces — Morning Sky Blue for user messages, Chalk Surface for assistant messages — as the sole color differentiation.
- **Do** keep the content area at or below `700px` wide, centered with auto margins.
- **Do** use italic + Faded Steel (`#888`) only for the pending/loading state — keep the same size.
- **Do** let new messages scroll smoothly into view with `scrollIntoView({ behavior: "smooth" })`.
- **Do** rely on `flex: 1` for the input to naturally share space with the button at any container width.

### Don't:
- **Don't** introduce custom shadow values anywhere — this is a zero-elevation system.
- **Don't** add a second typeface, a display heading size, or any text-size ramp beyond the single body scale.
- **Don't** apply Morning Sky Blue or Chalk Surface outside their speaker-role context — they are semantic, not decorative.
- **Don't** override button padding, radius, or background-color beyond browser defaults; the restraint is deliberate.
- **Don't** introduce a third accent color. The Two-Surface Rule is load-bearing.
