const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
        BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
        TabStopType, TabStopPosition } = require("docx");

// Colors
const PURPLE = "4C1D95";
const PURPLE_LIGHT = "7C3AED";
const GOLD = "CA8A04";
const GREEN = "059669";
const RED = "DC2626";
const GRAY = "64748B";
const LIGHT_BG = "F8FAFC";
const PURPLE_BG = "F5F3FF";
const GREEN_BG = "ECFDF5";
const GOLD_BG = "FFFBEB";
const RED_BG = "FEF2F2";

const border = { style: BorderStyle.SINGLE, size: 1, color: "D1D5DB" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// Page dimensions
const PAGE_WIDTH = 12240;
const MARGIN = 1440;
const CONTENT_WIDTH = PAGE_WIDTH - (MARGIN * 2); // 9360

// Helper: section header with colored left border
function sectionHeader(text, color) {
  return new Paragraph({
    spacing: { before: 360, after: 200 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: color, space: 8 } },
    indent: { left: 120 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: "1E293B" })]
  });
}

// Helper: body text
function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after || 120 },
    children: [new TextRun({ text, size: 22, font: "Arial", color: opts.color || "334155", ...opts })]
  });
}

// Helper: status badge text
function statusText(label, color) {
  return new TextRun({ text: ` [${label}] `, size: 18, font: "Arial", color: color, bold: true });
}

// Helper: milestone row
function milestoneRow(date, milestone, status, statusColor, bg) {
  return new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 2200, type: WidthType.DXA },
        shading: { fill: bg || LIGHT_BG, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: date, size: 20, font: "Arial", bold: true, color: "1E293B" })] })]
      }),
      new TableCell({
        borders, width: { size: 5560, type: WidthType.DXA },
        shading: { fill: bg || LIGHT_BG, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: milestone, size: 20, font: "Arial", color: "334155" })] })]
      }),
      new TableCell({
        borders, width: { size: 1600, type: WidthType.DXA },
        shading: { fill: bg || LIGHT_BG, type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: status, size: 18, font: "Arial", bold: true, color: statusColor })
        ] })]
      }),
    ]
  });
}

// Helper: feature row (for the 3 tiers)
function featureRow(feature, tier, status, notes, bg) {
  const tierColor = tier === "Must-Have" ? RED : tier === "Nice-to-Have" ? GOLD : PURPLE_LIGHT;
  return new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 3400, type: WidthType.DXA },
        shading: { fill: bg || "FFFFFF", type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: feature, size: 20, font: "Arial", color: "1E293B" })] })]
      }),
      new TableCell({
        borders, width: { size: 1400, type: WidthType.DXA },
        shading: { fill: bg || "FFFFFF", type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: tier, size: 18, font: "Arial", bold: true, color: tierColor })
        ] })]
      }),
      new TableCell({
        borders, width: { size: 1400, type: WidthType.DXA },
        shading: { fill: bg || "FFFFFF", type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: status, size: 18, font: "Arial", color: status === "Done" ? GREEN : status === "Partial" ? GOLD : GRAY })
        ] })]
      }),
      new TableCell({
        borders, width: { size: 3160, type: WidthType.DXA },
        shading: { fill: bg || "FFFFFF", type: ShadingType.CLEAR },
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new Paragraph({ children: [new TextRun({ text: notes, size: 18, font: "Arial", color: GRAY, italics: true })] })]
      }),
    ]
  });
}

// Header row helper
function headerRow(cols, widths, bg) {
  return new TableRow({
    children: cols.map((text, i) => new TableCell({
      borders, width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: bg || PURPLE, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 100, right: 100 },
      children: [new Paragraph({ children: [
        new TextRun({ text, size: 20, font: "Arial", bold: true, color: "FFFFFF" })
      ] })]
    }))
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: PURPLE },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "1E293B" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "\u2013", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1440, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH, height: 15840 },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN }
      }
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
          children: [
            new TextRun({ text: "SLAB WORTHY\u2122", size: 18, font: "Arial", bold: true, color: PURPLE }),
            new TextRun({ text: "\t1.0 Launch Roadmap \u2014 SDCC 2026", size: 18, font: "Arial", color: GRAY }),
          ],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: PURPLE, space: 4 } }
        })
      ] })
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 2, color: "E2E8F0", space: 4 } },
          children: [
            new TextRun({ text: "Confidential \u2014 ", size: 16, font: "Arial", color: GRAY }),
            new TextRun({ text: "Page ", size: 16, font: "Arial", color: GRAY }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: GRAY }),
          ]
        })
      ] })
    },
    children: [

      // ============ TITLE PAGE ============
      new Paragraph({ spacing: { before: 2400 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [new TextRun({ text: "SLAB WORTHY\u2122", size: 56, font: "Arial", bold: true, color: PURPLE })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [new TextRun({ text: "1.0 Launch Roadmap", size: 40, font: "Arial", color: GOLD })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [new TextRun({ text: "San Diego Comic-Con \u2022 July 23, 2026", size: 26, font: "Arial", color: "475569" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 },
        children: [new TextRun({ text: "5 months to launch \u2022 Physical booth + Digital launch", size: 22, font: "Arial", color: GRAY })]
      }),

      // Key dates box
      new Table({
        width: { size: 5000, type: WidthType.DXA },
        columnWidths: [2500, 2500],
        alignment: AlignmentType.CENTER,
        rows: [
          new TableRow({ children: [
            new TableCell({ borders: noBorders, width: { size: 2500, type: WidthType.DXA },
              shading: { fill: PURPLE_BG, type: ShadingType.CLEAR },
              margins: { top: 100, bottom: 100, left: 160, right: 160 },
              children: [
                new Paragraph({ children: [new TextRun({ text: "Beta Launch", size: 20, font: "Arial", color: GRAY })] }),
                new Paragraph({ children: [new TextRun({ text: "April 2026", size: 24, font: "Arial", bold: true, color: PURPLE })] }),
              ]
            }),
            new TableCell({ borders: noBorders, width: { size: 2500, type: WidthType.DXA },
              shading: { fill: GOLD_BG, type: ShadingType.CLEAR },
              margins: { top: 100, bottom: 100, left: 160, right: 160 },
              children: [
                new Paragraph({ children: [new TextRun({ text: "SDCC Launch", size: 20, font: "Arial", color: GRAY })] }),
                new Paragraph({ children: [new TextRun({ text: "July 23, 2026", size: 24, font: "Arial", bold: true, color: GOLD })] }),
              ]
            }),
          ] }),
        ]
      }),

      new Paragraph({ spacing: { before: 800 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Prepared: February 23, 2026", size: 20, font: "Arial", color: GRAY })]
      }),

      // ============ PAGE 2: WHERE WE ARE ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Where We Are Today")]
      }),

      bodyText("Slab Worthy has a working product with real infrastructure. The core grading engine, Slab Guard anti-theft system, sales data pipeline, and billing are all functional. This roadmap is about going from working to launch-ready."),

      sectionHeader("What\u2019s Built & Working", GREEN),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [3000, 6360],
        rows: [
          headerRow(["System", "Status"], [3000, 6360]),
          ...[
            ["AI Grading Engine", "4-photo Claude Vision analysis, FMV lookup, slab-or-skip verdict"],
            ["Sales Database", "50,000+ sales from eBay & Whatnot, daily growth via extensions"],
            ["Slab Guard Registry", "Comic registration, fingerprinting, serial tracking"],
            ["Slab Guard Verify", "Public verification page with Turnstile, photo matching"],
            ["Sighting System", "Report to Owner flow, owner dashboard alerts, response actions"],
            ["Chrome Extension (eBay)", "Slab Guard monitor, eBay sales capture, bid filter"],
            ["Chrome Extension (Whatnot)", "Live auction valuator, Vision scanning, auto-scan, sale tracking"],
            ["Backend API", "Flask on Render (Docker), 14 route blueprints, JWT auth, CORS"],
            ["Frontend", "Cloudflare Pages, PWA, universal footer, 17 HTML pages"],
            ["Billing", "Stripe integration, 4 tiers (Free/Pro/Guard/Dealer), plan gating"],
            ["Contact Form", "Resend email, Turnstile spam protection, topic routing"],
            ["Vision API Proxy", "Server-side Anthropic calls, daily scan caps, usage logging"],
          ].map((r, i) => new TableRow({ children: [
            new TableCell({ borders, width: { size: 3000, type: WidthType.DXA },
              shading: { fill: i % 2 ? "FFFFFF" : GREEN_BG, type: ShadingType.CLEAR },
              margins: { top: 60, bottom: 60, left: 100, right: 100 },
              children: [new Paragraph({ children: [new TextRun({ text: r[0], size: 20, font: "Arial", bold: true, color: "1E293B" })] })]
            }),
            new TableCell({ borders, width: { size: 6360, type: WidthType.DXA },
              shading: { fill: i % 2 ? "FFFFFF" : GREEN_BG, type: ShadingType.CLEAR },
              margins: { top: 60, bottom: 60, left: 100, right: 100 },
              children: [new Paragraph({ children: [new TextRun({ text: r[1], size: 20, font: "Arial", color: "475569" })] })]
            }),
          ] }))
        ]
      }),

      // ============ PAGE 3: MUST-HAVES ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Must-Haves for 1.0")]
      }),

      bodyText("These are launch blockers. Without these, we don\u2019t launch."),

      sectionHeader("1. Grading Consistency", RED),
      bodyText("The core product. Right now the AI can return different grades for identical photos. For a paid product\u2014especially one people will try live at a booth\u2014this must be reliable and repeatable."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Implement grading calibration layer (normalize Claude\u2019s output against known graded comics)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Build a test suite of 50+ comics with known CGC grades for regression testing", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Target: same photos should produce grades within \u00B10.5 points, 95% of the time", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Add confidence scoring (\u201CHigh confidence: 9.2\u201D vs \u201CLow confidence: 7\u20138 range\u201D)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("2. Mobile Experience", RED),
      bodyText("At SDCC, everyone is on their phone. The grading flow must work flawlessly on mobile\u2014camera capture, photo upload, results display."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Full mobile audit of grading flow (camera \u2192 upload \u2192 results)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Direct camera capture (not file picker) for each of the 4 angles", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Responsive design pass on all public pages (index, pricing, about, FAQ, contact)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Touch-optimized UI (larger tap targets, swipe gestures for results)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("3. Onboarding & First-Time Experience", RED),
      bodyText("At the booth, someone picks up their phone and needs to go from zero to graded comic in under 2 minutes. No friction."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Streamlined sign-up (email + password, skip email verification for first grade)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Guided first-grade walkthrough (\u201CStep 1: Take a photo of the front cover\u201D)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Free tier gets 2 grades (enough to try at the booth, not enough to never pay)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "QR code \u2192 landing page \u2192 sign up \u2192 grade (single funnel, no dead ends)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("4. Photo Quality Gate", RED),
      bodyText("Users will submit blurry, dark, cropped photos. The AI can\u2019t grade what it can\u2019t see. We need client-side checks before the photo even leaves the phone."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Blur detection (reject photos below sharpness threshold)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Brightness check (too dark / too washed out)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Minimum resolution check", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Real-time feedback with fix instructions (\u201CToo dark \u2014 try near a window\u201D)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("5. Results & Grading Report", RED),
      bodyText("The grading result is the money moment. It needs to feel authoritative and be immediately useful."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Single-screen slab report: grade, confidence, FMV at that grade, slab-or-skip verdict", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Breakdown of defects found (spine ticks, color breaks, corner wear) with photo annotations", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Shareable result card (image users can save/post to social media)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Grade history in account page (re-grade comparison over time)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("6. Billing & Payment Polish", RED),
      bodyText("People need to be able to sign up, pay, and start using premium features without hitting any dead ends."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "End-to-end Stripe Checkout tested for all tiers", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Plan upgrade/downgrade flow", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Usage limits enforced and clearly communicated (\u201C3 of 10 grades used this month\u201D)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Cancellation flow (self-serve, no support ticket needed)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("7. Infrastructure & Reliability", RED),
      bodyText("A booth demo that crashes is worse than no demo. The backend needs to handle a surge of sign-ups."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Load testing: simulate 100 concurrent grading requests", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Render plan upgrade if needed (current plan may not handle burst traffic)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Error handling pass: no raw stack traces, friendly messages everywhere", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Monitoring & alerting (uptime checks, error rate alerts)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Database backups verified and restorable", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("8. Analytics & Tracking", RED),
      bodyText("We need to know what\u2019s happening from day one: who\u2019s signing up, who\u2019s grading, who\u2019s paying."),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Google Analytics or Plausible on all pages", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Conversion funnel tracking (visit \u2192 sign-up \u2192 first grade \u2192 paid)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Admin dashboard: daily sign-ups, grades, revenue", size: 22, font: "Arial", color: "334155" })] }),

      // ============ PAGE: NICE-TO-HAVES ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Nice-to-Haves")]
      }),

      bodyText("Would make the launch stronger but won\u2019t block it. Prioritize after must-haves are locked."),

      sectionHeader("Email System", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Welcome email after sign-up (already have Resend\u2014just need templates)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Grading result email (\u201CYour comic graded at 8.5 \u2014 here\u2019s your report\u201D)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Sighting alert emails (owner notified when their comic is spotted)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("SMS / Text Alerts (Twilio)", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Opt-in text alerts for Slab Guard sightings", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Premium feature for Guard/Dealer tiers", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("Landing Page Optimization", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Hero section with animated demo or video", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Social proof (testimonials from beta testers, grade accuracy stats)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "SEO optimization (meta tags, Open Graph, structured data)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "SDCC-specific landing page (/sdcc) with show-exclusive offer", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("Demo / Try-Before-You-Buy Mode", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Sample grading with a pre-loaded comic (no sign-up needed to see what results look like)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Great for booth traffic\u2014\u201Cscan this comic\u201D demo station", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("Collection Gallery Improvements", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Grid/list view toggle, cover thumbnails", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Total collection value estimate", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Export to CSV/PDF", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("Chrome Web Store Publishing", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Slab Guard Monitor extension published and installable", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Whatnot Valuator extension published (or invite-only for Dealer tier)", size: 22, font: "Arial", color: "334155" })] }),

      // ============ PAGE: STRETCH GOALS ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Stretch Goals")]
      }),

      bodyText("Only if everything else is done early. These are post-launch features that would be great to tease at SDCC."),

      sectionHeader("Native Mobile App", PURPLE_LIGHT),
      bodyText("PWA wrapper or React Native app. \u201CDownload Slab Worthy\u201D is a stronger pitch than \u201Cgo to our website.\u201D Could be App Store / Google Play listing even if it\u2019s just a thin wrapper."),

      sectionHeader("AI Comic Identification", PURPLE_LIGHT),
      bodyText("Point your camera at any comic and identify it\u2014title, issue, variant, key status\u2014without typing anything. The Whatnot extension already does this via Vision; bringing it to the main app would be huge."),

      sectionHeader("Dealer Dashboard & Bulk Grading", PURPLE_LIGHT),
      bodyText("Upload a stack of 20 comics, get grades for all of them. Dealer-tier feature. CSV export with grades, FMVs, and slab recommendations for the whole batch."),

      sectionHeader("API for Third Parties", PURPLE_LIGHT),
      bodyText("Public API for comic shops, auction houses, or other apps to integrate Slab Worthy grading. Paid per-call or bundled with Dealer tier."),

      sectionHeader("Grading Certificate PDF", PURPLE_LIGHT),
      bodyText("Downloadable PDF report with the Slab Worthy grade, defect analysis, FMV data, and a QR code linking to the verification page. Not a replacement for CGC/CBCS, but useful for raw sales."),

      // ============ PAGE: TIMELINE ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Timeline")]
      }),

      bodyText("Five phases from now to SDCC. Each phase has a clear milestone that must be hit before moving on."),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [2200, 5560, 1600],
        rows: [
          headerRow(["Dates", "Milestone", "Status"], [2200, 5560, 1600]),

          // Phase 1
          milestoneRow("", "PHASE 1: CORE HARDENING", "", PURPLE, PURPLE_BG),
          milestoneRow("Feb 24 \u2013 Mar 14", "Grading consistency: calibration layer + 50-comic test suite", "Not Started", RED),
          milestoneRow("Mar 1 \u2013 Mar 21", "Mobile experience: full grading flow on iOS Safari & Android Chrome", "Not Started", RED),
          milestoneRow("Mar 7 \u2013 Mar 28", "Photo quality gate: blur, brightness, resolution checks", "Not Started", RED),
          milestoneRow("Mar 14 \u2013 Mar 31", "Grading report redesign: single-screen, shareable, defect breakdown", "Not Started", RED),

          // Phase 2
          milestoneRow("", "PHASE 2: BETA LAUNCH", "", PURPLE, PURPLE_BG),
          milestoneRow("Apr 1 \u2013 Apr 7", "Onboarding flow: sign-up \u2192 first grade in under 2 minutes", "Not Started", RED),
          milestoneRow("Apr 1 \u2013 Apr 14", "Billing polish: all Stripe flows tested, usage limits visible", "Not Started", RED),
          milestoneRow("Apr 7 \u2013 Apr 14", "Error handling pass: friendly messages everywhere, no stack traces", "Not Started", RED),
          milestoneRow("Apr 14", "BETA LAUNCH \u2014 Invite first 20\u201350 testers", "Gate", GOLD),

          // Phase 3
          milestoneRow("", "PHASE 3: BETA ITERATION", "", PURPLE, PURPLE_BG),
          milestoneRow("Apr 14 \u2013 May 15", "Collect and triage beta feedback (weekly check-ins)", "Not Started", RED),
          milestoneRow("Apr 14 \u2013 May 15", "Fix top 10 issues from beta testers", "Not Started", RED),
          milestoneRow("Apr 21 \u2013 May 8", "Analytics setup: funnels, sign-ups, grade completion rate", "Not Started", RED),
          milestoneRow("May 1 \u2013 May 15", "Email system: welcome, grading results, sighting alerts (via Resend)", "Not Started", RED),

          // Phase 4
          milestoneRow("", "PHASE 4: LAUNCH PREP", "", PURPLE, PURPLE_BG),
          milestoneRow("May 15 \u2013 Jun 7", "Load testing: 100 concurrent users, identify bottlenecks", "Not Started", RED),
          milestoneRow("May 15 \u2013 Jun 14", "Landing page optimization: hero, social proof, SEO, /sdcc page", "Not Started", RED),
          milestoneRow("Jun 1 \u2013 Jun 21", "Nice-to-haves sprint (SMS alerts, demo mode, collection gallery)", "Not Started", RED),
          milestoneRow("Jun 14 \u2013 Jun 21", "Chrome Web Store submissions (2\u20133 week review period)", "Not Started", RED),

          // Phase 5
          milestoneRow("", "PHASE 5: FINAL QA & SDCC", "", PURPLE, PURPLE_BG),
          milestoneRow("Jun 21 \u2013 Jul 7", "Full regression test pass (updated Session 59 test plan)", "Not Started", RED),
          milestoneRow("Jul 1 \u2013 Jul 14", "SDCC booth prep: QR codes, demo devices, banner/signage", "Not Started", RED),
          milestoneRow("Jul 7 \u2013 Jul 18", "Code freeze \u2014 bug fixes only, no new features", "Not Started", RED),
          milestoneRow("Jul 18 \u2013 Jul 22", "Dress rehearsal: full demo run-through, backup plans", "Not Started", RED),
          milestoneRow("Jul 23", "LAUNCH AT SDCC", "D-Day", GOLD),
        ]
      }),

      // ============ PAGE: SDCC BOOTH ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("SDCC Booth Strategy")]
      }),

      bodyText("The booth is the product demo. Everything should drive people to scan a comic on their phone and see the result."),

      sectionHeader("Booth Setup", PURPLE_LIGHT),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Large QR code banner: \u201CScan Your Comic \u2014 Free AI Grade in 60 Seconds\u201D", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "2\u20133 demo tablets/phones for walk-up demos", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Sample comics to grade live (mix of grades: a 9.8, a 6.0, a 3.0)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Monitor showing real-time grading results (demo loop or live feed)", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("SDCC Promo Offer", GOLD),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "SDCC-exclusive: sign up at the con and get 5 free grades (normally 2)", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
        children: [new TextRun({ text: "Promo code: SDCC2026 \u2014 first month of Pro free", size: 22, font: "Arial", color: "334155" })] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 120 },
        children: [new TextRun({ text: "Business cards / stickers with QR code for people who don\u2019t sign up on the spot", size: 22, font: "Arial", color: "334155" })] }),

      sectionHeader("Demo Script (60-Second Pitch)", PURPLE_LIGHT),
      bodyText("\u201CHave a comic you\u2019re not sure about grading? Slab Worthy tells you the grade AND whether it\u2019s worth the money to send in. Takes 60 seconds. Scan this QR code, snap 4 photos, and you\u2019ll know if your book is slab-worthy.\u201D"),

      sectionHeader("Backup Plan", GRAY),
      bodyText("WiFi at SDCC can be unreliable. Bring a mobile hotspot. If the server goes down, have a pre-recorded demo video on the monitor showing the full grading flow. Keep the team\u2019s phones on cellular as backup demo devices."),

      // ============ PAGE: RISKS ============
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Risks & Mitigations")]
      }),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [3120, 3120, 3120],
        rows: [
          headerRow(["Risk", "Impact", "Mitigation"], [3120, 3120, 3120]),
          ...[
            ["Grading consistency not reliable enough by April", "Beta testers lose trust; can\u2019t demo at booth", "Start this first (Feb 24). If it\u2019s not there by March 31, delay beta to May and simplify scope"],
            ["Anthropic API costs spike with real users", "Margins disappear or we hit rate limits", "Monitor costs during beta. Set hard daily caps per user. Budget $500/mo for API during beta, $2K/mo at launch"],
            ["SDCC booth WiFi is terrible", "Live demos fail", "Mobile hotspot, offline demo video, pre-graded sample results as fallback"],
            ["Render free/starter tier can\u2019t handle traffic", "Site goes down during launch", "Load test in May. Upgrade Render plan by June. Set up health monitoring with auto-alerts"],
            ["Chrome Web Store review takes too long", "Extensions not published by SDCC", "Submit by June 14 (5+ weeks before). Have direct download (.crx) as backup"],
            ["Beta testers find major UX issues", "Scramble to fix before launch", "That\u2019s why we have beta. April\u2013May is specifically for this. Triage ruthlessly: fix blockers, defer cosmetics"],
            ["Scope creep eats the timeline", "Must-haves aren\u2019t done", "This roadmap is the scope. If it\u2019s not on the Must-Have list, it waits until after SDCC"],
          ].map((r, i) => new TableRow({ children: r.map((text, j) => new TableCell({
            borders, width: { size: 3120, type: WidthType.DXA },
            shading: { fill: i % 2 ? "FFFFFF" : LIGHT_BG, type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 100, right: 100 },
            children: [new Paragraph({ children: [
              new TextRun({ text, size: 20, font: "Arial", color: j === 0 ? "1E293B" : "475569", bold: j === 0 })
            ] })]
          })) }))
        ]
      }),

      // ============ FINAL: DECISION LOG ============
      new Paragraph({ spacing: { before: 600 } }),
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("Open Decisions")]
      }),

      bodyText("Items that need your input before we proceed:"),

      new Table({
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        columnWidths: [600, 5160, 1800, 1800],
        rows: [
          headerRow(["#", "Decision", "Options", "Decide By"], [600, 5160, 1800, 1800]),
          ...[
            ["1", "Free tier grade limit (currently undefined)", "2 / 3 / 5 grades", "Mar 7"],
            ["2", "Beta tester recruitment strategy", "Friends / Reddit / LCS / All", "Mar 21"],
            ["3", "SDCC booth size and budget", "Small table / Full booth", "Apr 1"],
            ["4", "Promo offer structure", "Free grades / Discount / Both", "May 15"],
            ["5", "Analytics provider", "Google Analytics / Plausible / PostHog", "Mar 14"],
            ["6", "Render plan tier for launch", "Starter ($7) / Standard ($25) / Pro ($85)", "Jun 1"],
          ].map((r, i) => new TableRow({ children: r.map((text, j) => new TableCell({
            borders, width: { size: [600, 5160, 1800, 1800][j], type: WidthType.DXA },
            shading: { fill: i % 2 ? "FFFFFF" : LIGHT_BG, type: ShadingType.CLEAR },
            margins: { top: 60, bottom: 60, left: 100, right: 100 },
            children: [new Paragraph({
              alignment: j === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
              children: [new TextRun({ text, size: 20, font: "Arial", color: j === 0 ? GRAY : "334155", bold: j === 0 })]
            })]
          })) }))
        ]
      }),

    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/sessions/tender-wonderful-bohr/mnt/SW/SDCC_Launch_Roadmap.docx", buffer);
  console.log("Done - SDCC_Launch_Roadmap.docx created");
});
