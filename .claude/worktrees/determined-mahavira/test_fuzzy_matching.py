"""Quick test to demonstrate fuzzy title matching and creator extraction"""

from title_normalizer import normalize_title

# Test cases with messy/misspelled titles from known list
test_cases = [
    # Fuzzy matching should normalize these
    "AMZING SPIDER MAN #1 CGC 9.8",  # Misspelling
    "Amazing Spiderman 300",          # Missing hyphen
    "Uncany X-Men #266 CGC 9.6",      # Misspelling
    "The Walking Dead #1",            # With "The"
    "Walking Dead 19 CGC 9.8",        # Without "The"
    "Batman Dark Knight Returns TPB", # Partial title match

    # Creator extraction
    "Amazing Spider-Man #1 Todd McFarlane variant CGC 9.8",
    "X-Men #1 Jim Lee cover",
    "Daredevil #1 Frank Miller run",
    "Batman #1 Scott Snyder Signed CGC 9.8",
    "Spawn #1 Todd McFarlane Image Comics",
    "Department of Truth #1 James Tynion IV Martin Simmonds NYCC",
]

print("=" * 100)
print("FUZZY MATCHING & CREATOR EXTRACTION TEST")
print("=" * 100)

for raw in test_cases:
    result = normalize_title(raw)
    print(f"\nRAW:      {raw}")
    print(f"  Title:    {result['canonical_title']}")
    print(f"  Issue:    {result['issue_number']}")
    if result['creators']:
        print(f"  Creators: {result['creators']}")
    if result['title_notes']:
        print(f"  Notes:    {result['title_notes']}")
