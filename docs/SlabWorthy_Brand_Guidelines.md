# Slab Worthy brand guidelines

Status: canonical. Created 2026-08-30 to resolve a documented conflict between CLAUDE.md and the live stylesheet. Where this document and any other source disagree, this document wins and the other source should be corrected. Decision of record, 2026-08-30 (Mike): gold is part of the brand, not merely part of the wordmark. This resolves the open question raised in claude/SW_envelope_insert_claims_audit_2026-08-28.md and creates a code action, below. Supersedes: the brand fragment in CLAUDE.md and the "brand token drift" section of the envelope insert claims audit.

> This .md is the source of truth; `docs/SlabWorthy_Brand_Guidelines.docx` is the human-reading copy of the same content, and `claude/SW_BRAND_GUIDELINES.md` in Claude project storage is a DO-NOT-EDIT mirror. Brand changes land here first and are mirrored outward, never the reverse.

## The conflict this document resolves

Two sources described the brand and did not agree.

CLAUDE.md said: $LAB WORTHY, purple and gold, Bangers wordmark, gold #facc15, purple accent #7c3aed, favicon a gold dollar sign on black at an 8 degree tilt.

The live slabworthy.com/styles.css :root described an indigo, purple and cyan system with no gold token at all. Only #7c3aed existed in both.

Anyone building from one source produced collateral that did not match anyone building from the other. The envelope insert of 2026-08-28 papered over this by choosing, and that choice is now ratified: gold is a brand colour.

⚠️ Open code action. #facc15 is not currently a token in the live stylesheet. Until it is added, the product UI is off-brand against this document. See "Code actions" at the end.

## Colour

### Brand colours

| Role | Token | Hex | Notes |
|---|---|---|---|
| Brand gold | `--brand-gold` | #facc15 | Not yet in the stylesheet. Wordmark, dollar mark, value moments. |
| Brand purple | `--brand-purple` | #7c3aed | The one colour present in every source. The connective accent. |
| Brand indigo | `--brand-indigo` | #4f46e5 | Gradient partner, borders, structure. |
| Brand cyan | `--brand-cyan` | #06b6d4 | Value gradient partner. Use sparingly. |

### Surfaces and text

| Role | Token | Hex |
|---|---|---|
| Background primary | `--bg-primary` | #0f0f1a |
| Background secondary | `--bg-secondary` | #1a1a2e |
| Text primary | `--text-primary` | #ffffff |
| Text secondary | `--text-secondary` | #94a3b8 |
| Text muted | `--text-muted` | #64748b |
| Border default | `--border-default` | #334155 |
| Border accent | `--border-accent` | #4f46e5 |

### Status

| Role | Token | Hex |
|---|---|---|
| Success | `--status-success` | #10b981 |
| Warning | `--status-warning` | #f59e0b |
| Error | `--status-error` | #ef4444 |

⚠️ Warning amber #f59e0b sits close to brand gold #facc15. Do not use gold for anything that could read as a warning state, and do not use amber decoratively. Keep the two on separate duties or users will misread one for the other.

### Gradients

--brand-gradient: linear-gradient(135deg, #4f46e5, #7c3aed) — structural, headers, brand surfaces.

--value-gradient: linear-gradient(135deg, #06b6d4, #7c3aed) — value and numeric emphasis.

Gradients do not print reliably. See the print section.

### Meta

Page theme-color meta is #1e1b4b.

## What gold is for

Gold is the value colour. The product exists to tell a collector what a book is worth and whether spending money on grading pays off, and the wordmark is a dollar sign for that reason. Gold marks the moment where value is asserted.

Use gold for: the wordmark and dollar mark; the headline FMV figure; the slabbing verdict; a single primary emphasis per screen.

Do not use gold for: body copy, large filled areas, warning or error states, or more than one emphasis in the same view. Gold that appears everywhere stops meaning anything, which is the same failure the grading rubric has with defect flags.

Purple remains the connective accent and does the everyday work: links, bullets, rules, secondary emphasis.

## Contrast, measured

Real numbers, because "gold on dark looks fine" is not a specification.

| Pair | Ratio | Verdict |
|---|---|---|
| Gold #facc15 on #0f0f1a | 12.4:1 | Passes AAA. The primary brand pairing. |
| Gold #facc15 on white | 1.5:1 | Fails everything. Never do this. |
| Purple #7c3aed on #0f0f1a | 3.3:1 | Large text only. Fails AA for body copy. |

Two rules follow and they are not negotiable.

Gold never sits on white. On light backgrounds the wordmark drops to #0f0f1a and gold accents become #7c3aed. This is what the light insert variant does and it is the correct behaviour, not a compromise.

Purple is not a body-text colour on dark. At 3.3:1 it is legal for large display text and illegal for paragraphs. Body copy is #94a3b8 or lighter.

## Typography

Bangers — wordmark and dollar mark only. Never body copy, never headings, never UI. It is a logo face.

Inter — everything else. Body, headings, UI, numerals.

When embedding for print or offline use, subset and embed both as base64 rather than linking Google Fonts, so the artifact prints correctly with no network. A web-fonts variant is acceptable as a lighter alternate but must be labelled as requiring a connection.

## The wordmark

Written $LAB WORTHY with a superscript ™.

The $ is gold #facc15.

Favicon is a gold dollar sign on black, tilted 8 degrees.

The 8 degree tilt belongs to the favicon and standalone dollar mark. Do not tilt the full wordmark.

On light backgrounds the wordmark is #0f0f1a, with the dollar mark permitted to stay gold only if it sits on its own dark tile.

⚠️ Common error: "SLAB WORTHY" without the dollar sign. This was live in the footer and was corrected on 2026-07-29. It is wrong everywhere.

## Print and physical collateral

Learned building the 2026-08-28 envelope insert. These are not preferences, they are failures already paid for.

Lighten body greys. Web #94a3b8 goes muddy on a home inkjet over near-black. Use #b6c2d2. Purple fine print #7c3aed becomes #a78bfa.

Inset the dark panel from the trim. Home printers cannot bleed, so a full-bleed dark card cut at the panel edge shows a ragged white margin. An inset panel reads as an intentional frame.

Avoid gradients. They do not paint reliably in Chromium print. Use solid segments.

QR codes are dark-on-white on their own tile, always. Never invert a QR onto a dark panel; many scanners fail on light-module codes. Verify every QR decodes from the rendered PDF at 300 dpi before printing.

Sizing: the shipped insert is 5.5 x 8.5 portrait, 2-up on 11 x 8.5 landscape letter, printed at 100% with no scale-to-fit, one vertical cut.

Thin dividers inside flex columns collapse. An empty 5px rule inside a column flex container is shrunk to zero height. Set flex:none on it. This trap applies in the app as well as in print.

## Existing assets

claude/creatives/slabworthy_insert_dark.html — shipped variant, fonts embedded.

claude/creatives/slabworthy_insert_light.html — ink-economy alternate, never printed.

Google Drive, folder Slab Worthy — Envelope Insert 2026-08-28 — web-fonts copy.

Regenerate print PDFs with:

```bash
chrome --headless --no-pdf-header-footer --print-to-pdf=out.pdf slabworthy_insert_dark.html
```

## Code actions arising from this decision

Add --brand-gold: #facc15 to styles.css :root. Until this lands, the stylesheet does not describe the brand.

Decide where gold appears in the product UI. Per the "what gold is for" section, the candidates are the FMV figure and the slabbing verdict. This is a taste call, not an engineering one, and needs Mike before implementation.

Correct the brand fragment in CLAUDE.md to point at this document rather than restating a partial palette.

Audit for SLAB WORTHY without the dollar sign, which has recurred once already.

None of these are on the critical path against the grading calibration work, and none should displace it.
