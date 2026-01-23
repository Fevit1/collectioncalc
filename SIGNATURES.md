# Creator Signature Reference Database

## Purpose
Collect verified creator signatures for future AI-powered signature identification.
When a user uploads a signed comic, we can compare against these references to improve "WHO signed" accuracy.

## How to Use
1. Find verified signatures (eBay ~$1 each, convention photos, CGC/CBCS verified)
2. Save image to `/signatures/` folder (create when ready)
3. Add entry to this file
4. Filename format: `firstname_lastname_01.jpg` (number for multiple samples)

## Collection Status

| Creator | Role | Samples | Verified Source | Notes |
|---------|------|---------|-----------------|-------|
| Danny Miki | Inker | 1 | eBay/Facebook | Long horizontal stroke with loop |
| David Finch | Artist | 1 | eBay/Facebook | Writes "Finch" clearly readable |

## Priority Creators to Collect
High-frequency signers at conventions:

### Artists (Most Common Signers)
- [ ] Jim Lee
- [ ] Todd McFarlane
- [ ] Rob Liefeld
- [ ] Greg Capullo
- [ ] Alex Ross
- [ ] J. Scott Campbell
- [ ] Stanley "Artgerm" Lau
- [ ] Frank Miller
- [ ] John Romita Jr.
- [ ] Mark Bagley

### Writers
- [ ] Stan Lee (deceased - historical reference)
- [ ] Chris Claremont
- [ ] Scott Snyder
- [ ] Geoff Johns
- [ ] Brian Michael Bendis
- [ ] Tom King
- [ ] Donny Cates

### Inkers/Colorists
- [x] Danny Miki ✓
- [ ] Klaus Janson
- [ ] Scott Williams
- [ ] Alex Sinclair

## Implementation Notes
- Store images in a `/signatures/` folder when ready to implement
- Each creator can have multiple samples for better matching
- Include both "clean" signatures and "on cover" examples if possible
- Consider storing signature characteristics (ink color preferences, style notes)

## Future Feature: Signature Comparison
When implementing:
1. User uploads signed comic
2. Opus detects signature exists
3. Pass signature crop + reference images to Claude
4. Claude compares: "Does this match Danny Miki, David Finch, or neither?"
5. Return higher-confidence identification

---

*Last updated: January 22, 2026 (Session 7)*
