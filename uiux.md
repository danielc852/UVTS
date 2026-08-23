# UVTS UI/UX Specification

**Product:** UVTS (User-View Testing Stimulation)  
**Release:** First release  
**Source:** `product_spec.md`  
**Audience:** Product designers, engineers, content designers, and quality reviewers  
**Last updated:** 2026-08-23

## 1. Purpose

This document defines the user experience and visual direction for the first release of UVTS. It translates the product requirements into an implementation-ready responsive web experience for non-technical people who write or review product manuals.

The interface should feel calm, direct, and professional. It should help a writer move from uploading one PDF to understanding the resulting information gaps without needing technical or AI knowledge.

The complete journey happens on one page:

1. Upload and check a manual.
2. Generate questions using the default or adjusted settings.
3. Review the complete question list.
4. Evaluate the reviewed questions against the manual.
5. Read the report and decide what to improve.

## 2. Experience Principles

### 2.1 Lead with the next useful action

Each workflow stage has one visually dominant action. Secondary actions remain available but should not compete with the next step in the journey.

### 2.2 Explain the system in plain words

Use familiar terms such as “check,” “question,” “manual,” and “information.” Avoid implementation language such as “retrieval,” “embedding,” “agent,” “model,” or “inference.”

### 2.3 Make system status visible

Long-running work must show what is happening, what has completed, and what the writer can do next. Never leave the user with an unexplained spinner.

### 2.4 Make evidence easy to inspect

Every result that finds information must expose real page references and a short evidence extract or note. The design must make it easy to compare the result with the original manual.

### 2.5 Never communicate through color alone

Every status includes a text label and, where useful, an icon. Color provides emphasis but never carries the full meaning.

### 2.6 Preserve trust

The report must clearly distinguish found, partly found, missing, unfinished, and failed information. It must not imply that UVTS checked factual accuracy or generated an answer to the user question.

## 3. Astryx Design System

Meta’s Astryx design system is the source of truth for components, accessibility behavior, interaction states, spacing, and semantic tokens. The monochrome UVTS theme is a product-specific visual treatment built on Astryx; it must not replace or weaken Astryx keyboard, focus, validation, or responsive behavior.

Developers must consult the current Astryx documentation before implementation. Do not rely on copied props or remembered APIs because the design system may evolve.

### 3.1 Component mapping

| UVTS need | Astryx pattern | Usage |
| --- | --- | --- |
| Application frame | `AppShell` | Use once at the root. Use its main landmark, skip link, and responsive behavior; do not create a second `<main>` or skip link. |
| Product theme | `Theme` | Apply a statically built light theme using semantic tokens. |
| Workflow regions | `Section` | Group the five ordered stages and the report subsections. Use spacing and dividers before adding containers. |
| Form organization | `FormLayout` | Stack fields vertically. Use horizontal arrangements only for directly related values such as the three question-type counts. |
| PDF upload | `FileInput` | Use a single-file drop zone with PDF acceptance, validation status, and a visible description of known limits. |
| Multiple choices | `CheckboxList` | Use for the three question types, six topics, and three user viewpoints. Provide group labels and helper descriptions. |
| Question totals and split | `NumberInput` | Set integer-only values with `min`, `max`, and step controls. Disable wheel-based changes in scrolling pages. |
| Actions | `Button` | Reserve `primary` for one next-step action per active stage. Use specific labels such as “Generate questions” and “Evaluate questions.” |
| Known progress | `ProgressBar` | Show completed questions out of total with an accessible label and visible value. Use an indeterminate state only when the amount of work is genuinely unknown. |
| Status and categories | `Badge` | Use sparingly for short status or category labels. Use plain supporting text for dates, counts, filenames, and descriptions. |
| Persistent feedback | `Banner` | Use for upload errors, incomplete reports, failed questions, privacy notices, and report limitations. Keep unresolved errors visible. |
| Expandable evidence | `Collapsible` | Reveal question reasoning and page evidence. Keep essential status and missing-information summaries visible before expansion. |
| Irreversible confirmation | `AlertDialog` | Confirm deleting or replacing connected data and replacing generated questions. Describe the consequence and focus the cancel action first. |

Use native semantic HTML within Astryx components: headings in order, `<form>` for configuration, lists for question collections, and links for navigation. Do not use a button when the action only navigates to another page.

## 4. Visual System

### 4.1 Color direction

UVTS is light-mode only for the first release. White and black are the dominant colors.

| Role | Design intent | Astryx token guidance |
| --- | --- | --- |
| Page background | White | `--color-background-body` |
| Primary surface | White | `--color-background-surface` |
| Primary text | Black or near-black | `--color-text-primary` |
| Secondary text | Neutral dark gray | `--color-text-secondary` |
| Borders and dividers | Neutral light gray | Astryx semantic border token |
| Muted regions | Very light neutral gray | Astryx muted or wash surface token |
| Primary action | Black background with white text | Astryx primary button tokens |
| Focus | High-contrast dark outline with visible offset | Astryx focus tokens |

Do not introduce decorative brand colors, gradients, tinted page backgrounds, or large colored panels. Hard-coded colors in individual components are not allowed; define the monochrome treatment through Astryx semantic theme tokens.

### 4.2 Semantic status colors

Restrained semantic colors are permitted where they improve recognition. Each treatment must meet WCAG AA contrast and include a label.

| Status | Required label | Supporting treatment |
| --- | --- | --- |
| Complete | “Ready” or “Complete” | Success icon and restrained green accent |
| Information found | “Information found” | Check icon and restrained green accent |
| Information partly found | “Information partly found” | Partial/warning icon and restrained amber accent |
| Information not found | “Information not found” | Missing/error icon and restrained red accent |
| Processing | “Uploading,” “Checking,” “Processing,” or “Evaluating” | Progress indicator and neutral/accent treatment |
| Failed | “Failed” | Error icon, restrained red accent, and a retry action |
| Unfinished | “Report incomplete” | Warning icon, restrained amber accent, and explanatory text |

Question type, topic, and viewpoint labels use neutral or subdued category treatments. Do not give them the same visual intensity as warnings or errors.

### 4.3 Typography

- Use the Astryx default sans-serif type system.
- The workspace starts with one visible level-one heading. Workflow sections use correctly nested level-two and level-three headings.
- Use sentence case for headings, buttons, labels, and statuses.
- Keep body copy at a comfortable reading size with a line length of approximately 60–75 characters for explanatory content.
- Use tabular numerals where summary counts must align.
- Do not use all caps for emphasis.
- Use bold text sparingly for page titles, section headings, status labels, and the main coverage sentence.

### 4.4 Spacing and containers

- Use the Astryx spacing scale exclusively.
- Use one centered content column with a maximum width of approximately 960 px. Report breakdowns may use the full width of that column.
- Keep the same content width and reading order as the workflow grows; do not switch to a different report layout.
- Use `Section` and dividers for page-level grouping. Do not wrap every region in a card.
- Use cards only when an item has its own interaction boundary, such as an independently expandable question result.
- Use restrained Astryx container radii and low or no elevation. The visual hierarchy should come mainly from spacing, typography, and borders.

### 4.5 Icons and motion

- Use Astryx-compatible semantic icons and always pair status icons with text.
- Do not use decorative illustrations in the core workflow.
- Motion should explain state change, such as progress, expansion, or dialog entry.
- Respect `prefers-reduced-motion`; remove non-essential animation and retain an immediate state change.

## 5. Single-Page Application Structure

Use one `AppShell` with `height="auto"`, an accessible product header, and one growing main content area. The first release does not need side navigation or separate workflow pages.

The header contains:

- UVTS product name linking to a clean workspace.
- The active manual name when a test exists.
- A privacy or data-management entry point when those features are available.

The main area starts with one level-one heading, “Check a manual,” a short explanation, and a compact workflow overview. Render the overview as an accessible ordered list with the text labels “Upload,” “Questions,” “Review,” “Evaluate,” and “Report.” Mark the current item with text such as “Current” and completed items with “Complete”; do not make the overview interactive or build an undocumented custom stepper.

Below the overview, render five `Section` regions in this order:

1. Upload manual
2. Generate questions
3. Review questions
4. Evaluation
5. Report

Only the current stage shows full content. Completed stages show compact summaries, and future stages show a short, muted locked-state sentence explaining what must happen first. Do not hide the workflow or send the writer to a different route.

Each stage uses one of four presentation states:

| Stage state | Presentation |
| --- | --- |
| Locked | Heading, stage number, and one prerequisite sentence; no disabled form controls. |
| Active | Full content and one primary next action. |
| Working | Keep the active content visible, disable duplicate actions, and show a written loading or progress status. |
| Complete | Compact summary with “Complete” or “Ready” and only safe secondary actions. Upload shows the filename and page count; Generate shows the saved setup; Review shows the question count with an option to reveal the list; Evaluation shows final counts. |

The intended page anatomy is:

```text
UVTS                                              Active manual

Check a manual
Upload — Questions — Review — Evaluate — Report

1. Upload manual        [manual.pdf · 12 pages · Ready]
2. Generate questions   [9 questions · Default setup] [Generate questions]
3. Review questions     [numbered question list]       [Evaluate questions]
4. Evaluation           [6 of 9 checked — progress and statuses]
5. Report               [coverage → results → gaps → recommendations]
```

When an action unlocks the next stage:

- Keep completed earlier stages visible in a compact completed state.
- Scroll the newly available section into view only after the user-initiated action succeeds.
- Move keyboard focus to the new section heading without adding it to the normal tab order.
- Update the document title and live region with the new stage and status.
- Preserve the same stage after reload by restoring server state.

When an upstream action would invalidate later work, name the affected questions, evaluation, and report in an `AlertDialog`. Do not clear downstream content until the replacement action succeeds.

## 6. Single-Page Workflow Specification

### 6.1 Upload manual

#### Purpose

Help the writer add one valid manual and understand when it is ready for question generation.

#### Information hierarchy

1. Section heading: “1. Upload manual”
2. Short explanation of what UVTS checks
3. Manual upload
4. Ready-file summary

#### Manual upload

Use `FileInput` in drop-zone mode with the visible label “Upload a PDF manual.” State the known constraints before selection: one readable PDF, 1–20 pages, no password protection, and no image-only scanned pages. Do not state a maximum file size until the product decision is made.

Upload states:

| State | UI behavior |
| --- | --- |
| Empty | Show the drop zone and file rules. Keep Generate questions locked with the explanation “Upload a manual to continue.” |
| Uploading | Show filename, “Uploading,” and progress when known. Prevent selecting another file until upload settles or is canceled by the platform. |
| Checking | Show “Checking the PDF” and explain that UVTS is confirming page count and readable text. |
| Processing | Show “Preparing the manual” and retain the filename. |
| Ready | Show filename, page count, “Ready,” and actions to replace or remove the file. |
| Invalid | Keep the drop zone available, show a persistent error message, and move focus to or announce the error. |

Use the product-approved plain-language errors:

- “Upload a PDF file.”
- “This PDF has 24 pages. UVTS currently supports up to 20 pages.” Replace 24 with the actual count.
- “This PDF is password-protected. Remove the password and upload it again.”
- “UVTS could not read the text in this PDF. Scanned documents are not supported yet.”

If an upload fails for another recoverable reason, explain that the file was not added and provide a “Try again” action. Never clear an error before the user corrects it or dismisses an informational message.

#### Replacing or removing a manual

- If no questions or results exist, allow replacement or removal without a destructive confirmation.
- If generated questions, an unfinished test, or results are connected to the manual, open an `AlertDialog`.
- The dialog title must name the action, for example “Replace this manual?”
- Explain that connected questions and results will be permanently removed.
- Use “Cancel” and a specific destructive action such as “Replace manual” or “Delete manual and results.”
- Keep the dialog open with a loading state until deletion succeeds. On failure, preserve all existing data and show an error.

### 6.2 Generate questions

#### Purpose

Create a question set with sensible defaults while keeping advanced choices available without making setup feel like a separate page.

When the manual is Ready, unlock this section. Show a concise default summary such as “9 questions · all relevant topics · all user viewpoints,” followed by the primary action “Generate questions.” Provide a secondary disclosure labeled “Adjust question settings” containing a vertical `FormLayout` with these fields:

1. **Number of questions** — `NumberInput`, integer only, minimum 1, maximum 15, default 9.
2. **Question types** — `CheckboxList` containing Basic, Cross-paragraph, and Edge-case. At least one is required.
3. **Questions by type** — one `NumberInput` per selected type. Default to an even split; distribute any remainder predictably in the displayed order. The split must equal the total.
4. **Topics** — `CheckboxList` containing the six product-defined topics. Select all topics the system identifies as relevant by default.
5. **User viewpoints** — `CheckboxList` containing Beginner, Regular user, and Advanced user. Select all three by default.

For a topic judged irrelevant, keep it visible but unavailable and show a plain-language reason through the Astryx disabled-message behavior. Do not hide it or rely on a tooltip that cannot be reached by keyboard.

Show validation near the affected group and in a summary near the primary action when submission is attempted. Required messages include:

- “Choose at least one question type.”
- “Choose at least one topic.”
- “Choose at least one user viewpoint.”
- “Enter a number from 1 to 15.”
- “The questions by type must add up to [total].”

Show a concise read-only sentence containing the manual name, total questions, type split, topics, and viewpoints immediately above the action. The only primary action in this stage is “Generate questions.” Disable it until the manual is Ready and the settings are valid. A disabled action must have nearby visible text explaining what remains incomplete.

During generation, keep the upload and settings visible, show the button loading state, and show plain-language status such as “Creating 9 questions.” On success, mark this stage Complete and unlock Review questions. On failure, keep the manual and settings and show “Try again.”

### 6.3 Review questions

#### Purpose

Let the writer verify the complete generated set before starting an immutable evaluation.

#### Information hierarchy

1. Section heading: “3. Review questions”
2. Manual and configuration summary
3. Numbered question list
4. Notice that questions cannot change after evaluation starts
5. Secondary action: “Generate again”
6. Primary action: “Evaluate questions”

Each question shows:

- Its number and complete question text.
- A neutral label for question type.
- Topic in supporting text or a restrained category label.
- User viewpoint in supporting text or a restrained category label.

Keep the entire question text visible. Do not truncate or hide questions behind disclosure controls.

“Generate again” opens an `AlertDialog` because it permanently replaces the current set. Use the title “Generate a new question set?” and explain that the current questions will be removed. Actions are “Keep these questions” and “Generate new questions.” Show a loading state while regeneration runs and do not discard the current set unless the new set succeeds.

“Evaluate questions” is the only primary action. Activating it saves the exact question set, makes it immutable, marks this stage Complete, and unlocks Evaluation directly below. Prevent duplicate starts while the request is pending. If starting fails, keep the questions and show a retryable error.

On narrow screens, stack metadata below each question and place the action bar after the list. A sticky mobile action area may be used only if it does not obscure content or keyboard focus.

### 6.4 Evaluation

#### Purpose

Show that the test is active, communicate exact progress, preserve completed work, and expose recoverable failures.

#### Information hierarchy

1. Section heading: “4. Evaluation”
2. Manual name and question count
3. One determinate `ProgressBar`
4. Plain-language progress sentence, for example “6 of 9 questions checked”
5. Question processing list
6. Failure or completion actions

Each question row shows its number, short or full question text, and one status:

- Waiting
- Checking
- Complete
- Failed

Announce meaningful progress changes through a polite live region without announcing every animation frame. Keep completed rows visible if another question fails.

If one question fails:

- Continue processing the remaining questions.
- Mark the failed row with the written label “Failed.”
- Show a plain-language reason when available.
- Provide “Try this question again.”
- When several questions fail, also provide “Retry failed questions.”
- Never reset completed results during retry.

When all possible questions complete, mark Evaluation Complete and unlock Report directly below it. Scroll and move focus to the Report heading after report finalization succeeds. If failures remain, unlock the report in its incomplete state, show a warning `Banner`, and retain retry actions in both Evaluation and Report.

Whether a writer can stop a running test is an unresolved product decision. Do not display a stop or cancel action until that decision is made.

### 6.5 Report

#### Purpose

Help the writer understand coverage, inspect evidence, find important gaps, and decide what to improve next.

The report is the final section of the same page, not a destination page. Earlier stages remain above it in compact completed states. The report begins with the section heading “5. Report.”

#### Report order

1. Test summary
2. Coverage overview
3. Question results
4. Main gaps
5. Recommendations
6. Follow-up

#### Test summary

Show the exact main-result pattern prominently:

> X questions are covered out of Y total questions.

Only “Information found” counts toward X. Also show counts for partly found, not found, and failed. The counts must add up to the total.

Supporting metadata includes manual name, page count, test date, total questions, question-type split, selected topics, and selected viewpoints. Use plain text or a `MetadataList`; do not render dates, counts, or filenames as badges.

If unfinished or failed questions exist, place a persistent warning `Banner` before the summary. State that the report is incomplete, show how many questions remain, and provide a retry action.

#### Coverage overview

Show breakdowns by:

- Question type
- Topic
- User viewpoint

Start with readable grouped counts or horizontal bars, not decorative charts. Every visualization must include visible labels and exact values. It must remain understandable in monochrome, at 200% zoom, and to screen-reader users through an equivalent text representation.

#### Question results

Display results in a `CollapsibleGroup` that allows multiple questions to remain open for comparison. Each collapsed trigger shows:

- Question number and text.
- Written result status.
- Type, topic, and viewpoint.

Keep the status visible without expansion. Expanded content shows:

1. Information needed
2. Information found
3. Information missing or unclear
4. Page evidence

For “Information found” and “Information partly found,” show at least one real page reference and a short extract or simple evidence note. Show multiple pages when the needed information is spread across the manual.

For “Information not found,” show the exact message “No supporting information found.” Do not show a page placeholder or inferred reference.

Do not generate or display an answer to the question. Clearly state that the status measures whether information exists, not whether it is accurate, clearly written, or safe.

#### Main gaps

Group missing or incomplete information by subject. Every gap includes:

- A plain-language title.
- Why the gap matters.
- Links to or identifiers for affected questions.
- Whether the gap is missing information or incomplete/scattered information.

Selecting an affected question moves focus to the corresponding question result and opens it without losing the writer’s place unexpectedly.

#### Recommendations

Every recommendation must connect to at least one gap or question. Recommend changes to the manual, not changes to the product.

Show a written priority:

- **High:** May stop a common task or affect safety, privacy, or important data.
- **Medium:** May cause mistakes or support requests because information is incomplete or scattered.
- **Low:** Information exists but could be easier to find or understand.

Priority may use restrained semantic emphasis but must not rely on color. Each recommendation contains the suggested writing change, its reason, and the linked supporting results.

#### Follow-up

Show suggested questions to use after the manual is updated and a clear recommendation to run the test again. If failed questions remain, list them separately.

Available actions are:

- “Start another test with this manual” for different choices.
- “Test an updated manual” for a replacement manual.
- “Retry failed questions” when applicable.

Do not include report download, sharing, team comments, comparison, or approval actions in the first release.

## 7. Responsive Behavior

The first release supports wide desktop and narrow mobile-width browser layouts.

### Wide screens

- Use one centered column throughout the workflow.
- Related report summary counts may appear in a responsive grid within that column.
- Keep report reading order identical to the visual order.

### Narrow screens

- Keep the existing single-column workflow and collapse only report summary grids into one vertical flow.
- Keep the primary action full-width when that improves reach and clarity.
- Wrap metadata and category labels; never truncate essential status or question text.
- Allow tables or grids to become labeled stacked groups rather than forcing horizontal scrolling.
- Keep dialogs within the viewport and preserve focus trapping and focus return.
- Maintain touch targets of at least 44 by 44 CSS pixels where practical.

Test at 320 px width, 200% browser zoom, long filenames, long generated questions, and large translated labels even though localization is not a first-release feature.

## 8. Accessibility Requirements

Target WCAG 2.2 AA and preserve all applicable Astryx accessibility behavior.

- All functions must work with keyboard only.
- Use a logical focus order matching the reading order.
- The workspace has one level-one heading and correctly nested section headings.
- Use visible labels; placeholders are not labels.
- Provide visible, high-contrast `:focus-visible` treatment on every interactive element.
- Move focus to the first invalid field or an error summary after failed form submission.
- Announce upload, generation, testing, retry, success, and failure changes through appropriate live regions.
- Do not repeatedly announce routine progress updates more often than necessary.
- Dialogs must trap focus, focus the least destructive action first, close on Escape where Astryx specifies, and return focus to the trigger.
- Disabled controls that need explanation remain keyboard discoverable through Astryx disabled-message behavior or nearby visible text.
- Statuses always contain words; icons are supplementary and decorative icons are hidden from assistive technology.
- Evidence extracts, result counts, and progress values must be available as text.
- The interface must remain usable with reduced motion, high zoom, and reflow.

## 9. Validation, Loading, Empty, and Error Patterns

### Validation

- Validate as the writer completes a field or attempts to continue; do not show errors on initial page load.
- Place messages beside the relevant control and summarize multiple errors near the action area.
- Preserve valid entries when another field is invalid.
- State the problem and the next action in one or two short sentences.

### Loading

- Use a button loading state for local actions and a labeled `ProgressBar` for known multi-item work.
- Retain the current content during regeneration or retry until replacement content succeeds.
- Prevent duplicate submissions without making the page appear frozen.
- If processing takes longer than expected, show reassurance without promising a time until performance targets are decided.

### Empty states

- No manual: explain the supported file and provide the upload control.
- No generated questions after a failed request: explain that no set was saved and provide “Try again.”
- No gaps or recommendations: state that the tested questions did not reveal missing information, followed by the report limitation notice.
- No evidence: use “No supporting information found” only for an Information not found result.

### Errors

- Use a persistent `Banner` for blocking or workflow-level errors.
- Use attached field status for local validation errors.
- Keep user data and completed results whenever retry is possible.
- Never show raw exception messages, stack traces, model names, or request identifiers as the main error message.
- A support reference may appear in secondary details if operational support requires it.

## 10. Confirmation and Data Safety

Use `AlertDialog` only when an action is irreversible or discards meaningful work.

| Action | Confirmation requirement | Data behavior |
| --- | --- | --- |
| Replace an unused upload | No dialog | Replace the file. |
| Replace a manual with connected questions/results | Confirm | Delete the old manual’s questions and results only after replacement succeeds or the product’s transaction behavior is defined. |
| Remove an unused upload | No dialog | Remove the file. |
| Delete a manual with connected data | Confirm | Delete the manual, unfinished questions, and connected results. |
| Generate questions again | Confirm | Keep the existing set until the replacement set succeeds. |
| Start a test | No destructive dialog; show an immutability notice | Save and lock the exact question set. |
| Retry failed questions | No dialog | Preserve all completed results. |

Confirmation copy must name the item and consequence. Avoid generic actions such as “OK” or “Confirm.” If an irreversible operation fails, keep the original data and show what the writer can try next.

## 11. Content Design

- Address the person directly as “you” only when it makes an instruction clearer; otherwise use neutral action language.
- Use “manual” consistently for the uploaded PDF.
- Use “test” for the UVTS checking process.
- Use the exact statuses “Information found,” “Information partly found,” and “Information not found.”
- Say “page” rather than “source location” or “citation.”
- Keep buttons verb-led: “Upload PDF,” “Generate questions,” “Evaluate questions,” and “Retry failed questions.”
- Explain the consequence before destructive actions.
- Do not imply that UVTS tests the product, watches real users, checks factual accuracy, or replaces legal, safety, or expert review.

Every report includes this limitation in visible text:

> UVTS checks whether information exists in this manual. It does not confirm that the information is correct, safe, clearly written, or complete for every possible user. Its suggestions do not replace legal, safety, or expert review.

## 12. Privacy and Retention

The interface must state that manuals and reports are private and protected, and that uploaded manuals are not used to train general AI models without clear permission.

The writer must be able to delete a manual and its connected results. Deletion uses the confirmation behavior in this specification.

Do not invent retention copy. The product must decide how long manuals and reports are kept before the UI displays a duration. Until then, mark retention messaging as pending in design and engineering work rather than showing a vague or misleading promise to users.

## 13. First-Release Boundaries

Do not design active controls for:

- More than one manual in a test.
- Manuals over 20 pages.
- Files other than readable PDFs.
- Scanned-PDF text recognition.
- More than 15 questions.
- Editing individual generated questions.
- Comparing manual versions.
- Downloading or sharing reports.
- Team comments or approvals.
- Connections to support, document, or project-management systems.
- Factual, readability, consistency, legal, or safety validation.

Future capabilities may be mentioned only as unavailable when needed to explain a validation message. Do not display disabled navigation for speculative features.

## 14. Product Decisions Required Before Final UI

The following decisions remain dependencies. The implementation must not guess them:

| Decision | UI affected |
| --- | --- |
| Whether accounts are required | Entry flow, header, saved data, and deletion access |
| Maximum PDF file size | FileInput description and validation copy |
| Manual and report retention period | Privacy notice, data management, and deletion copy |
| Whether a running test can be stopped | Evaluation actions and confirmation behavior |
| Expected question-generation and testing time | Loading guidance, timeout states, and delayed-work messaging |
| Release accuracy threshold and review method | Internal quality process; do not expose an unsupported accuracy claim in the UI |

## 15. Design Acceptance Checklist

The UI/UX is ready for implementation when:

- The complete path from valid PDF upload to report is represented.
- Upload, question generation, question review, evaluation, and report remain in one ordered page without workflow navigation.
- Completed stages stay visible, future stages explain their prerequisites, and reload restores the current stage.
- Successful transitions scroll and move focus to the newly available section without disorienting the writer.
- Invalid file type, page limit, password protection, unreadable text, and upload failure have explicit behavior and copy.
- The 1–15 question rule, required selection groups, and exact type-total validation are represented.
- Question regeneration preserves the current set until the new set succeeds.
- Starting a test locks the exact reviewed questions.
- Testing shows completed out of total and preserves completed results when another question fails.
- Failed questions can be retried individually and together without resetting successful results.
- Report counts reconcile with individual statuses and failures.
- Found and partly found results show real page evidence; not found results show no invented reference.
- Gaps link to affected questions and recommendations link to supporting gaps or results.
- Every destructive action states its consequence and uses an accessible confirmation flow.
- White surfaces and black text dominate while semantic colors remain restrained and labeled.
- Desktop, 320 px width, 200% zoom, keyboard-only use, visible focus, screen-reader announcements, and reduced motion are covered.
- No first-release boundary or unresolved product decision has been silently designed as a completed feature.
