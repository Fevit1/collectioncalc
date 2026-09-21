# Signed-versus-unsigned premium from `ebay_sales` — 2026-09-21

Report only. Read-only database, no model calls, **$0**. Script: `scripts/signed_premium_report.py`. Last 365 days.

## Method — and why this report reads rows the valuation throws away
The valuation code EXCLUDES signed sales from every pool on purpose: a signature is a second price driver it cannot
attribute, so signed sales would contaminate the unsigned comps a user is priced against. This report reads them on
purpose — the premium is the thing being measured.
- **Pair** = `canonical_title` + `issue_number`. Lots, reprints, facsimiles and variants are excluded, as in the pools.
- **Slabbed** = `graded` (a grading company was parsed from the title); band from `grade`. **Raw** = not graded; band
  from `grade_from_title` — **the SELLER-STATED grade; every raw cell is a listing-stated grade, not a certified one.**
- **Signed** = the title matches `signature series | ss | signed | autograph(ed) | auto | verified signature | vsp |
  sig(nature)` and does not match `unsigned | not signed | facsimile/printed sig | signature page/stamp`. It is this
  report's own rule, not the stored `is_signed` flag; the two agree on 84,660 of 85,000 rows, and the rule finds 336
  signed rows the flag misses (mostly "SS" and "auto"), the flag finds 4 the rule misses.
- **Witnessed** = a slabbed signed row whose TITLE says Signature Series / SS / Verified Signature / VSP / yellow label.
- **Signer** = an in-set creator named in the title, else the words after "signed by" as written.

## ⚠️ Three things that limit what these numbers mean
1. **"Unwitnessed" is really "witness not stated in the title".** A signed book in a CGC slab is either Signature
   Series (yellow) or Qualified (green); sellers often write "CGC 9.8 signed by Scott Snyder" with no "SS". The
   right-hand column is therefore a MIX of true Signature Series and green-label books, and it is often the larger
   column (Absolute Batman #1 at 9.8: 121 vs 45). It cannot be split further from listing text; the slab label in
   the photo could — a vision read, not run. Do not read "unwitnessed beats witnessed" as a finding.
2. **Pairs are EDITION-BLIND.** `X-Men #1` mixes 1963 and 1991 (the $3,721 and $11,750 cells in its low band are
   1963 books); `Spider-Man #1`, `Spawn #1` and others carry the same risk less visibly. The premium within a band
   is still mostly like-for-like because the editions separate by price, but no cell is edition-clean.
3. **False positives in "signed":** "SS" can be part of a title or a seller's shorthand for something else; "auto"
   and "sig" are loose; a "signed" COA'd reprint or a signed PRINT sold with a book will count. False negatives:
   "w/ sketch", "remarked", a signer's name alone. At the pair level the counts are large enough that the direction
   is safe and the second decimal is not.
Small cells (n < 5) are shown because Mike asked for counts in every cell; they are not evidence.

## Headline
20 pairs shown of **82** that qualify (>= 10 signed AND >= 10 unsigned graded sales).
Cells with n>=5 on both sides (top 20 pairs, bands 9.0-9.6 and 9.8+): witnessed/unsigned multiple median 2.23x over 17 cells (range 0.65-7.32); label-not-stated/unsigned median 2.21x over 30 cells (range 0.92-4.93).
The premium is LARGEST on cheap modern books signed by their creator (Spider-Man #1, Spawn #1, X-Men #1 (1991): a
$70–$130 slab becomes $350–$470) and SMALLEST, in multiple terms, on books that are already expensive (ASM #300: a
$640 9.0–9.6 slab becomes ~$1,000–$1,175; at 9.8 the signed cells are BELOW unsigned on n ≤ 4). A signature adds
something closer to a flat dollar amount than a percentage — which is what a signing VERDICT needs to know.
**One anomaly, unexplained:** Absolute Batman #1's title-stated Signature Series cells sit BELOW unsigned (0.65× at
9.0–9.6 on n=11, 0.96× at 9.8+ on n=45) while its label-not-stated signed cells sit well above (1.5×). Later
printings are not separated from first printings in this table and are the first suspect; not investigated.
**TO DO when this report is next touched (Mike, 2026-09-21): a ONE-LINE look** — split Absolute Batman #1's
stated-SS rows by printing (title text: "2nd print", "3rd printing", …) and re-read the two cells. Accepted as is until then.
Raw signed books carry a premium too, on seller-stated grades: Absolute Batman #1 at 9.8+ raw, $600 signed (n=95).

## Top 20 pairs by total sample

### Absolute Batman #1 — 1471 sales (368 signed, 1103 unsigned) — signer(s): Scott Snyder 118, Daniel Warren Johnson 11, Skottie Young 6
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $140 (n=6) | — | — | — | — |
| 8.0-8.9 | $80 (n=31) | $212 (n=2) | $229 (n=2) | — | — |
| 9.0-9.6 | $250 (n=505) | $310 (n=78) | $306 (n=60) | $200 (n=11) | $382 (n=16) |
| 9.8+ | $37 (n=1) | $600 (n=95) | $470 (n=498) | $450 (n=45) | $725 (n=121) |

### Spider-Man #1 — 996 sales (236 signed, 760 unsigned) — signer(s): Todd McFarlane 190, Stan Lee 25
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $15 (n=13) | $61 (n=1) | $39 (n=6) | — | $426 (n=2) |
| 8.0-8.9 | $22 (n=35) | — | $42 (n=14) | $130 (n=1) | $792 (n=5) |
| 9.0-9.6 | $22 (n=291) | $210 (n=28) | $65 (n=139) | $250 (n=10) | $273 (n=34) |
| 9.8+ | $70 (n=1) | $350 (n=47) | $90 (n=261) | $350 (n=51) | $340 (n=57) |

### X-Men #1 — 766 sales (117 signed, 649 unsigned) — signer(s): Jim Lee 80, Chris Claremont 44, Stan Lee 7
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $29 (n=6) | $79 (n=1) | $3,721 (n=14) | — | $11,750 (n=4) |
| 8.0-8.9 | $10 (n=40) | — | $23 (n=10) | $200 (n=1) | — |
| 9.0-9.6 | $10 (n=153) | $80 (n=11) | $41 (n=127) | $300 (n=9) | $202 (n=18) |
| 9.8+ | $25 (n=1) | $300 (n=9) | $72 (n=298) | $250 (n=23) | $325 (n=41) |

### Amazing Spider-Man #300 — 547 sales (80 signed, 467 unsigned) — signer(s): Todd McFarlane 58, Stan Lee 10, McFarlane. ASM (as written) 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $334 (n=6) | $490 (n=1) | $350 (n=45) | $500 (n=5) | $585 (n=5) |
| 8.0-8.9 | $417 (n=31) | $797 (n=4) | $450 (n=75) | $680 (n=3) | $720 (n=9) |
| 9.0-9.6 | $530 (n=54) | $970 (n=9) | $640 (n=223) | $1,175 (n=20) | $995 (n=19) |
| 9.8+ | — | — | $2,900 (n=33) | $2,488 (n=4) | $2,140 (n=1) |

### Spawn #1 — 463 sales (104 signed, 359 unsigned) — signer(s): Todd McFarlane 96, Al Simmons (as written) 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $16 (n=9) | — | $75 (n=1) | $124 (n=1) | — |
| 8.0-8.9 | $22 (n=29) | $75 (n=3) | $47 (n=7) | — | — |
| 9.0-9.6 | $28 (n=122) | $299 (n=11) | $73 (n=72) | $296 (n=17) | $280 (n=5) |
| 9.8+ | — | $500 (n=12) | $130 (n=119) | $470 (n=39) | $450 (n=16) |

### New Mutants #98 — 459 sales (58 signed, 401 unsigned) — signer(s): Rob Liefeld 44, Stan Lee 7
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $250 (n=7) | — | $250 (n=12) | — | $318 (n=2) |
| 8.0-8.9 | $300 (n=14) | $400 (n=1) | $300 (n=33) | $345 (n=5) | $450 (n=2) |
| 9.0-9.6 | $345 (n=49) | $764 (n=6) | $400 (n=215) | $600 (n=9) | $512 (n=18) |
| 9.8+ | — | $400 (n=1) | $999 (n=71) | $1,961 (n=7) | $1,600 (n=7) |

### Secret Wars #8 — 410 sales (28 signed, 382 unsigned) — signer(s): Stan Lee 5, Mike Zeck 3, Jim Shooter (as written) 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $162 (n=4) | $400 (n=3) | $177 (n=24) | — | $260 (n=1) |
| 8.0-8.9 | $170 (n=24) | $265 (n=1) | $225 (n=25) | $200 (n=1) | $450 (n=2) |
| 9.0-9.6 | $220 (n=48) | $750 (n=3) | $305 (n=188) | $438 (n=2) | $550 (n=8) |
| 9.8+ | $472 (n=2) | $1,250 (n=1) | $620 (n=67) | $3,000 (n=1) | $1,600 (n=5) |

### Uncanny X-Men #266 — 392 sales (37 signed, 355 unsigned) — signer(s): Chris Claremont 18, Stan Lee 4, Jim Lee 2
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $130 (n=7) | $300 (n=1) | $142 (n=8) | $175 (n=1) | — |
| 8.0-8.9 | $134 (n=24) | — | $150 (n=23) | $600 (n=1) | $250 (n=1) |
| 9.0-9.6 | $175 (n=69) | $450 (n=7) | $225 (n=173) | $357 (n=6) | $375 (n=10) |
| 9.8+ | — | $2,000 (n=1) | $499 (n=51) | $900 (n=3) | $759 (n=6) |

### Secret Wars #1 — 387 sales (29 signed, 358 unsigned) — signer(s): Stan Lee 4, Jim Shooter (as written) 3, Mike Zeck 3
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $51 (n=14) | $66 (n=1) | $52 (n=6) | — | — |
| 8.0-8.9 | $25 (n=59) | $16 (n=1) | $58 (n=8) | — | — |
| 9.0-9.6 | $34 (n=128) | $100 (n=4) | $90 (n=79) | $250 (n=3) | $271 (n=6) |
| 9.8+ | — | $225 (n=2) | $217 (n=64) | $380 (n=5) | $699 (n=7) |

### Absolute Batman #15 — 372 sales (127 signed, 245 unsigned) — signer(s): Scott Snyder 53, SNYDER DRAGOTTA JOCK (as written) 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $12 (n=3) | $110 (n=1) | — | — | — |
| 9.0-9.6 | $12 (n=113) | $50 (n=30) | $50 (n=5) | — | $101 (n=6) |
| 9.8+ | — | $188 (n=55) | $60 (n=124) | $290 (n=14) | $200 (n=21) |

### Absolute Superman #1 — 361 sales (38 signed, 323 unsigned) — signer(s): Jason Aaron 17, Skottie Young 5, Clayton Crain 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $17 (n=3) | — | — | — | — |
| 9.0-9.6 | $29 (n=184) | $95 (n=7) | $41 (n=4) | — | $150 (n=1) |
| 9.8+ | — | $312 (n=20) | $110 (n=132) | $196 (n=2) | $326 (n=8) |

### Absolute Batman #9 — 348 sales (35 signed, 313 unsigned) — signer(s): Scott Snyder 19
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $15 (n=1) | $160 (n=1) | — | — | — |
| 8.0-8.9 | $43 (n=4) | — | — | — | — |
| 9.0-9.6 | $45 (n=195) | $88 (n=11) | $70 (n=6) | $148 (n=1) | $250 (n=3) |
| 9.8+ | — | $440 (n=9) | $155 (n=107) | $404 (n=4) | $292 (n=6) |

### Venom Lethal Protector #1 — 347 sales (44 signed, 303 unsigned) — signer(s): Mark Bagley 8, Stan Lee 3, Alex Ross 2
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $18 (n=2) | — | $174 (n=2) | $195 (n=1) | — |
| 8.0-8.9 | $15 (n=20) | $115 (n=2) | $34 (n=6) | — | $338 (n=1) |
| 9.0-9.6 | $24 (n=114) | $112 (n=10) | $70 (n=43) | $170 (n=1) | $124 (n=9) |
| 9.8+ | — | $540 (n=3) | $125 (n=116) | $250 (n=10) | $600 (n=7) |

### Teenage Mutant Ninja Turtles #1 — 338 sales (48 signed, 290 unsigned) — signer(s): Kevin Eastman 15, Art Adams 3, Skottie Young 3
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $30 (n=10) | — | $250 (n=9) | — | — |
| 8.0-8.9 | $15 (n=32) | $75 (n=1) | $225 (n=9) | — | — |
| 9.0-9.6 | $21 (n=118) | $23 (n=16) | $104 (n=44) | $175 (n=4) | $145 (n=5) |
| 9.8+ | — | $501 (n=4) | $172 (n=68) | $300 (n=3) | $158 (n=15) |

### Absolute Batman #2 — 331 sales (29 signed, 302 unsigned) — signer(s): Scott Snyder 4, Daniel Warren Johnson 4, Jae Lee 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $47 (n=9) | — | $75 (n=1) | — | — |
| 9.0-9.6 | $50 (n=185) | $130 (n=13) | $70 (n=8) | $315 (n=1) | $175 (n=1) |
| 9.8+ | — | $295 (n=7) | $142 (n=99) | $400 (n=1) | $330 (n=6) |

### Wolverine #1 — 309 sales (32 signed, 277 unsigned) — signer(s): Chris Claremont 12, Frank Miller 2, Stan Lee 2
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $70 (n=13) | $82 (n=2) | $70 (n=7) | — | $122 (n=2) |
| 8.0-8.9 | $58 (n=28) | $250 (n=1) | $86 (n=22) | $245 (n=1) | $200 (n=3) |
| 9.0-9.6 | $98 (n=62) | $350 (n=3) | $125 (n=93) | $325 (n=3) | $350 (n=9) |
| 9.8+ | — | — | $284 (n=52) | $925 (n=2) | $645 (n=6) |

### Absolute Batman #3 — 287 sales (22 signed, 265 unsigned) — signer(s): Scott Snyder 6, Gabriele Dell'Otto 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $36 (n=9) | — | — | — | — |
| 9.0-9.6 | $40 (n=152) | $130 (n=5) | $41 (n=11) | — | $182 (n=4) |
| 9.8+ | — | $325 (n=3) | $118 (n=93) | $340 (n=5) | $255 (n=5) |

### Absolute Batman #10 — 279 sales (34 signed, 245 unsigned) — signer(s): Scott Snyder 10, Gabriele Dell'Otto 1, Nick Dragotta (as written) 1
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $100 (n=15) | — | — | — | — |
| 9.0-9.6 | $112 (n=161) | $138 (n=8) | $118 (n=12) | — | $206 (n=4) |
| 9.8+ | — | $326 (n=15) | $300 (n=57) | $510 (n=1) | $522 (n=6) |

### Absolute Wonder Woman #1 — 272 sales (17 signed, 255 unsigned) — signer(s): Skottie Young 6
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | — | — | — | — | — |
| 8.0-8.9 | $30 (n=3) | — | — | — | — |
| 9.0-9.6 | $50 (n=130) | $75 (n=9) | $108 (n=2) | — | — |
| 9.8+ | — | $300 (n=4) | $130 (n=120) | $695 (n=1) | $399 (n=3) |

### Amazing Spider-Man #361 — 264 sales (29 signed, 235 unsigned) — signer(s): Mark Bagley 14, Stan Lee 3
| band | raw unsigned | raw signed | slab unsigned | slab signed WITNESSED | slab signed unwitnessed |
|---|---|---|---|---|---|
| 4.5-7.9 | $60 (n=3) | $78 (n=2) | $44 (n=6) | — | $224 (n=2) |
| 8.0-8.9 | $75 (n=17) | $166 (n=2) | $75 (n=13) | — | — |
| 9.0-9.6 | $86 (n=43) | $248 (n=8) | $130 (n=105) | $290 (n=5) | $232 (n=4) |
| 9.8+ | $300 (n=1) | $400 (n=1) | $310 (n=47) | $445 (n=2) | $750 (n=3) |

