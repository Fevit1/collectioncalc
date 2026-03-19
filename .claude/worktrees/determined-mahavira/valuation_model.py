"""
CollectionCalc - Valuation Model
Deterministic, tuneable, explainable comic book valuation algorithm

Key principles:
1. Consistent results every time (no AI variance)
2. Explainable calculations (show your work)
3. Tuneable weights based on user feedback
4. Confidence scoring
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Configuration file for tuneable weights
WEIGHTS_FILE = "valuation_weights.json"

# Default weights (can be tuned over time based on feedback)
DEFAULT_WEIGHTS = {
    "version": "1.0.0",
    "last_updated": datetime.now().isoformat(),
    
    # Grade multipliers (base = NM at 1.0)
    "grade_multipliers": {
        "MT": 1.50,    # 10.0
        "GM": 1.40,    # 9.9
        "NM/MT": 1.30, # 9.8
        "NM+": 1.20,   # 9.6
        "NM": 1.00,    # 9.4 - BASE
        "NM-": 0.90,   # 9.2
        "VF/NM": 0.85, # 9.0
        "VF+": 0.80,   # 8.5
        "VF": 0.75,    # 8.0
        "VF-": 0.70,   # 7.5
        "FN/VF": 0.60, # 7.0
        "FN+": 0.55,   # 6.5
        "FN": 0.50,    # 6.0
        "FN-": 0.45,   # 5.5
        "VG/FN": 0.40, # 5.0
        "VG+": 0.35,   # 4.5
        "VG": 0.30,    # 4.0
        "VG-": 0.25,   # 3.5
        "GD/VG": 0.22, # 3.0
        "GD+": 0.18,   # 2.5
        "GD": 0.15,    # 2.0
        "GD-": 0.12,   # 1.8
        "FR/GD": 0.10, # 1.5
        "FR": 0.08,    # 1.0
        "PR": 0.05,    # 0.5
    },
    
    # CGC premium varies by base value (expensive books get lower premium)
    "cgc_premiums": {
        "under_25": 1.50,      # $0-25 base: 50% premium
        "25_to_100": 1.40,     # $25-100 base: 40% premium
        "100_to_500": 1.30,    # $100-500 base: 30% premium
        "500_to_1000": 1.25,   # $500-1000 base: 25% premium
        "over_1000": 1.20,     # $1000+ base: 20% premium
    },
    
    # Edition multipliers
    "edition_multipliers": {
        "direct": 1.00,
        "newsstand_pre_1990": 1.10,    # Common era
        "newsstand_1990_1995": 1.25,   # Getting scarcer
        "newsstand_post_1995": 1.50,   # Rare
        "newsstand_post_2000": 2.00,   # Very rare
        "variant": 1.25,               # Average variant (can vary wildly)
        "ratio_variant_1_25": 2.00,    # 1:25 variant
        "ratio_variant_1_50": 3.00,    # 1:50 variant
        "ratio_variant_1_100": 5.00,   # 1:100 variant
        "second_print": 0.50,
        "third_print": 0.35,
        "later_print": 0.25,
        "facsimile": 0.15,
    },
    
    # Signature premiums
    "signature_premiums": {
        "unknown_signer": 1.25,
        "artist": 1.50,
        "writer": 1.40,
        "cover_artist": 1.75,
        "creator": 2.00,        # Created the character
        "stan_lee": 2.50,       # Premium for Stan Lee
        "multiple_signatures": 1.20,  # Additional multiplier per extra sig
    },
    
    # Key issue premiums (on top of base value)
    "key_issue_types": {
        "first_appearance_major": 1.00,  # Already priced in
        "first_appearance_minor": 1.00,  # Already priced in
        "death_major_character": 1.10,
        "origin_story": 1.05,
        "classic_cover": 1.15,
        "first_issue": 1.05,
        "low_print_run": 1.20,
    },
    
    # Age-based adjustments (older comics trend higher)
    "age_adjustments": {
        "golden_age": 1.10,     # Pre-1956
        "silver_age": 1.05,     # 1956-1970
        "bronze_age": 1.00,     # 1970-1985
        "copper_age": 0.98,     # 1985-1991
        "modern_age": 0.95,     # 1991-present
    },
    
    # Publisher adjustments (market preference)
    "publisher_adjustments": {
        "Marvel Comics": 1.00,
        "DC Comics": 0.95,
        "Image Comics": 0.90,
        "Dark Horse Comics": 0.85,
        "IDW Publishing": 0.80,
        "Other": 0.75,
    },
    
    # Condition confidence penalties
    # If grade is estimated vs verified, reduce confidence
    "confidence_adjustments": {
        "grade_verified": 1.00,
        "grade_estimated": 0.85,
        "price_from_db": 1.00,
        "price_from_web": 0.80,
        "price_estimated": 0.60,
    },
}


@dataclass
class ValuationBreakdown:
    """Detailed breakdown of how value was calculated"""
    base_value: float
    base_value_source: str
    grade: str
    grade_multiplier: float
    grade_adjusted_value: float
    edition: str
    edition_multiplier: float
    edition_adjusted_value: float
    cgc_graded: bool
    cgc_multiplier: float
    cgc_adjusted_value: float
    signatures: List[str]
    signature_multiplier: float
    signature_adjusted_value: float
    age_era: str
    age_multiplier: float
    publisher: str
    publisher_multiplier: float
    key_issue_reason: Optional[str]
    key_issue_multiplier: float
    final_value: float
    confidence_score: float
    confidence_factors: Dict[str, float]
    calculation_steps: List[str]


class ValuationModel:
    """
    Deterministic comic book valuation model
    
    Usage:
        model = ValuationModel()
        result = model.calculate_value(
            base_nm_value=100.00,
            grade="VF",
            edition="newsstand",
            year=1988,
            publisher="Marvel Comics",
            cgc=False,
            signatures=[],
            key_issue_reason="First appearance of Venom"
        )
        print(result.final_value)
        print(result.calculation_steps)
    """
    
    def __init__(self, weights_file: str = WEIGHTS_FILE):
        self.weights_file = weights_file
        self.weights = self._load_weights()
    
    def _load_weights(self) -> Dict:
        """Load weights from file or use defaults"""
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new weights added)
                    merged = DEFAULT_WEIGHTS.copy()
                    for key, value in loaded.items():
                        if isinstance(value, dict) and key in merged:
                            merged[key].update(value)
                        else:
                            merged[key] = value
                    return merged
            except Exception as e:
                print(f"Warning: Could not load weights file: {e}")
                return DEFAULT_WEIGHTS.copy()
        return DEFAULT_WEIGHTS.copy()
    
    def save_weights(self):
        """Save current weights to file"""
        self.weights["last_updated"] = datetime.now().isoformat()
        with open(self.weights_file, 'w') as f:
            json.dump(self.weights, f, indent=2)
    
    def _get_grade_multiplier(self, grade: str) -> float:
        """Get multiplier for grade, with fuzzy matching"""
        grade = grade.upper().strip()
        
        # Direct match
        if grade in self.weights["grade_multipliers"]:
            return self.weights["grade_multipliers"][grade]
        
        # Try common variations
        variations = {
            "NEAR MINT": "NM",
            "VERY FINE": "VF",
            "FINE": "FN",
            "VERY GOOD": "VG",
            "GOOD": "GD",
            "FAIR": "FR",
            "POOR": "PR",
            "MINT": "MT",
            "9.8": "NM/MT",
            "9.6": "NM+",
            "9.4": "NM",
            "9.2": "NM-",
            "9.0": "VF/NM",
            "8.5": "VF+",
            "8.0": "VF",
            "7.5": "VF-",
            "7.0": "FN/VF",
            "6.5": "FN+",
            "6.0": "FN",
            "5.5": "FN-",
            "5.0": "VG/FN",
            "4.5": "VG+",
            "4.0": "VG",
            "3.5": "VG-",
            "3.0": "GD/VG",
            "2.5": "GD+",
            "2.0": "GD",
            "1.8": "GD-",
            "1.5": "FR/GD",
            "1.0": "FR",
            "0.5": "PR",
        }
        
        if grade in variations:
            return self.weights["grade_multipliers"].get(variations[grade], 1.0)
        
        # Default to NM if unknown
        return 1.0
    
    def _get_cgc_multiplier(self, base_value: float, is_cgc: bool) -> float:
        """Get CGC premium based on base value"""
        if not is_cgc:
            return 1.0
        
        premiums = self.weights["cgc_premiums"]
        
        if base_value < 25:
            return premiums["under_25"]
        elif base_value < 100:
            return premiums["25_to_100"]
        elif base_value < 500:
            return premiums["100_to_500"]
        elif base_value < 1000:
            return premiums["500_to_1000"]
        else:
            return premiums["over_1000"]
    
    def _get_edition_multiplier(self, edition: str, year: Optional[int]) -> float:
        """Get edition multiplier, with year context for newsstand"""
        edition = edition.lower().strip()
        
        # Handle newsstand with year context
        if "newsstand" in edition:
            if year is None:
                return self.weights["edition_multipliers"].get("newsstand_1990_1995", 1.25)
            elif year >= 2000:
                return self.weights["edition_multipliers"]["newsstand_post_2000"]
            elif year >= 1995:
                return self.weights["edition_multipliers"]["newsstand_post_1995"]
            elif year >= 1990:
                return self.weights["edition_multipliers"]["newsstand_1990_1995"]
            else:
                return self.weights["edition_multipliers"]["newsstand_pre_1990"]
        
        # Handle ratio variants
        if "1:100" in edition or "1/100" in edition:
            return self.weights["edition_multipliers"]["ratio_variant_1_100"]
        elif "1:50" in edition or "1/50" in edition:
            return self.weights["edition_multipliers"]["ratio_variant_1_50"]
        elif "1:25" in edition or "1/25" in edition:
            return self.weights["edition_multipliers"]["ratio_variant_1_25"]
        
        # Direct match
        return self.weights["edition_multipliers"].get(edition, 1.0)
    
    def _get_signature_multiplier(self, signatures: List[str]) -> float:
        """Calculate signature premium"""
        if not signatures:
            return 1.0
        
        premiums = self.weights["signature_premiums"]
        
        # Start with first signature
        first_sig = signatures[0].lower()
        
        if "stan lee" in first_sig:
            multiplier = premiums["stan_lee"]
        elif "creator" in first_sig:
            multiplier = premiums["creator"]
        elif "cover" in first_sig:
            multiplier = premiums["cover_artist"]
        elif "artist" in first_sig:
            multiplier = premiums["artist"]
        elif "writer" in first_sig:
            multiplier = premiums["writer"]
        else:
            multiplier = premiums["unknown_signer"]
        
        # Additional signatures add incrementally
        if len(signatures) > 1:
            additional_mult = premiums["multiple_signatures"] ** (len(signatures) - 1)
            multiplier *= additional_mult
        
        return multiplier
    
    def _get_age_era(self, year: Optional[int]) -> Tuple[str, float]:
        """Determine comic era and adjustment"""
        if year is None:
            return "modern_age", 1.0
        
        adjustments = self.weights["age_adjustments"]
        
        if year < 1956:
            return "golden_age", adjustments["golden_age"]
        elif year < 1970:
            return "silver_age", adjustments["silver_age"]
        elif year < 1985:
            return "bronze_age", adjustments["bronze_age"]
        elif year < 1991:
            return "copper_age", adjustments["copper_age"]
        else:
            return "modern_age", adjustments["modern_age"]
    
    def _get_publisher_multiplier(self, publisher: str) -> float:
        """Get publisher market adjustment"""
        adjustments = self.weights["publisher_adjustments"]
        
        # Normalize publisher name
        publisher_lower = publisher.lower() if publisher else ""
        
        if "marvel" in publisher_lower:
            return adjustments["Marvel Comics"]
        elif "dc" in publisher_lower:
            return adjustments["DC Comics"]
        elif "image" in publisher_lower:
            return adjustments["Image Comics"]
        elif "dark horse" in publisher_lower:
            return adjustments["Dark Horse Comics"]
        elif "idw" in publisher_lower:
            return adjustments["IDW Publishing"]
        else:
            return adjustments["Other"]
    
    def calculate_value(
        self,
        base_nm_value: float,
        grade: str = "NM",
        edition: str = "direct",
        year: Optional[int] = None,
        publisher: str = "Unknown",
        cgc: bool = False,
        signatures: Optional[List[str]] = None,
        key_issue_reason: Optional[str] = None,
        base_value_source: str = "database",
        grade_source: str = "estimated"
    ) -> ValuationBreakdown:
        """
        Calculate comic value with full breakdown
        
        Args:
            base_nm_value: Near Mint base value (from database or web search)
            grade: Comic grade (e.g., "VF", "NM-", "9.4")
            edition: Edition type (e.g., "direct", "newsstand", "variant")
            year: Publication year
            publisher: Publisher name
            cgc: Whether CGC graded
            signatures: List of signature descriptions
            key_issue_reason: Why this is a key issue (if applicable)
            base_value_source: Where base value came from ("database", "web_search", "estimated")
            grade_source: How grade was determined ("verified", "estimated")
        
        Returns:
            ValuationBreakdown with full calculation details
        """
        signatures = signatures or []
        steps = []
        confidence_factors = {}
        
        # Step 1: Start with base value
        current_value = base_nm_value
        steps.append(f"Base NM value: ${base_nm_value:.2f} (source: {base_value_source})")
        
        # Track confidence based on source
        if base_value_source == "database":
            confidence_factors["base_value"] = self.weights["confidence_adjustments"]["price_from_db"]
        elif base_value_source == "web_search":
            confidence_factors["base_value"] = self.weights["confidence_adjustments"]["price_from_web"]
        else:
            confidence_factors["base_value"] = self.weights["confidence_adjustments"]["price_estimated"]
        
        # Step 2: Apply grade multiplier
        grade_mult = self._get_grade_multiplier(grade)
        grade_adjusted = current_value * grade_mult
        steps.append(f"Grade adjustment ({grade}): ${current_value:.2f} × {grade_mult:.2f} = ${grade_adjusted:.2f}")
        current_value = grade_adjusted
        
        # Grade confidence
        if grade_source == "verified":
            confidence_factors["grade"] = self.weights["confidence_adjustments"]["grade_verified"]
        else:
            confidence_factors["grade"] = self.weights["confidence_adjustments"]["grade_estimated"]
        
        # Step 3: Apply edition multiplier
        edition_mult = self._get_edition_multiplier(edition, year)
        edition_adjusted = current_value * edition_mult
        if edition_mult != 1.0:
            steps.append(f"Edition adjustment ({edition}): ${current_value:.2f} × {edition_mult:.2f} = ${edition_adjusted:.2f}")
        current_value = edition_adjusted
        
        # Step 4: Apply CGC premium
        cgc_mult = self._get_cgc_multiplier(base_nm_value, cgc)
        cgc_adjusted = current_value * cgc_mult
        if cgc:
            steps.append(f"CGC premium: ${current_value:.2f} × {cgc_mult:.2f} = ${cgc_adjusted:.2f}")
            confidence_factors["grade"] = 1.0  # CGC = verified grade
        current_value = cgc_adjusted
        
        # Step 5: Apply signature premium
        sig_mult = self._get_signature_multiplier(signatures)
        sig_adjusted = current_value * sig_mult
        if signatures:
            sig_desc = ", ".join(signatures[:2])
            if len(signatures) > 2:
                sig_desc += f" +{len(signatures)-2} more"
            steps.append(f"Signature premium ({sig_desc}): ${current_value:.2f} × {sig_mult:.2f} = ${sig_adjusted:.2f}")
        current_value = sig_adjusted
        
        # Step 6: Apply age adjustment
        age_era, age_mult = self._get_age_era(year)
        age_adjusted = current_value * age_mult
        if age_mult != 1.0:
            steps.append(f"Era adjustment ({age_era}): ${current_value:.2f} × {age_mult:.2f} = ${age_adjusted:.2f}")
        current_value = age_adjusted
        
        # Step 7: Apply publisher adjustment
        pub_mult = self._get_publisher_multiplier(publisher)
        pub_adjusted = current_value * pub_mult
        if pub_mult != 1.0:
            steps.append(f"Publisher adjustment ({publisher}): ${current_value:.2f} × {pub_mult:.2f} = ${pub_adjusted:.2f}")
        current_value = pub_adjusted
        
        # Step 8: Key issue (usually already factored into base, but note it)
        key_mult = 1.0
        if key_issue_reason:
            steps.append(f"Key issue: {key_issue_reason} (premium already in base value)")
        
        # Final value
        final_value = round(current_value, 2)
        steps.append(f"Final estimated value: ${final_value:.2f}")
        
        # Calculate confidence score (product of all factors)
        confidence_score = 1.0
        for factor, value in confidence_factors.items():
            confidence_score *= value
        confidence_score = round(confidence_score * 100, 1)
        
        return ValuationBreakdown(
            base_value=base_nm_value,
            base_value_source=base_value_source,
            grade=grade,
            grade_multiplier=grade_mult,
            grade_adjusted_value=round(grade_adjusted, 2),
            edition=edition,
            edition_multiplier=edition_mult,
            edition_adjusted_value=round(edition_adjusted, 2),
            cgc_graded=cgc,
            cgc_multiplier=cgc_mult,
            cgc_adjusted_value=round(cgc_adjusted, 2),
            signatures=signatures,
            signature_multiplier=sig_mult,
            signature_adjusted_value=round(sig_adjusted, 2),
            age_era=age_era,
            age_multiplier=age_mult,
            publisher=publisher,
            publisher_multiplier=pub_mult,
            key_issue_reason=key_issue_reason,
            key_issue_multiplier=key_mult,
            final_value=final_value,
            confidence_score=confidence_score,
            confidence_factors=confidence_factors,
            calculation_steps=steps
        )
    
    def adjust_weight(self, category: str, key: str, new_value: float):
        """
        Adjust a specific weight based on feedback
        
        Usage:
            model.adjust_weight("grade_multipliers", "VF", 0.78)
            model.save_weights()
        """
        if category in self.weights and key in self.weights[category]:
            old_value = self.weights[category][key]
            self.weights[category][key] = new_value
            print(f"Adjusted {category}.{key}: {old_value} → {new_value}")
        else:
            print(f"Warning: {category}.{key} not found in weights")
    
    def get_weight(self, category: str, key: str) -> Optional[float]:
        """Get a specific weight value"""
        return self.weights.get(category, {}).get(key)
    
    def to_dict(self, breakdown: ValuationBreakdown) -> Dict:
        """Convert breakdown to dictionary for JSON serialization"""
        return asdict(breakdown)


# Quick test
def test_valuation():
    """Test the valuation model"""
    model = ValuationModel()
    
    print("=" * 60)
    print("VALUATION MODEL TEST")
    print("=" * 60)
    
    # Test 1: Captain America Annual #8
    print("\n📚 Captain America Annual #8")
    result = model.calculate_value(
        base_nm_value=50.00,
        grade="VF",
        edition="direct",
        year=1986,
        publisher="Marvel Comics",
        cgc=False,
        key_issue_reason="Classic Wolverine cover by Mike Zeck"
    )
    print(f"   Final Value: ${result.final_value:.2f}")
    print(f"   Confidence: {result.confidence_score}%")
    print("   Steps:")
    for step in result.calculation_steps:
        print(f"     • {step}")
    
    # Test 2: Same comic, CGC graded
    print("\n📚 Captain America Annual #8 (CGC 9.6)")
    result = model.calculate_value(
        base_nm_value=50.00,
        grade="9.6",
        edition="direct",
        year=1986,
        publisher="Marvel Comics",
        cgc=True,
        key_issue_reason="Classic Wolverine cover by Mike Zeck",
        grade_source="verified"
    )
    print(f"   Final Value: ${result.final_value:.2f}")
    print(f"   Confidence: {result.confidence_score}%")
    
    # Test 3: Newsstand edition
    print("\n📚 Amazing Spider-Man #300 (Newsstand)")
    result = model.calculate_value(
        base_nm_value=1200.00,
        grade="VF+",
        edition="newsstand",
        year=1988,
        publisher="Marvel Comics",
        cgc=False,
        key_issue_reason="First full appearance of Venom"
    )
    print(f"   Final Value: ${result.final_value:.2f}")
    print(f"   Confidence: {result.confidence_score}%")
    print("   Steps:")
    for step in result.calculation_steps:
        print(f"     • {step}")
    
    # Test 4: Signed copy
    print("\n📚 Spawn #1 (Signed by Todd McFarlane)")
    result = model.calculate_value(
        base_nm_value=125.00,
        grade="NM",
        edition="direct",
        year=1992,
        publisher="Image Comics",
        cgc=True,
        signatures=["creator - Todd McFarlane"],
        key_issue_reason="First appearance of Spawn"
    )
    print(f"   Final Value: ${result.final_value:.2f}")
    print(f"   Confidence: {result.confidence_score}%")
    print("   Steps:")
    for step in result.calculation_steps:
        print(f"     • {step}")


if __name__ == "__main__":
    test_valuation()
