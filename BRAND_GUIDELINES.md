# CollectionCalc Brand Guidelines

## Brand Overview

**Name:** CollectionCalc  
**Tagline:** AI-Powered Collectible Valuations  
**Positioning:** The intelligent way to value your collection

---

## Color Palette

### Primary Colors

| Color | Hex | RGB | Usage |
|-------|-----|-----|-------|
| Near Black | `#0f0f1a` | 15, 15, 26 | Primary background |
| Dark | `#1a1a2e` | 26, 26, 46 | Card backgrounds, secondary surfaces |
| Indigo | `#4f46e5` | 79, 70, 229 | Primary accent, buttons, links |
| Purple | `#7c3aed` | 124, 58, 237 | Gradient endpoint, highlights |
| Cyan | `#06b6d4` | 6, 182, 212 | Success states, positive values |

### Gradient

**Primary Gradient:** `linear-gradient(135deg, #4f46e5, #7c3aed)`  
Use for: Logo, primary buttons, value displays, key UI elements

**Accent Gradient:** `linear-gradient(135deg, #06b6d4, #7c3aed)`  
Use for: Value numbers, special highlights

### Supporting Colors

| Color | Hex | Usage |
|-------|-----|-------|
| White | `#ffffff` | Primary text |
| Light Gray | `#94a3b8` | Secondary text, labels |
| Dark Gray | `#334155` | Borders, dividers |
| Success Green | `#10b981` | Positive trends, high confidence |
| Warning Amber | `#f59e0b` | Medium confidence, caution |
| Error Red | `#ef4444` | Low confidence, errors |

---

## Typography

### Font Stack

**Primary:** Inter, system-ui, -apple-system, sans-serif  
**Monospace (prices):** JetBrains Mono, Fira Code, monospace

### Scale

| Element | Size | Weight |
|---------|------|--------|
| H1 | 2.5rem (40px) | 700 |
| H2 | 2rem (32px) | 600 |
| H3 | 1.5rem (24px) | 600 |
| Body | 1rem (16px) | 400 |
| Small | 0.875rem (14px) | 400 |
| Caption | 0.75rem (12px) | 400 |
| Price Display | 2.5rem (40px) | 700 |

---

## Logo

### Wordmark

The CollectionCalc logo uses the primary gradient applied to text:

```css
.logo {
    font-weight: 700;
    font-size: 1.5rem;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
```

### Logo Variations

1. **Gradient on dark** (primary) - Use on dark backgrounds
2. **White** - Use on gradient backgrounds
3. **Dark** (#1a1a2e) - Use on light backgrounds (rare)

### Clear Space

Maintain minimum clear space equal to the height of the "C" around the logo.

### Minimum Size

- Digital: 100px width minimum
- Print: 1 inch width minimum

---

## Icon Library

**Recommended:** Lucide Icons (https://lucide.dev)  
- Open source, consistent style
- Works well with gradient accents
- Lightweight

**Key Icons Needed:**
- Search (magnifying glass)
- Calculator
- Trending up/down
- Star (favorites)
- Collection/grid
- Chart/analytics
- Camera (photo upload)
- Settings

**Icon Style:**
- Stroke width: 1.5px
- Size: 20px (default), 24px (large)
- Color: Inherit from text or use gradient

---

## UI Components

### Buttons

**Primary Button:**
```css
.btn-primary {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: #ffffff;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    border: none;
}
```

**Secondary Button:**
```css
.btn-secondary {
    background: transparent;
    color: #ffffff;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid #4f46e5;
}
```

### Cards

```css
.card {
    background: #1a1a2e;
    border: 1px solid #4f46e5;
    border-radius: 12px;
    padding: 24px;
}
```

### Inputs

```css
.input {
    background: #0f0f1a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 16px;
    color: #ffffff;
}

.input:focus {
    border-color: #4f46e5;
    outline: none;
}
```

---

## Confidence Indicators

| Level | Color | Badge Style |
|-------|-------|-------------|
| HIGH | `#10b981` | Solid green background |
| MEDIUM-HIGH | `#06b6d4` | Solid cyan background |
| MEDIUM | `#f59e0b` | Solid amber background |
| LOW | `#ef4444` | Solid red background |
| VERY LOW | `#6b7280` | Solid gray background |

---

## Voice & Tone

### Brand Voice

- **Confident** - We know valuations
- **Transparent** - Show our work, explain confidence
- **Helpful** - Guide users to better decisions
- **Modern** - AI-forward, not stuffy

### Writing Style

- Clear, concise language
- Avoid jargon unless necessary
- Use numbers and data
- Be honest about uncertainty

### Example Copy

✅ **Do:** "Based on 7 recent sales, we estimate $1,003 with high confidence."  
❌ **Don't:** "Our proprietary algorithm suggests a value of approximately $1,003."

✅ **Do:** "No recent sales found. Using historical data."  
❌ **Don't:** "Insufficient market data to calculate precise valuation metrics."

---

## Application Examples

### Dark Mode (Primary)

- Background: `#0f0f1a`
- Cards: `#1a1a2e`
- Text: `#ffffff` / `#94a3b8`
- Accents: Gradient

### Value Display

```
┌─────────────────────────────┐
│  Estimated Value            │  ← #94a3b8
│  $1,003.00                  │  ← Gradient text
│  ████ HIGH Confidence       │  ← #10b981 badge
└─────────────────────────────┘
```

---

## Future Considerations

### Logo Icon (TODO)
- Abstract "CC" mark
- Works at small sizes (favicon, app icon)
- Incorporates gradient

### Extended Palette (TODO)
- Category-specific colors (comics, cards, coins, etc.)
- Chart/visualization colors

### Motion (TODO)
- Loading animations
- Micro-interactions
- Transition timing

---

## Quick Reference

```css
:root {
    /* Backgrounds */
    --bg-primary: #0f0f1a;
    --bg-secondary: #1a1a2e;
    
    /* Brand */
    --brand-indigo: #4f46e5;
    --brand-purple: #7c3aed;
    --brand-cyan: #06b6d4;
    --brand-gradient: linear-gradient(135deg, #4f46e5, #7c3aed);
    
    /* Text */
    --text-primary: #ffffff;
    --text-secondary: #94a3b8;
    
    /* Status */
    --status-success: #10b981;
    --status-warning: #f59e0b;
    --status-error: #ef4444;
    
    /* Borders */
    --border-default: #334155;
    --border-accent: #4f46e5;
    
    /* Radius */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
}
```

---

*Last Updated: January 2026*  
*Version: 1.0*
