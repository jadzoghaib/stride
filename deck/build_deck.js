/**
 * Stride — investor pitch deck for the ESADE MSc Business Plan defence.
 *
 * 15 minutes, one speaker, shared over Zoom. The register is the product's own:
 * the "Timing Board" language from apps/web/DESIGN.md, a stadium results board
 * rather than a SaaS dashboard. Graphite ground, one signal-amber accent,
 * enormous condensed numerals against 11pt tracked caps. The deck looks like
 * the thing it is selling, which is the cheapest credibility available.
 *
 * Every figure comes from business-plan/model.py or the chart CSVs it writes;
 * nothing here is typed from memory.
 *
 * Joan Riera's evaluation form grades five things, and three of them are the
 * deck's job rather than the speaker's: investor-grade content, storyline
 * coherence, and "Look & Feel: Design, page number, layout". Hence the page
 * number on every slide, the single repeated motif, and a narrative that runs
 * problem, mechanism, product, proof, market, model, money, ask.
 *
 * The spine is two engines rather than one product. Fan monetisation and
 * sponsor analytics are shown as peers that feed each other: two problems
 * (slides 3 and 4), one missing layer that explains both (5), the two engines
 * (6), the loop that joins them (7), and then each one proved against the
 * running application in turn (8 and 9). Mechanics that used to sit in the
 * main line are backup slides, because they are answers rather than beats.
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

// ── palette, lifted from apps/web/src/index.css ─────────────────────────────
// The app stores RGB triplets so Tailwind can inject alpha; these are the same
// values as hex. Changing a colour here restyles the whole deck.
const C = {
  ground: "101216",      // page ground, graphite not black
  deep: "0A0C0F",        // the full-bleed board band
  panel: "171A20",       // card
  raised: "1F242C",      // hover / inset
  track: "262C35",       // meter track
  ink: "F2F4F7",         // headings
  ink2: "AEB6C2",        // body
  ink3: "828C9A",        // muted, captions, page numbers
  accent: "FFB020",      // signal amber, the scoreboard LED
  accentOn: "14100A",    // text sitting ON amber
  ok: "3FCF8E",
  warn: "FF8A3D",
  critical: "F2555A",
  cat1: "3B86E0",
  cat2: "1FBD85",
  cat3: "A884E8",
};

// Barlow Condensed ships here as the Bold weight and Barlow as Regular, so
// neither ever takes bold:true — PowerPoint would synthesise a second, uglier
// bold on top of the one the face already has.
const DISPLAY = "Barlow Condensed";
const BODY = "Barlow";

const W = 13.333, H = 7.5;
const M = 0.78;                       // side margin
const COL = W - M * 2;

const UI = path.resolve(__dirname, "../business-plan/attachments/ui");
// Sponsor-side captures taken for this deck. The product appendix only ever
// shot the athlete half, and the deck argues the other half is the same size.
const SHOTS = path.resolve(__dirname, "shots");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";          // 13.333 x 7.5, must precede addSlide
pres.theme = { headFontFace: DISPLAY, bodyFontFace: BODY };
pres.author = "Jad Zoghaib";
pres.title = "Stride: athlete monetisation built on analytics";
pres.subject = "ESADE MSc Business Plan, final presentation";

// ── layouts ─────────────────────────────────────────────────────────────────
const pageNum = {
  x: W - M - 0.8, y: H - 0.52, w: 0.8, h: 0.3, align: "right",
  fontFace: DISPLAY, fontSize: 12, color: C.ink3,
};

pres.defineSlideMaster({
  title: "COVER",
  background: { color: C.deep },
  objects: [],
});

// No wordmark in the footer: the source line lives bottom-left on most slides
// and the two collided on every one of them. Page number only, which is what
// the evaluation form actually asks for.
pres.defineSlideMaster({
  title: "BOARD",
  background: { color: C.ground },
  objects: [],
  slideNumber: pageNum,
});

pres.defineSlideMaster({
  title: "BOARD_DEEP",
  background: { color: C.deep },
  objects: [],
  slideNumber: pageNum,
});

// ── helpers ─────────────────────────────────────────────────────────────────
// Every options object is built fresh: pptxgenjs converts values to EMU in
// place on first use, so a shared literal silently corrupts the second caller.

/** 11pt tracked caps. The deck's smallest voice and its most repeated one. */
function eyebrow(s, text, opts = {}) {
  s.addText(text.toUpperCase(), {
    x: M, y: 0.52, w: COL, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12.5, color: C.accent, charSpacing: 3.2,
    ...opts,
  });
}

/** The slide's one message, set in the condensed display face. */
function title(s, text, opts = {}) {
  s.addText(text, {
    x: M, y: 0.86, w: COL, h: 0.95, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 36, color: C.ink, lineSpacing: 38,
    ...opts,
  });
}

function body(s, text, opts = {}) {
  s.addText(text, {
    margin: 0, isTextBox: true, valign: "top", fontFace: BODY, fontSize: 15,
    color: C.ink2, lineSpacing: 22, ...opts,
  });
}

/** A panel card. No edge stripes: a tint and a hairline is the whole device. */
function card(s, x, y, w, h, fill = C.panel) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.04,
    fill: { color: fill },
    line: { color: C.track, width: 0.75 },
  });
}

/** Scoreboard block: tracked cap label over an enormous numeral. */
function stat(s, x, y, w, label, value, note, colour = C.ink, size = 54, labelH = 0.24) {
  s.addText(label.toUpperCase(), {
    x, y, w, h: labelH, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 11.5, color: C.ink3, charSpacing: 2.2,
    lineSpacing: 14,
  });
  s.addText(value, {
    x, y: y + labelH, w, h: size / 58, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: size, color: colour, lineSpacing: size * 0.98,
  });
  if (note) {
    s.addText(note, {
      x, y: y + labelH + size / 58 + 0.03, w, h: 0.78, margin: 0, isTextBox: true, valign: "top",
      fontFace: BODY, fontSize: 12, color: C.ink3, lineSpacing: 15,
    });
  }
}

function source(s, text) {
  s.addText(text, {
    x: M, y: H - 0.52, w: COL - 1.2, h: 0.3, margin: 0, isTextBox: true, valign: "top",
    fontFace: BODY, fontSize: 9.5, color: C.ink3,
  });
}

/** The logo: a short amber dash, then the wordmark. Same as the app's sidebar. */
function wordmark(s, x, y, size = 30) {
  const dash = size / 140;                     // short, as in the product
  s.addShape(pres.ShapeType.rect, {
    x, y: y + size / 155, w: dash, h: Math.max(0.028, size / 1000),
    fill: { color: C.accent }, line: { width: 0 },
  });
  s.addText("STRIDE", {
    x: x + dash + size / 260, y, w: size / 7, h: size / 52, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: size, color: C.ink, charSpacing: size / 14,
  });
}

/** Chart frame. The fill has to be the slide's own ground, or the plot area
 *  reads as a lighter rectangle floating on the darker board. */
function chartFrame(ground) {
  return {
    catAxisLabelFontFace: BODY, catAxisLabelColor: C.ink3, catAxisLabelFontSize: 11,
    valAxisLabelFontFace: BODY, valAxisLabelColor: C.ink3, valAxisLabelFontSize: 11,
    dataLabelFontFace: DISPLAY, dataLabelFontSize: 11, dataLabelColor: C.ink,
    valGridLine: { color: C.track, size: 0.75 },
    catGridLine: { style: "none" },
    chartArea: { fill: { color: ground } }, plotArea: { fill: { color: ground } },
    border: { pt: 0, color: ground },
  };
}

// ════════════════════════════════════════════════════════════════════════════
// 1 — COVER
// ════════════════════════════════════════════════════════════════════════════
pres.addSection({ title: "Open" });
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Open" });
  wordmark(s, M, 1.55, 58);
  // Two imperative sentences, because the opener has about one second to land
  // and "athletes are creators with a second payer" needs a beat of thought.
  // The thesis sentence is not lost, it moves into the first thing I say.
  s.addText("Get the athlete paid.\nShow the brand what it bought.", {
    x: M, y: 2.72, w: 10.4, h: 1.5, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 46, color: C.ink, lineSpacing: 50,
  });
  // The segment, on slide one. Both sides of it, because who we sell to is the
  // part of this plan that is easiest to get wrong in the panel's head.
  s.addText(
    "For semi-professional athletes in niche sports, and the local businesses near their club. " +
    "Neither side is served today.", {
    x: M, y: 4.22, w: 8.6, h: 0.9, margin: 0, isTextBox: true, valign: "top",
    fontFace: BODY, fontSize: 15.5, color: C.ink2, lineSpacing: 23,
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 5.5, w: COL, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });
  s.addText([
    { text: "Jad Zoghaib", options: { color: C.ink, fontFace: DISPLAY, fontSize: 17 } },
    { text: "   MSc Business Plan, ESADE   ·   Tutor: Ignacio Gallardo Albajar   ·   October 2026",
      options: { color: C.ink3, fontFace: BODY, fontSize: 12.5 } },
  ], { x: M, y: 5.72, w: 9.2, h: 0.36, margin: 0, isTextBox: true });
  s.addText("LIVE DEMO", {
    x: W - M - 3.3, y: 5.68, w: 3.3, h: 0.2, margin: 0, isTextBox: true, valign: "top",
    align: "right", fontFace: DISPLAY, fontSize: 10.5, color: C.ink3, charSpacing: 2.6,
  });
  s.addText("stride-demo.onrender.com", {
    x: W - M - 3.3, y: 5.88, w: 3.3, h: 0.3, margin: 0, isTextBox: true, valign: "top",
    align: "right", fontFace: DISPLAY, fontSize: 16, color: C.accent,
  });
  s.addNotes(
    "Good morning. I am Jad Zoghaib and this is Stride.\n\n" +
    "Two sentences. Get the athlete paid, and show the brand what it bought. Those are the two halves " +
    "of the company, and most of my fifteen minutes is about why they are one company rather than two.\n\n" +
    "Be clear about who I mean on both sides. The athletes are semi-professional and amateur, in niche " +
    "sports, with a real following in a real place and no agent. A professional does not need me, they " +
    "already have one, and they would not use this. The brands are the businesses near that athlete's " +
    "club: the physiotherapy clinic, the gym, the car dealer.\n\n" +
    "And the thesis in one sentence: athletes are creators with a second payer. OnlyFans proved direct " +
    "fan monetisation beats ad share. Nobody built it for athletes, who unlike lifestyle creators also " +
    "have sponsors, clubs and a competitive record that makes their audience measurable.\n\n" +
    "Everything I show you is live at that URL, and I am happy to open it in the Q&A."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 2 — ORIGIN
// ════════════════════════════════════════════════════════════════════════════
// This was three cards of founder credentials, which is the least interesting
// slide any pitch can open with. One person carries the argument better: he is
// at the top of two sports and the market has no mechanism to pay him. The
// credentials still have to be here, because the deck later claims the product
// and the model are the author's own work, so they keep one line at the foot.
pres.addSection({ title: "Problem" });
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Problem" });
  eyebrow(s, "Why this");
  title(s, "A national champion, and the sport has no way to pay him");

  card(s, M, 2.1, 7.3, 3.2);
  s.addText("TWO SPORTS, AT THE TOP OF BOTH", {
    x: M + 0.32, y: 2.32, w: 6.6, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.6,
  });
  [["CrossFit", "Champion of Lebanon", 2.76],
   ["Rugby league", "Among the best in the country", 3.44],
  ].forEach(([sport, standing, y]) => {
    s.addText(sport.toUpperCase(), {
      x: M + 0.32, y, w: 2.6, h: 0.34, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 19, color: C.accent, charSpacing: 1.8,
    });
    s.addText(standing, {
      x: M + 3.0, y: y + 0.02, w: 3.9, h: 0.34, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 19, color: C.ink,
    });
    s.addShape(pres.ShapeType.rect, {
      x: M + 0.32, y: y + 0.5, w: 6.6, h: 0.014, fill: { color: C.track }, line: { width: 0 },
    });
  });
  body(s,
    "A friend I play rugby with, and one of the five athletes in the research behind this plan. " +
    "He is not the exception in that group. He is what a niche sport looks like at the very top of it.", {
    x: M + 0.32, y: 4.12, w: 6.6, h: 1.0, fontSize: 13.5, lineSpacing: 19,
  });

  card(s, 8.38, 2.1, COL - 7.6, 3.2, C.raised);
  s.addText("WHAT HE EARNS", {
    x: 8.68, y: 2.32, w: 3.6, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.6,
  });
  // Deliberately a word and not a number: slide 3 owns the enormous €0, and
  // two giant figures back to back would blunt the one that carries the data.
  s.addText("Nothing", {
    x: 8.68, y: 2.68, w: 3.6, h: 0.8, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 46, color: C.accent, lineSpacing: 48,
  });
  body(s,
    "Not a small amount, and not an inconsistent one. There is no mechanism at all by which a record " +
    "like his, or the audience that comes with it, turns into income.", {
    x: 8.68, y: 3.56, w: 3.6, h: 1.2, fontSize: 13, lineSpacing: 18,
  });
  body(s, "I started building because of him.", {
    x: 8.68, y: 4.78, w: 3.6, h: 0.4, fontSize: 13, color: C.ink, lineSpacing: 18,
  });

  card(s, M, 5.55, COL, 1.0, C.raised);
  s.addText("WHY I CAN SEE THIS AT ALL", {
    x: M + 0.3, y: 5.77, w: 3.3, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13, color: C.accent, charSpacing: 2.2,
  });
  body(s,
    "Capped by the Lebanese national rugby team, so these are teammates rather than survey respondents. " +
    "Four years of consulting built the model; the MSc and the build produced the product and its code.", {
    x: M + 3.9, y: 5.73, w: COL - 4.2, h: 0.72, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });
  source(s, "One of the five athletes in the primary research. Full method and limitations in section 3.1.5.");
  s.addNotes(
    "Why this, and it starts with one person.\n\n" +
    "A friend I play rugby with is the CrossFit champion of Lebanon, and one of the best rugby league " +
    "players in the country. He earns nothing from either one. Not a little. Nothing.\n\n" +
    "He is one of the five athletes in my research, and in that group he is not the exception. He is the " +
    "median. Someone at the very top of two sports, with a real audience, and no mechanism anywhere that " +
    "turns either of those things into income.\n\n" +
    "I started building this because of him.\n\n" +
    "And the reason I can see it at all is on the bottom line: these are teammates, not survey " +
    "respondents. I am capped for Lebanon myself, which is why the conversations were candid. The " +
    "consulting built the model, and the demo is my own code."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 3 — THE PROBLEM
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Problem" });
  eyebrow(s, "What five athletes told me");

  s.addText("€0", {
    x: M, y: 1.25, w: 5.2, h: 2.5, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 168, color: C.ink, lineSpacing: 160,
  });
  s.addText("CURRENT INCOME FROM THEIR AUDIENCE", {
    x: M, y: 3.62, w: 5.4, h: 0.3, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13, color: C.ink3, charSpacing: 2.6,
  });
  s.addText("Not low. Not inconsistent. Nothing", {
    x: M, y: 4.05, w: 5.6, h: 0.9, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 30, color: C.accent, lineSpacing: 34,
  });

  card(s, 6.9, 1.35, COL - 6.12, 3.95, C.panel);
  s.addText("“", {
    x: 7.2, y: 1.42, w: 1, h: 1, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 80, color: C.track,
  });
  body(s,
    "People are not going to spend time setting up social media and building followers purely " +
    "around their sport if nothing comes back.", {
    x: 7.3, y: 2.25, w: COL - 7.0, h: 1.5, fontSize: 19, color: C.ink, lineSpacing: 27,
  });
  s.addShape(pres.ShapeType.rect, {
    x: 7.3, y: 3.9, w: 1.1, h: 0.02, fill: { color: C.accent }, line: { width: 0 },
  });
  body(s,
    "Rugby league players competing in Spain and Lebanon, and top-ranked Lebanese CrossFit athletes. " +
    "The founder is capped by the Lebanese national rugby team, which is how this access exists.", {
    x: 7.3, y: 4.08, w: COL - 7.0, h: 1.1, fontSize: 12.5, color: C.ink3, lineSpacing: 17,
  });

  // The other three findings, so the lower third carries the rest of the
  // research rather than sitting empty under the headline number.
  const findings = [
    ["The inequity is felt", "Influencers producing far less demanding content earn more than competing athletes do"],
    ["Sponsorship arrives despite the sport", "The one athlete who has a sponsor did not get it as a rugby league player"],
    ["So they stop building an audience", "Which suppresses the very supply the market is measured on"],
  ];
  const fw = (COL - 0.6) / 3;
  findings.forEach(([head, text], i) => {
    const x = M + i * (fw + 0.3);
    s.addShape(pres.ShapeType.rect, {
      x, y: 5.62, w: fw, h: 0.014, fill: { color: C.track }, line: { width: 0 },
    });
    s.addText(head.toUpperCase(), {
      x, y: 5.76, w: fw, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12, color: C.ink, charSpacing: 1.8,
    });
    body(s, text, { x, y: 6.02, w: fw, h: 0.6, fontSize: 11.5, color: C.ink3, lineSpacing: 15 });
  });
  source(s, "Primary research, five semi-structured interviews, 2026. Convenience sample, reported as one.");
  s.addNotes(
    "He was one of five athletes in my own sports I asked the same question: what do you earn from " +
    "your audience.\n\n" +
    "The answer was not 'a little'. It was zero. Nothing, across all five.\n\n" +
    "And read the quote carefully, because it is the finding that matters most: they do not build an " +
    "audience, because there is no return on building one. That is not a complaint about pricing. " +
    "It is a market with no infrastructure in it."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 4 — THE BUYER'S HALF
// ════════════════════════════════════════════════════════════════════════════
// The deck used to carry one problem, the athlete's. The company has two
// customers with two different complaints, and the analytics engine answers
// the second one. Showing only the first made the engine look like a feature.
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Problem" });
  eyebrow(s, "The buyer's half");
  title(s, "A local brand spends on instinct, and never finds out");

  s.addText("“What did you get back,\nand how did you know?”", {
    x: M, y: 2.06, w: 6.4, h: 1.2, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 34, color: C.ink, lineSpacing: 38,
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 3.34, w: 1.1, h: 0.02, fill: { color: C.accent }, line: { width: 0 },
  });
  body(s,
    "The question the sponsor discovery programme is built around. It is the one the whole analytics " +
    "engine exists to answer, and today nobody below the professional tier owns an instrument that can.", {
    x: M, y: 3.52, w: 6.3, h: 0.9, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });

  card(s, 7.45, 2.06, W - M - 7.45, 1.9, C.panel);
  s.addText("WHO THE BUYER IS", {
    x: 7.73, y: 2.28, w: W - M - 8.01, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.6,
  });
  body(s,
    "Physiotherapy clinics, gyms, car dealers, restaurants and regional insurers within reach of an " +
    "anchor athlete's club. The segment the agencies will not serve, and the one this model is built on.", {
    x: 7.73, y: 2.62, w: W - M - 8.01, h: 1.2, fontSize: 13, color: C.ink2, lineSpacing: 18,
  });

  const cannot = [
    ["Choose", "Two athletes, and nothing to compare them on but follower count, which is the one number that can be bought."],
    ["Price", "No rate card and no benchmark anywhere in the segment. The fee is whatever was asked for."],
    ["Verify", "The campaign ends, and nothing is known that was not known before it started."],
  ];
  const cw = (COL - 0.6) / 3;
  cannot.forEach(([head, text], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 4.28, cw, 1.3);
    s.addText(head.toUpperCase(), {
      x: x + 0.26, y: 4.48, w: cw - 0.52, h: 0.28, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 16, color: C.accent, charSpacing: 2.2,
    });
    body(s, text, { x: x + 0.26, y: 4.82, w: cw - 0.52, h: 0.78, fontSize: 12.5, color: C.ink2, lineSpacing: 17 });
  });

  card(s, M, 5.76, COL, 0.88, C.raised);
  s.addText("THE ASSUMPTION I TEST FIRST", {
    x: M + 0.3, y: 5.96, w: 3.2, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13.5, color: C.accent, charSpacing: 2.2,
  });
  body(s,
    "Twenty sponsor conversations before the pre-seed gate, and the answer that kills it is written down " +
    "in advance: if brands say they already know what they get, the analytics engine is not a differentiator.", {
    x: M + 3.8, y: 5.92, w: COL - 4.1, h: 0.62, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });
  source(s, "Sponsor discovery programme, section 4.6: four buyer groups, seven questions, each one aimed at an assumption the model depends on.");
  s.addNotes(
    "Now the other side, and this is the half of the company I care most about.\n\n" +
    "The brand paying for this is not Nike. It is a physiotherapy clinic or a regional insurer near the " +
    "athlete's club. They have a budget. What they do not have is any instrument at all: they cannot " +
    "compare two athletes except on follower count, they have no benchmark to price against, and when " +
    "the campaign ends they know nothing they did not know before.\n\n" +
    "I want to be straight about status. I have interviewed athletes, not sponsors. This is the biggest " +
    "hole in my research, so it is the first thing I build and the first thing I test, and I have written " +
    "down in advance which answer would kill it. If brands tell me they already know what they get, " +
    "my differentiator is gone."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 5 — WHY IT HAPPENS
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Problem" });
  eyebrow(s, "The mechanism");
  title(s, "One missing layer explains both halves");

  const halves = [
    ["In a popular sport", "An agent introduces the athlete and vouches for the audience. Ten to twenty per cent, and the brand gets a number it can defend.", C.ink2],
    ["In a niche sport", "There is no agent. The athlete's alternative is not a worse deal, it is no deal. The brand's alternative is a guess.", C.accent],
  ];
  const hw = (COL - 0.3) / 2;
  halves.forEach(([head, text, colour], i) => {
    const x = M + i * (hw + 0.3);
    card(s, x, 2.1, hw, 1.62, i === 1 ? C.raised : C.panel);
    s.addText(head.toUpperCase(), {
      x: x + 0.28, y: 2.32, w: hw - 0.56, h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12.5, color: C.ink3, charSpacing: 2.6,
    });
    body(s, text, { x: x + 0.28, y: 2.62, w: hw - 0.56, h: 1.0, fontSize: 16, color: colour, lineSpacing: 23 });
  });

  s.addText("AND THAT ABSENCE FEEDS ITSELF", {
    x: M, y: 4.0, w: COL, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.8,
  });
  const loop = [
    "No route from audience to income",
    "So no reason to build an audience",
    "So the market measures smaller than it is",
  ];
  const lw = (COL - 1.3) / 3;
  loop.forEach((text, i) => {
    const x = M + i * (lw + 0.65);
    card(s, x, 4.34, lw, 0.92, C.panel);
    s.addText(String(i + 1).padStart(2, "0"), {
      x: x + 0.24, y: 4.5, w: 0.5, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 15, color: C.accent,
    });
    body(s, text, { x: x + 0.74, y: 4.5, w: lw - 1.0, h: 0.62, fontSize: 13, color: C.ink, lineSpacing: 17 });
    if (i < 2) {
      s.addText("›", {
        x: x + lw + 0.12, y: 4.56, w: 0.42, h: 0.5, margin: 0, isTextBox: true, valign: "top",
        align: "center", fontFace: DISPLAY, fontSize: 26, color: C.ink3,
      });
    }
  });
  body(s,
    "An agent introduces, and an agent vouches. Below the professional tier neither function exists: " +
    "no route to income on one side, no basis for a decision on the other. So the market is sized under " +
    "the incentives that suppress it, and the honest error direction is understatement.", {
    x: M, y: 5.42, w: COL, h: 0.84, fontSize: 14, color: C.ink2, lineSpacing: 19,
  });
  s.addNotes(
    "So why does this happen, on both sides at once? Because one layer is missing, and it used to do " +
    "two jobs.\n\n" +
    "An agent introduces the athlete to the brand, and an agent vouches for what the brand is getting. " +
    "In football that costs 10 to 20 per cent and it exists. In trail running or rugby league there is " +
    "no agent at all, so the athlete has no route to income and the brand has no basis for a decision. " +
    "One absence, two victims.\n\n" +
    "And it compounds: no route to income, so no reason to build an audience, so the market counts " +
    "smaller than it really is. Every number I am about to show you is therefore the conservative reading."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 6 — TWO ENGINES
// ════════════════════════════════════════════════════════════════════════════
// This slide used to read "a creator platform with a sponsorship feature",
// which subordinated the half of the company that does the hardest work. The
// two engines are peers, and the next slide is why they are in one company.
pres.addSection({ title: "Product" });
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Product" });
  eyebrow(s, "The product");
  title(s, "Two engines, and each one is the other's reason to exist");

  const engines = [
    ["Engine one", "Monetisation", "Athlete and fan", C.cat2,
     "The athlete's own page, with paid fan tiers they price themselves. They keep 85% and pay nothing " +
     "to be there. Self serve, with no sales touch per subscriber.",
     "15% of fan revenue", "48% of Y7"],
    ["Engine two", "Analytics", "Sponsor", C.cat1,
     "A campaign brief matched to athletes on measured audience evidence, every score decomposed into " +
     "the arithmetic behind it, and delivery measured against what was projected.",
     "10% of deal value, plus €99 to €999 a month", "52% of Y7"],
  ];
  const hw = (COL - 0.4) / 2;
  engines.forEach(([tag, head, who, colour, text, price, share], i) => {
    const x = M + i * (hw + 0.4);
    card(s, x, 2.1, hw, 3.0);
    s.addText(tag.toUpperCase(), {
      x: x + 0.32, y: 2.32, w: hw - 0.64, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.8,
    });
    s.addText(head, {
      x: x + 0.32, y: 2.6, w: hw - 0.64, h: 0.56, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 30, color: colour, lineSpacing: 32,
    });
    s.addText(who.toUpperCase(), {
      x: x + 0.32, y: 3.12, w: hw - 0.64, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11.5, color: C.ink3, charSpacing: 2.2,
    });
    body(s, text, { x: x + 0.32, y: 3.46, w: hw - 0.64, h: 0.95, fontSize: 13.5, lineSpacing: 19 });
    s.addShape(pres.ShapeType.rect, {
      x: x + 0.32, y: 4.5, w: hw - 0.64, h: 0.014, fill: { color: C.track }, line: { width: 0 },
    });
    s.addText([
      { text: price, options: { fontFace: DISPLAY, fontSize: 16, color: C.ink } },
      { text: `   ·   ${share}`, options: { fontFace: BODY, fontSize: 12, color: C.ink3 } },
    ], {
      x: x + 0.32, y: 4.64, w: hw - 0.64, h: 0.34, margin: 0, isTextBox: true, valign: "top",
    });
  });

  card(s, M, 5.35, COL, 0.9, C.raised);
  s.addText("THE ATHLETE PAYS NOTHING", {
    x: M + 0.3, y: 5.55, w: 3.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13.5, color: C.accent, charSpacing: 2.2,
  });
  body(s,
    "No monthly fee, ever, on either engine. The athlete earning €200 a month pays the same rate as the " +
    "one earning €5,000, which a subscription would not have done. They are the supply, and supply is the constraint.", {
    x: M + 3.6, y: 5.52, w: COL - 3.9, h: 0.6, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });
  source(s, "Stride financial model: Y7 net revenue of €3.01M, 48% from fans and 52% from the two sponsor streams.");
  s.addNotes(
    "So what is Stride. Two engines, and I want to be precise that they are peers rather than a product " +
    "and a feature.\n\n" +
    "Engine one is monetisation. The athlete gets their own page with paid fan tiers they price " +
    "themselves, they keep 85 per cent, and they pay nothing to be there. That is 48 per cent of year " +
    "seven revenue.\n\n" +
    "Engine two is analytics. A sponsor briefs a campaign, gets athletes matched on measured audience " +
    "evidence with every score decomposed, and then gets delivery measured against what was projected. " +
    "Ten per cent of the deal plus a subscription, and that is the other 52 per cent.\n\n" +
    "One deliberate choice: the flat take with no athlete fee. The athlete earning 200 euros a month " +
    "pays the same rate as the one earning 5,000. A subscription would have been regressive against " +
    "exactly the athlete we are built for."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 7 — THE FLYWHEEL
// ════════════════════════════════════════════════════════════════════════════
// The point of the deck. Two engines in one company is only interesting if
// each one produces the input the other cannot buy, so the loop is drawn
// rather than asserted.
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Product" });
  eyebrow(s, "Why they are one company");
  title(s, "Each engine produces the input the other cannot buy");

  const loop = [
    ["01", "Fans pay\nthe athlete", "Subscriptions give the athlete a reason to build an audience, and give us revenue from the first month.", C.cat2],
    ["02", "The athlete connects\ntheir platforms", "Monetising requires the connectors. Those same connectors are the measurement instrument.", C.cat2],
    ["03", "The sponsor\nsees evidence", "Measured reach, engagement and cost per thousand, per athlete, in place of a follower count.", C.cat1],
    ["04", "Deals raise\nathlete income", "Which brings the next athlete, and arrives with an audience that can now be measured.", C.accent],
  ];
  const cw = 2.6, gap = (COL - 4 * cw) / 3;
  loop.forEach(([n, head, text, colour], i) => {
    const x = M + i * (cw + gap);
    card(s, x, 2.2, cw, 2.2, C.panel);
    s.addText(n, {
      x: x + 0.24, y: 2.38, w: 0.8, h: 0.44, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 26, color: colour,
    });
    s.addText(head, {
      x: x + 0.24, y: 2.84, w: cw - 0.48, h: 0.62, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 16, color: C.ink, charSpacing: 1.2, lineSpacing: 19,
    });
    body(s, text, { x: x + 0.24, y: 3.5, w: cw - 0.48, h: 0.8, fontSize: 11.5, color: C.ink2, lineSpacing: 15 });
    if (i < 3) {
      s.addText("›", {
        x: x + cw + 0.02, y: 3.0, w: gap - 0.04, h: 0.5, margin: 0, isTextBox: true, valign: "top",
        align: "center", fontFace: DISPLAY, fontSize: 26, color: C.ink3,
      });
    }
  });

  // The chain reads left to right and then stops, so the thing that makes it a
  // flywheel rather than a funnel has to be drawn: a rule straight back across
  // the four, carrying the return.
  [M, M + 7.47].forEach((x) => {
    s.addShape(pres.ShapeType.rect, {
      x, y: 4.62, w: 4.3, h: 0.014, fill: { color: C.track }, line: { width: 0 },
    });
  });
  s.addText("AND FOUR RETURNS TO ONE", {
    x: M + 4.4, y: 4.51, w: 2.97, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    align: "center", fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.6,
  });

  card(s, M, 4.88, COL, 0.95, C.raised);
  s.addText("WHY NEITHER HALF STANDS ALONE", {
    x: M + 0.3, y: 5.1, w: 3.5, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13.5, color: C.accent, charSpacing: 2.2,
  });
  body(s,
    "A creator platform has no reason to measure an audience. A sponsorship data company has no " +
    "relationship with the athlete, so it cannot get the measurements. Both halves are required, and " +
    "that is the architecture rather than a roadmap.", {
    x: M + 4.2, y: 5.06, w: COL - 4.5, h: 0.66, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });

  body(s,
    "Fan revenue funds the years in which the data accrues. By the time the analytics are worth selling, " +
    "someone else has already paid to build them.", {
    x: M, y: 6.02, w: COL, h: 0.7, fontSize: 16, color: C.ink, lineSpacing: 22,
  });
  s.addNotes(
    "This is the slide I would most like you to remember.\n\n" +
    "Follow the loop. Fans pay the athlete, so the athlete has a reason to build an audience. To take " +
    "that money they connect their platforms, and those connectors are the same instrument that measures " +
    "the audience. That measurement is what the sponsor is shown instead of a follower count. The deal " +
    "raises the athlete's income, which brings the next athlete, who arrives with another audience to " +
    "measure.\n\n" +
    "Now the part that matters commercially. A creator platform has no reason to measure an audience, so " +
    "it never builds this. A sponsorship data company has no relationship with the athlete, so it cannot " +
    "get the data at all. You need both sides, and almost nobody has both.\n\n" +
    "And the financing consequence: fan revenue pays for the years in which the data is accumulating. " +
    "By the time the analytics are worth selling, somebody else has already funded building them."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 8 — IT IS BUILT
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Product" });
  eyebrow(s, "Not a mockup");
  s.addText("It is built, deployed,\nand you can open it now", {
    x: M, y: 0.86, w: 4.15, h: 1.6, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 33, color: C.ink, lineSpacing: 35,
  });
  const live = [
    "Admission gate with human review",
    "Versioned marketability scoring",
    "Explainable campaign matching",
    "Offers, deals, delivery measurement",
    "Audit log and a resilience drill",
    "Tests on two databases in CI",
  ];
  live.forEach((text, i) => {
    const y = 2.62 + i * 0.355;
    s.addShape(pres.ShapeType.rect, {
      x: M, y: y + 0.105, w: 0.14, h: 0.03, fill: { color: C.accent }, line: { width: 0 },
    });
    body(s, text, { x: M + 0.3, y, w: 3.8, h: 0.32, fontSize: 13, color: C.ink2 });
  });
  s.addText("stride-demo.onrender.com", {
    x: M, y: 4.95, w: 4.0, h: 0.34, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 18, color: C.accent,
  });
  body(s, "Fourteen demo accounts. Registration is open.", {
    x: M, y: 5.3, w: 4.0, h: 0.3, fontSize: 11.5, color: C.ink3,
  });
  s.addImage({
    path: path.join(UI, "02-athlete-dashboard.png"),
    x: 5.05, y: 0.75, w: 7.85, h: 5.45,
  });
  source(s, "Athlete dashboard, captured from the running application.");
  s.addNotes(
    "This is the part most business plans cannot show you.\n\n" +
    "It is not a mockup and not a prototype. It is deployed, and the URL is on the slide. " +
    "Fourteen demo accounts, registration open, you can sign in during the questions if you want to.\n\n" +
    "What you are looking at is an athlete's marketability score, 72, decomposed into the five " +
    "dimensions that produced it, with the connected platforms and the live offers underneath. " +
    "Every number on that screen traces back to a platform sync."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 9 — WHAT THE SPONSOR SEES
// ════════════════════════════════════════════════════════════════════════════
// Deliberately the same composition as the slide before it. The pair is the
// argument: one engine proved, then the other, on the same ground.
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Product" });
  eyebrow(s, "The second engine, running");
  s.addText("And this is what\nreplaces the instinct", {
    x: M, y: 0.86, w: 4.15, h: 1.6, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 33, color: C.ink, lineSpacing: 35,
  });
  const gets = [
    "Delivered reach and engagements, per athlete",
    "Cost per thousand reached, cost per engagement",
    "Delivered against what was projected when priced",
    "Share of reach landing in the targeted countries",
    "Every match score decomposed to its arithmetic",
    "A dash where nothing is measured. Never a zero",
  ];
  gets.forEach((text, i) => {
    const y = 2.46 + i * 0.4;
    s.addShape(pres.ShapeType.rect, {
      x: M, y: y + 0.105, w: 0.14, h: 0.03, fill: { color: C.accent }, line: { width: 0 },
    });
    body(s, text, { x: M + 0.3, y, w: 3.85, h: 0.34, fontSize: 12.5, color: C.ink2 });
  });
  body(s,
    "The arithmetic is shown because a brand that cannot audit the number will not spend against it a " +
    "second time. The red figure on that screen is a deal that underdelivered, and the product says so.", {
    x: M, y: 5.0, w: 3.95, h: 1.1, fontSize: 12.5, color: C.ink3, lineSpacing: 17,
  });
  s.addImage({
    path: path.join(SHOTS, "sponsor-campaign-analytics.png"),
    x: 5.05, y: 0.75, w: 7.85, h: 5.45,
  });
  source(s, "Campaign result view, captured from the running application. The demo's engagement figures are seeded, and the product labels them simulated on the screen itself.");
  s.addNotes(
    "And the same proof for the second engine.\n\n" +
    "This is the screen a sponsor shows their own management. Delivered reach, engagements, cost per " +
    "thousand reached, cost per engagement. Underneath, every athlete on the campaign with what they " +
    "actually delivered against what was projected when the offer was priced.\n\n" +
    "I want to point at one number. The red one, minus 85.8 per cent. That is a deal that " +
    "underdelivered, and the platform is telling the sponsor so. Every incentive in this industry runs " +
    "the other way. That is the number that makes the rest of the screen believable.\n\n" +
    "And look at the dashes. A deal with nothing attached yet reads as unmeasured, never as zero. " +
    "Zero would be a lie that flatters us.\n\n" +
    "One honesty note, and say it before anyone asks: the engagement figures in the demo are seeded, " +
    "and the product labels them simulated on the screen. The arithmetic is real, the data is a fixture."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 10 — THE EXPERT
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Product" });
  eyebrow(s, "Primary research");
  title(s, "The research changed the product, which is the point of doing it");

  card(s, M, 2.1, 7.2, 3.3, C.panel);
  s.addText("“", {
    x: M + 0.28, y: 2.16, w: 1, h: 1, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 76, color: C.track,
  });
  body(s,
    "Open registration to everyone, but build a filtering mechanism so that not anyone " +
    "can register as an athlete.", {
    x: M + 0.42, y: 2.92, w: 6.4, h: 1.2, fontSize: 20, color: C.ink, lineSpacing: 28,
  });
  s.addShape(pres.ShapeType.rect, {
    x: M + 0.42, y: 4.28, w: 1.1, h: 0.02, fill: { color: C.accent }, line: { width: 0 },
  });
  body(s,
    "Íñigo Cristóbal Losada, AI Lead at olympics.com, after eleven years at Olympic " +
    "Broadcasting Services, where he was Broadcaster Services Manager through Tokyo 2020 and Beijing 2022.", {
    x: M + 0.42, y: 4.46, w: 6.4, h: 0.8, fontSize: 12.5, color: C.ink3, lineSpacing: 17,
  });

  s.addText("WHAT IT CHANGED", {
    x: 8.5, y: 2.1, w: COL - 7.72, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.8,
  });
  body(s,
    "I had pitched it to him as a product for the IOC, open only to Olympic athletes. He rejected " +
    "that framing outright.", {
    x: 8.5, y: 2.46, w: COL - 7.72, h: 1.0, fontSize: 14, color: C.ink2, lineSpacing: 20,
  });
  body(s,
    "The admission gate exists because of that conversation. It is not a feature that was designed " +
    "and then justified.", {
    x: 8.5, y: 3.48, w: COL - 7.72, h: 1.0, fontSize: 14, color: C.ink, lineSpacing: 20,
  });
  body(s,
    "It also settled market entry. An IOC-only product inherits the IOC's athletes: elite, " +
    "represented, already monetised. The segment with the actual problem sits below that tier.", {
    x: 8.5, y: 4.5, w: COL - 7.72, h: 1.2, fontSize: 13, color: C.ink3, lineSpacing: 18,
  });
  s.addNotes(
    "I interviewed an expert with eleven years inside Olympic broadcasting.\n\n" +
    "I pitched him a product for the IOC, Olympic athletes only. He rejected it and told me to open " +
    "registration to everyone but filter who gets in.\n\n" +
    "The admission gate you just saw exists because of that sentence. I want to be precise about this: " +
    "the research changed the product, it did not decorate it. And it settled where we enter the " +
    "market, because the IOC's athletes are already represented and already monetised."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 11 — MARKET
// ════════════════════════════════════════════════════════════════════════════
pres.addSection({ title: "Market" });
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Market" });
  eyebrow(s, "How big, bottom up");
  title(s, "A segment nobody measures is a segment nobody has sized a product for");

  const funnel = [
    ["520M", "EU-27 and UK population", 1.0],
    ["8.3M", "Compete at club level or above", 0.62],
    ["138,000", "TAM: niche sports, 5,000+ followers", 0.40],
    ["55,000", "SAM: six launch markets", 0.26],
    ["6,300", "Our Y7 target, 11% of SAM", 0.13],
  ];
  funnel.forEach(([value, label, frac], i) => {
    const y = 2.18 + i * 0.66;
    const last = i === funnel.length - 1;
    s.addShape(pres.ShapeType.rect, {
      x: M, y, w: 5.9 * frac, h: 0.48,
      fill: { color: last ? C.accent : C.track }, line: { width: 0 },
    });
    s.addText(value, {
      x: M + 0.18, y: y + 0.03, w: 2.2, h: 0.4, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 21, color: last ? C.accentOn : C.ink,
    });
    body(s, label, { x: M + 6.15, y: y + 0.09, w: 2.75, h: 0.36, fontSize: 12.5, color: C.ink3 });
  });

  card(s, 9.95, 2.18, COL - 9.17, 3.3, C.panel);
  stat(s, 10.22, 2.44, 2.3, "European sport sponsorship", "€24.79bn",
       "Growing 5.9% a year", C.ink, 30, 0.46);
  s.addShape(pres.ShapeType.rect, {
    x: 10.22, y: 3.86, w: 2.0, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });
  stat(s, 10.22, 4.04, 2.3, "Spain, the fastest major market", "+14%",
       "Ahead of the UK and France", C.ok, 30, 0.46);

  body(s,
    "None of that top-down figure breaks below the professional tier. There is no published number for " +
    "sponsorship of individual athletes, so the plan does not divide it by anything. The bottom-up funnel " +
    "exists because the measured market stops exactly where ours starts.", {
    x: M, y: 5.62, w: COL, h: 0.72, fontSize: 13.5, color: C.ink2, lineSpacing: 19,
  });
  source(s, "European Sponsorship Association, 2025, via Statista. Funnel: Eurostat, Eurobarometer 525, and the plan's own Sport Opportunity Index.");
  s.addNotes(
    "Market, bottom up, because top down does not work here.\n\n" +
    "European sport sponsorship is 24.8 billion euros and Spain is the fastest growing major market at " +
    "plus 14 per cent. But none of that breaks below the professional tier, so I refuse to divide it by " +
    "a number and call it my market.\n\n" +
    "Instead: 138,000 niche-sport athletes in Europe with over 5,000 followers. 55,000 in the six markets " +
    "we would enter. We target 6,300 by year seven, which is 11 per cent of the serviceable market. " +
    "That is deliberately modest."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 12 — WHY NICHE FIRST
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Market" });
  eyebrow(s, "The wedge");
  title(s, "We start where there is no incumbent, because that is also where the economics are best");

  const cols = [
    ["Niche sports", "€16", "To acquire one athlete in Y1", "48%", "Of them monetise by Y7", C.accent, C.raised],
    ["Popular sports", "€40", "To acquire one athlete in Y1", "30%", "Of them monetise by Y7", C.ink2, C.panel],
  ];
  const cw = (COL - 0.3) / 2;
  cols.forEach(([head, cac, cacNote, mon, monNote, colour, fill], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 2.2, cw, 2.12, fill);
    s.addText(head.toUpperCase(), {
      x: x + 0.32, y: 2.42, w: cw - 0.64, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 17, color: colour, charSpacing: 2.0,
    });
    s.addText(cac, {
      x: x + 0.32, y: 2.84, w: 1.9, h: 0.85, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 52, color: C.ink, lineSpacing: 52,
    });
    body(s, cacNote, { x: x + 0.32, y: 3.74, w: 2.3, h: 0.5, fontSize: 11.5, color: C.ink3, lineSpacing: 15 });
    s.addText(mon, {
      x: x + 3.1, y: 2.84, w: 1.9, h: 0.85, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 52, color: C.ink, lineSpacing: 52,
    });
    body(s, monNote, { x: x + 3.1, y: 3.74, w: 2.3, h: 0.5, fontSize: 11.5, color: C.ink3, lineSpacing: 15 });
  });
  body(s,
    "Cheaper to acquire, and a larger share of them earn. A professional already has an agent and would " +
    "not use this, so nobody is fighting us for a trail runner with 25,000 followers and an inbox of " +
    "unanswered brand DMs. What we learn there generalises upward. Football does not generalise downward.", {
    x: M, y: 4.62, w: COL, h: 0.9, fontSize: 14.5, color: C.ink2, lineSpacing: 20,
  });

  // The second reason the wedge works, and the one that makes the two sides
  // fit each other rather than merely coexist: a niche athlete's audience is
  // concentrated in a place, and that is the thing a local brand cannot buy.
  card(s, M, 5.62, COL, 0.98, C.raised);
  s.addText("WHY THE TWO SIDES FIT", {
    x: M + 0.3, y: 5.84, w: 3.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13.5, color: C.accent, charSpacing: 2.4,
  });
  body(s,
    "A niche athlete's audience is concentrated where they train and compete. That concentration is worth " +
    "little to a national advertiser, and it is exactly what the clinic two streets from the club is trying " +
    "to buy and has no other way of buying. The same choice makes supply cheap and demand local.", {
    x: M + 3.5, y: 5.8, w: COL - 3.8, h: 0.68, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });
  source(s, "Stride financial model, segment assumptions. Acquisition cost rises over the plan as the mix shifts toward popular sports.");
  s.addNotes(
    "Why niche sports first, and this is the strategic heart of the plan. There are two reasons and the " +
    "second one is the better one.\n\n" +
    "The first is cost. A niche athlete costs 16 euros to acquire against 40 for a popular one, and by " +
    "year seven 48 per cent of them monetise against 30 per cent. Cheaper, and more of them earn, because " +
    "nobody is competing for them. A professional already has an agent and would not use this.\n\n" +
    "The second reason is the one I would argue for. A niche athlete's audience is concentrated in a " +
    "place, around the club and the circuit they compete on. To a national advertiser that is close to " +
    "worthless, which is why nobody bids for it. To the physiotherapy clinic two streets from the club " +
    "it is the only thing worth buying, and there is currently no way to buy it. So the same decision " +
    "that makes my supply cheap is what makes my demand side exist at all.\n\n" +
    "And what we learn here generalises upward into bigger sports. Starting in football and working down " +
    "does not work, because in football we would be the fifth option."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 13 — COMPETITION
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Market" });
  eyebrow(s, "Four companies tried this before us");
  // The table splits two and two along the same seam as our two engines, which
  // is the strongest available evidence that the pairing is the hard part.
  title(s, "Two built the marketplace, two built the data. Nobody built both");

  const rows = [
    ["Sponsoo", "Marketplace, same model", "11 yrs", "13", "€2.17M", "Total equity zero"],
    ["OpenSponsorship", "Marketplace, same model", "12 yrs", "23", "€7.6M", "Still private"],
    ["Hookit", "Sponsorship data", "18 yrs", "47", "€21.5M", "Sold"],
    ["SponsorUnited", "Sponsorship data, enterprise", "9 yrs", "355", "€38.8M", "A different business"],
  ];
  const headers = ["Company", "What it is", "Age", "People", "Raised", "Where it got to"];
  const colX = [M, M + 2.5, M + 5.4, M + 6.5, M + 7.7, M + 9.3];
  const colW = [2.4, 2.8, 1.0, 1.1, 1.5, 2.4];

  headers.forEach((h, i) => {
    s.addText(h.toUpperCase(), {
      x: colX[i], y: 2.16, w: colW[i], h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.2,
    });
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 2.46, w: COL, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });
  // One panel behind the first two rows rather than alternating stripes: the
  // title claims the set splits two and two, so the shading has to agree.
  s.addShape(pres.ShapeType.rect, {
    x: M - 0.12, y: 2.52, w: COL + 0.24, h: 1.04,
    fill: { color: C.panel }, line: { width: 0 },
  });
  rows.forEach((r, ri) => {
    const y = 2.58 + ri * 0.52;
    r.forEach((cell, ci) => {
      s.addText(cell, {
        x: colX[ci], y, w: colW[ci], h: 0.34, margin: 0, isTextBox: true, valign: "top",
        fontFace: ci === 0 ? DISPLAY : BODY, fontSize: ci === 0 ? 16 : 12.5,
        color: ci === 0 ? C.ink : (ci === 5 ? C.ink2 : C.ink3),
      });
    });
  });

  // The question this table always draws is about the one that got large, so
  // the answer belongs on the slide rather than only in the backup.
  body(s,
    "The one that got large sells data to agencies and rights holders, and never executes a deal. " +
    "355 people is what enterprise sales costs, and it is the reason nobody runs this motion down at a " +
    "€2,000 sponsorship.", {
    x: M, y: 4.80, w: COL, h: 0.56, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });

  card(s, M, 5.48, COL, 1.12, C.raised);
  s.addText("THE SECOND PAYER", {
    x: M + 0.3, y: 5.68, w: 2.6, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13.5, color: C.accent, charSpacing: 2.4,
  });
  body(s,
    "Fan subscriptions are 48% of our Y7 revenue, and none of these four has that stream at all. " +
    "If it works, the economics are not Sponsoo's. If it does not, they are, and this is Sponsoo with " +
    "eleven fewer years of relationships. The plan prices both cases.", {
    x: M + 3.2, y: 5.64, w: COL - 3.5, h: 0.84, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });
  source(s, "PitchBook company profiles, retrieved 1 October 2026, reported in euros.");
  s.addNotes(
    "I want to be straight with you about the comparables, because they are not flattering.\n\n" +
    "Four companies have built in this space. The two doing exactly what we do are small after more than " +
    "a decade. Sponsoo has thirteen people after eleven years and its total equity is zero, which means " +
    "accumulated losses have eaten everything shareholders put in. PitchBook models it at a 94 per cent " +
    "probability of no exit.\n\n" +
    "But look at how the four split, because it is the slide about the flywheel again. Sponsoo and " +
    "OpenSponsorship built the marketplace and no analytics worth the name. Hookit and SponsorUnited " +
    "built the data and never had the athlete relationship, so they sell enterprise dashboards to brands " +
    "that already spend. Two halves, four companies, nobody with both.\n\n" +
    "If you want the long answer on SponsorUnited I have a backup slide for it, but the short one is " +
    "this. They sell what the market did. We measure what one brand's money did, and we can only do that " +
    "because the projection is written onto the deal at the moment the offer is made. A company that was " +
    "not in the transaction never saw the promise. I am not beating them, to be clear. I am serving a " +
    "customer their cost structure will not let them near.\n\n" +
    "And none of the four has the fan. For us that is 48 per cent of year seven revenue: a second payer " +
    "none of them has, and it is the whole thesis. If it works we are not Sponsoo. If it does not, we are."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 14 — REVENUE MIX
// ════════════════════════════════════════════════════════════════════════════
pres.addSection({ title: "Model" });
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Model" });
  eyebrow(s, "Revenue model");
  title(s, "The business changes shape as it grows");

  const years = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7"];
  s.addChart(pres.ChartType.bar, [
    { name: "Fan subscriptions", labels: years, values: [0.0, 0.051, 0.184, 0.396, 0.684, 1.034, 1.436] },
    { name: "Sponsorship commission", labels: years, values: [0.002, 0.009, 0.046, 0.149, 0.346, 0.649, 0.982] },
    { name: "Sponsor SaaS", labels: years, values: [0.001, 0.008, 0.056, 0.159, 0.292, 0.441, 0.595] },
  ], {
    x: M, y: 2.08, w: 8.3, h: 3.5,
    barGrouping: "stacked", chartColors: [C.accent, C.cat1, C.cat3],
    showLegend: true, legendPos: "b", legendColor: C.ink3, legendFontFace: BODY, legendFontSize: 11,
    showValue: false, valAxisTitle: "", valAxisMaxVal: 3.2,
    valAxisLabelFormatCode: '"€"0.0"M"', barGapWidthPct: 55,
    valAxisMinVal: 0,
    ...chartFrame(C.ground),
  });

  const notes = [
    ["Y2", "75%", "of revenue is fan subscriptions, the year the thesis is tested"],
    ["Y7", "48%", "still fan, with sponsorship and SaaS compounding behind it"],
  ];
  notes.forEach(([yr, pct, text], i) => {
    const y = 2.3 + i * 1.6;
    card(s, 9.2, y, COL - 8.42, 1.35, C.panel);
    s.addText(yr, {
      x: 9.5, y: y + 0.18, w: 0.8, h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12, color: C.ink3,
    });
    s.addText(pct, {
      x: 9.5, y: y + 0.4, w: 1.6, h: 0.5, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 34, color: C.accent, lineSpacing: 34,
    });
    body(s, text, { x: 9.5, y: y + 0.88, w: COL - 9.0, h: 0.42, fontSize: 11.5, color: C.ink3, lineSpacing: 15 });
  });
  card(s, 9.2, 5.5, COL - 8.42, 0.55, C.raised);
  s.addText("€3.01M total at Y7", {
    x: 9.5, y: 5.62, w: 3.2, h: 0.32, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 17, color: C.ink,
  });
  source(s, "Stride financial model. Y1 to Y7, net revenue after the athlete's share.");
  s.addNotes(
    "The revenue model in one picture. Three streams.\n\n" +
    "Fan subscriptions in amber lead and fund the early years. Sponsorship commission and the sponsor " +
    "SaaS tier compound behind them.\n\n" +
    "The shape is the point: this starts as a subscription business and becomes a two-sided one. " +
    "Three million euros of net revenue at year seven."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 15 — YEAR ONE
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Model" });
  eyebrow(s, "Go to market");
  title(s, "Year one, concretely");

  const items = [
    ["250", "athletes", "recruited from 1,250 applications, in two or three niche Spanish sports"],
    ["20", "sponsor conversations", "which are the first sales as much as the research, closing about 15 deals"],
    ["1", "salary", "mine, plus a named athlete partner on 5% equity rather than cash"],
    ["€113k", "of cash", "two thirds of it available as a non-dilutive ENISA loan"],
  ];
  const cw = (COL - 0.75) / 4;
  items.forEach(([value, unit, note], i) => {
    const x = M + i * (cw + 0.25);
    card(s, x, 2.14, cw, 2.5);
    s.addText(value, {
      x: x + 0.28, y: 2.38, w: cw - 0.56, h: 0.95, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 54, color: i === 3 ? C.accent : C.ink, lineSpacing: 54,
    });
    // "SPONSOR CONVERSATIONS" wraps to two lines, so the label owns the room
    // for two and the note starts below the taller of the two cases.
    s.addText(unit.toUpperCase(), {
      x: x + 0.28, y: 3.34, w: cw - 0.56, h: 0.48, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 13, color: C.ink3, charSpacing: 2.2, lineSpacing: 15,
    });
    body(s, note, { x: x + 0.28, y: 3.88, w: cw - 0.56, h: 0.7, fontSize: 12, color: C.ink2, lineSpacing: 16 });
  });

  card(s, M, 4.84, COL, 1.2, C.panel);
  s.addText("THE SEQUENCE IS THE OPPOSITE OF THE OBVIOUS ONE", {
    x: M + 0.3, y: 5.04, w: 5.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13, color: C.accent, charSpacing: 2.2,
  });
  body(s,
    "Build the payment rail and sponsorship billing first, and the fan tier last. Commission is invoiced " +
    "against a signed deal: it needs no content moderation, no minors safeguarding and no media egress, " +
    "so it is the cheapest of the three to build and the only one that earns inside the first year.", {
    x: M + 0.3, y: 5.34, w: COL - 0.6, h: 0.68, fontSize: 13, color: C.ink2, lineSpacing: 17,
  });
  s.addNotes(
    "Year one, concretely, because a plan that cannot say what happens first is not a plan.\n\n" +
    "250 athletes from 1,250 applications in two or three niche Spanish sports. Twenty sponsor " +
    "conversations that are the first sales as much as they are research, closing about fifteen deals. " +
    "One salary, mine, plus an anchor athlete on equity rather than cash. 113,000 euros.\n\n" +
    "And note the build order, because it is counter-intuitive. We build the sponsorship rail first and " +
    "the fan product last, even though the fan product is the thesis. Commission earns inside year one. " +
    "The fan tier cannot, because it needs moderation and safeguarding built first."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 16 — OPERATIONS AND TEAM
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Model" });
  eyebrow(s, "Operations and people");
  title(s, "One human step in the chain, and a team sized to what I can actually run");

  card(s, M, 2.12, 5.6, 2.3, C.panel);
  s.addText("WHAT IS SUBCONTRACTED", {
    x: M + 0.3, y: 2.34, w: 5.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.4,
  });
  [["Stripe Connect", "Payments, KYC and payouts in 30+ countries"],
   ["AWS", "Compute, database and media processing"],
   ["Zero-egress CDN", "Media delivery, the cost that decides viability"],
  ].forEach(([what, why], i) => {
    const y = 2.68 + i * 0.52;
    s.addText(what, {
      x: M + 0.3, y, w: 2.0, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 15, color: C.ink,
    });
    body(s, why, { x: M + 2.4, y: y + 0.04, w: 3.1, h: 0.4, fontSize: 11.5, color: C.ink3, lineSpacing: 15 });
  });

  card(s, M + 5.9, 2.12, COL - 5.9, 2.3, C.panel);
  s.addText("HEADCOUNT", {
    x: M + 6.2, y: 2.34, w: 4.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.4,
  });
  const hc = [["Y1", 1, "1"], ["Y4", 2, "2"], ["Y7", 10, "10"], ["Y10", 16, "16"]];
  hc.forEach(([yr, n, lbl], i) => {
    const x = M + 6.2 + i * 1.35;
    s.addShape(pres.ShapeType.rect, {
      x, y: 3.9 - (n / 16) * 1.0, w: 0.62, h: (n / 16) * 1.0,
      fill: { color: i === 3 ? C.accent : C.track }, line: { width: 0 },
    });
    s.addText(lbl, {
      x: x - 0.12, y: 3.92, w: 0.86, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      align: "center", fontFace: DISPLAY, fontSize: 17, color: C.ink,
    });
    s.addText(yr, {
      x: x - 0.12, y: 4.18, w: 0.86, h: 0.22, margin: 0, isTextBox: true, valign: "top",
      align: "center", fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 1.6,
    });
  });

  body(s,
    "The only human step in the value chain is admission review, and it scales with applications rather " +
    "than with transactions. That is why sixteen people can run this. Sponsoo took eleven years to reach " +
    "thirteen, so the comparison is deliberate rather than optimistic.", {
    x: M, y: 4.58, w: COL, h: 0.7, fontSize: 14, color: C.ink2, lineSpacing: 19,
  });
  card(s, M, 5.28, COL, 0.94, C.raised);
  s.addText("THE ASSUMPTION I AM MOST EXPOSED ON", {
    x: M + 0.3, y: 5.5, w: 4.2, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 12.5, color: C.warn, charSpacing: 2.2,
  });
  body(s,
    "€301k of revenue per employee at Y7, against a private B2B SaaS median of €135k. If I am " +
    "wrong, the first thing to give is headcount, which means slower growth rather than a cash crisis.", {
    x: M + 4.7, y: 5.46, w: COL - 4.9, h: 0.66, fontSize: 12.5, color: C.ink2, lineSpacing: 17,
  });
  s.addNotes(
    "Operations and people, briefly, because the exam asks for both.\n\n" +
    "Payments, compute and media are all subcontracted. The only human step in the whole chain is " +
    "admission review, and it scales with applications, not with transactions. That is why sixteen " +
    "people can run this at five million of revenue.\n\n" +
    "And I will name the weak point before you do: 301,000 euros of revenue per employee is above the " +
    "top quartile for B2B SaaS. If that is wrong, headcount is what gives, and the consequence is " +
    "slower growth, not insolvency."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 17 — FINANCIALS
// ════════════════════════════════════════════════════════════════════════════
pres.addSection({ title: "Money" });
{
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Money" });
  eyebrow(s, "Financial plan");
  title(s, "Loss-making for four years, and the losses are small");

  const years = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7"];
  s.addChart([
    { type: pres.ChartType.bar,
      data: [{ name: "Net revenue", labels: years, values: [0.002, 0.068, 0.287, 0.704, 1.321, 2.124, 3.013] }],
      options: { chartColors: [C.track], barGapWidthPct: 55 } },
    { type: pres.ChartType.line,
      data: [{ name: "EBITDA", labels: years, values: [-0.111, -0.142, -0.072, 0.04, 0.173, 0.393, 0.743] }],
      options: { chartColors: [C.accent], lineSize: 3, lineSmooth: false,
                 lineDataSymbol: "circle", lineDataSymbolSize: 7 } },
  ], {
    x: M, y: 2.1, w: 8.3, h: 3.45,
    showLegend: true, legendPos: "b", legendColor: C.ink3, legendFontFace: BODY, legendFontSize: 11,
    valAxisLabelFormatCode: '"€"0.0"M"',
    ...chartFrame(C.ground),
  });

  const facts = [
    ["EBITDA positive", "Y4", C.ok],
    ["Cash positive", "Y5", C.ok],
    ["Y7 EBITDA margin", "24.7%", C.ink],
    ["Y10 net revenue", "€5.25M", C.ink],
  ];
  facts.forEach(([label, value, colour], i) => {
    const y = 2.18 + i * 0.86;
    s.addText(label.toUpperCase(), {
      x: 9.3, y, w: 3.4, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.2,
    });
    s.addText(value, {
      x: 9.3, y: y + 0.24, w: 3.4, h: 0.5, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 32, color: colour, lineSpacing: 32,
    });
  });
  body(s,
    "Gross margin climbs from 63% to 70%, not the SaaS 80%, because the payment rail is real.", {
    x: M, y: 5.68, w: COL, h: 0.5, fontSize: 13.5, color: C.ink3,
  });
  source(s, "Stride financial model, base case. Three scenarios are modelled; the pessimistic case still breaks even in Y5.");
  s.addNotes(
    "The financials. Revenue in grey, EBITDA the amber line.\n\n" +
    "We are loss-making for four years and the losses are small: the worst year is 142,000 euros. " +
    "EBITDA turns positive in year four, cash in year five, and year seven is three million of revenue " +
    "at a 24.7 per cent margin.\n\n" +
    "One honest note on margin. We climb to 70 per cent, not the 80 a SaaS business would claim, " +
    "because we move real money and Stripe takes its cut. I would rather show you 70 that survives " +
    "diligence."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 18 — THE ASK
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "BOARD_DEEP", sectionTitle: "Money" });
  eyebrow(s, "The ask");
  s.addText("€150k at €1.8M pre-money", {
    x: M, y: 0.86, w: 8.0, h: 0.8, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 44, color: C.ink,
  });
  body(s, "The first of two tranches, and the round that clears the worst point in the cash curve", {
    x: M, y: 1.68, w: 8.4, h: 0.4, fontSize: 15, color: C.ink2,
  });

  const years = ["Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7"];
  s.addChart(pres.ChartType.line, [
    { name: "Cumulative cash before raises", labels: years,
      values: [-0.113, -0.254, -0.296, -0.186, 0.08, 0.552, 1.25] },
  ], {
    x: M, y: 2.35, w: 7.3, h: 3.1,
    chartColors: [C.accent], lineSize: 3, lineSmooth: false,
    lineDataSymbol: "circle", lineDataSymbolSize: 7,
    showLegend: false, valAxisLabelFormatCode: '"€"0.0"M"',
    ...chartFrame(C.deep),
  });
  s.addText("TROUGH €296k IN Y3", {
    x: M + 1.55, y: 5.0, w: 2.6, h: 0.24, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 11.5, color: C.critical, charSpacing: 1.6,
  });

  const asks = [
    ["Total requirement", "€414k", "the €296k trough plus a 40% buffer"],
    ["Now", "€150k", "equity, which also unlocks €75k of non-dilutive ENISA debt"],
    ["In Y2", "€250k", "priced against three months of real subscription revenue, not a promise"],
  ];
  asks.forEach(([label, value, note], i) => {
    const y = 2.35 + i * 1.12;
    card(s, 8.6, y, COL - 7.82, 0.98, i === 1 ? C.raised : C.panel);
    s.addText(label.toUpperCase(), {
      x: 8.88, y: y + 0.14, w: 3.2, h: 0.22, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 10.5, color: C.ink3, charSpacing: 2.2,
    });
    s.addText(value, {
      x: 8.88, y: y + 0.34, w: 1.6, h: 0.42, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 27, color: i === 1 ? C.accent : C.ink, lineSpacing: 27,
    });
    body(s, note, { x: 10.42, y: y + 0.3, w: 2.0, h: 0.66, fontSize: 10.5, color: C.ink3, lineSpacing: 14 });
  });

  body(s,
    "Staging it costs about two points of equity and buys the right to price the second tranche on " +
    "evidence. A plan whose survival does not depend on the next round arriving on schedule is a " +
    "stronger one to raise against.", {
    x: M, y: 5.58, w: COL, h: 0.6, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });
  s.addNotes(
    "The ask. 150,000 euros at 1.8 million pre-money, and it is the first of two.\n\n" +
    "Look at the curve. The worst point is 296,000 euros in year three. Total requirement with a " +
    "40 per cent buffer is 414,000. But I do not need it now.\n\n" +
    "150 now, which also unlocks a 75,000 ENISA loan at no equity cost. Then 250 in year two, priced " +
    "against three months of real subscription revenue instead of against the same promise I am making " +
    "today. That staging costs me about two points of equity and it is worth it.\n\n" +
    "The important property: the pre-seed clears the trough on its own. Every round after it is a " +
    "growth option, not a rescue."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// 19 — CLOSE
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Money" });
  s.addText("ONE ASSUMPTION CARRIES THIS PLAN", {
    x: M, y: 1.35, w: COL, h: 0.3, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 13, color: C.accent, charSpacing: 3.2,
  });
  s.addText("Will fans of a semi-professional\nathlete actually pay?", {
    x: M, y: 1.82, w: 9.6, h: 1.8, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 44, color: C.ink, lineSpacing: 48,
  });
  body(s,
    "No interview answers it and no amount of further market sizing can. Only three months of real " +
    "subscription revenue from one anchor athlete settles it, and that is exactly what the pre-seed buys.", {
    x: M, y: 3.72, w: 9.2, h: 0.8, fontSize: 15.5, color: C.ink2, lineSpacing: 22,
  });

  const closes = [
    ["Tested for", "€80k and one year", "rather than €2.6M and four"],
    ["If it fails", "A smaller marketplace", "viable, but a different company"],
    ["Everything else", "Already done", "built, deployed and demonstrable"],
  ];
  const cw = (COL - 0.6) / 3;
  closes.forEach(([label, value, note], i) => {
    const x = M + i * (cw + 0.3);
    s.addShape(pres.ShapeType.rect, {
      x, y: 4.72, w: cw, h: 0.014, fill: { color: C.track }, line: { width: 0 },
    });
    s.addText(label.toUpperCase(), {
      x, y: 4.86, w: cw, h: 0.22, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 10.5, color: C.ink3, charSpacing: 2.2,
    });
    s.addText(value, {
      x, y: 5.08, w: cw, h: 0.38, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 21, color: i === 2 ? C.accent : C.ink,
    });
    body(s, note, { x, y: 5.48, w: cw, h: 0.4, fontSize: 11.5, color: C.ink3 });
  });

  wordmark(s, M, 6.25, 24);
  s.addText("stride-demo.onrender.com", {
    x: W - M - 4.0, y: 6.3, w: 4.0, h: 0.34, margin: 0, isTextBox: true, valign: "top",
    align: "right", fontFace: DISPLAY, fontSize: 16, color: C.accent,
  });
  s.addNotes(
    "I will finish where the plan is weakest, because you are going to ask anyway.\n\n" +
    "One assumption carries this: will fans of a semi-professional athlete actually pay? " +
    "No interview I did answers that. No market sizing answers it. Only real subscription revenue does.\n\n" +
    "So the plan is arranged so that question costs 80,000 euros and one year to answer, instead of " +
    "2.6 million and four. If the answer is no, what is left is a smaller sponsorship marketplace: " +
    "viable, but a less interesting company, and I would tell you that rather than find out quietly.\n\n" +
    "Everything else is already built. Thank you, and I am happy to open the demo."
  );
}

// ════════════════════════════════════════════════════════════════════════════
// BACKUP — not presented, carried for Q&A
// ════════════════════════════════════════════════════════════════════════════
pres.addSection({ title: "Backup" });
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Backup" });
  s.addText("BACKUP", {
    x: M, y: 3.1, w: COL, h: 0.4, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 15, color: C.accent, charSpacing: 3.4,
  });
  s.addText("Held for questions", {
    x: M, y: 3.52, w: COL, h: 0.8, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 40, color: C.ink,
  });
  body(s, "The four steps, the matching arithmetic, how we differ from the data companies, pricing, scenarios, risk, valuation and the admission gate.", {
    x: M, y: 4.35, w: 10.4, h: 0.7, fontSize: 14, color: C.ink3,
  });
}

/** Backup slides share one frame: title, a lead line, then free content. */
function backup(eyebrowText, titleText, lead) {
  const s = pres.addSlide({ masterName: "BOARD", sectionTitle: "Backup" });
  eyebrow(s, eyebrowText);
  title(s, titleText, { fontSize: 32, h: 0.75 });
  if (lead) body(s, lead, { x: M, y: 1.68, w: COL, h: 0.45, fontSize: 14, color: C.ink2 });
  return s;
}

// B1 — how it works. Moved out of the main line: the mechanics are a
//      question-and-answer subject rather than a story beat.
{
  const s = backup("Backup, mechanics", "Four steps, and a rule that holds all four together",
    "How an athlete gets in, gets scored, gets matched and gets paid.");

  const steps = [
    ["01", "Apply", "The athlete connects their platforms and applies. Proof is checked automatically, then a person decides. A club can nominate a whole roster as a second route."],
    // Two different scores, and conflating them is the easiest mistake to make
    // here: marketability is the athlete's own, the mean of five dimensions.
    // The eight weighted components are the match, which needs a campaign.
    ["02", "Score", "Marketability is the mean of five computed dimensions, each traceable to the posts behind it, and every score version is kept."],
    ["03", "Match", "A sponsor briefs a campaign, and the match is scored on eight weighted components, each one decomposed: audience fit 72 × 32% = 23.1."],
    ["04", "Deal", "Offer, acceptance, delivery measured against what was projected. An unmeasured campaign reads as unmeasured, never as zero."],
  ];
  const cw = (COL - 0.75) / 4;
  steps.forEach(([n, head, text], i) => {
    const x = M + i * (cw + 0.25);
    card(s, x, 2.2, cw, 2.72);
    s.addText(n, {
      x: x + 0.26, y: 2.4, w: cw - 0.52, h: 0.52, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 34, color: C.accent,
    });
    s.addText(head.toUpperCase(), {
      x: x + 0.26, y: 2.92, w: cw - 0.52, h: 0.28, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 16, color: C.ink, charSpacing: 2.0,
    });
    body(s, text, { x: x + 0.26, y: 3.26, w: cw - 0.52, h: 1.5, fontSize: 12.5, lineSpacing: 17 });
  });
  card(s, M, 5.16, COL, 0.92, C.raised);
  s.addText("NOTHING SELF-VERIFIES", {
    x: M + 0.3, y: 5.36, w: 3.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 14, color: C.accent, charSpacing: 2.4,
  });
  body(s,
    "A club scoring above the verification bar still waits for a human. A rejected proof cannot be " +
    "cleared by re-submitting the form. That is what a sponsor is actually buying.", {
    x: M + 3.5, y: 5.34, w: COL - 3.8, h: 0.6, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });
  s.addNotes(
    "Four steps. Apply, score, match, deal.\n\n" +
    "I will not go through the arithmetic now, it is in appendix I and I am happy to take it in questions. " +
    "The one thing worth your attention is the rule at the bottom.\n\n" +
    "Nothing self-verifies. Every other platform in this space lets supply assert its own numbers. " +
    "Ours cannot. That is precisely what the sponsor is paying for, and it is why the admission gate " +
    "is the product rather than a feature of it."
  );
}

// B2 — how a match is explained. The question the matching claim always draws,
//      answered with the screen rather than a description of the screen.
{
  const s = backup("Backup, the matching engine", "A ranked athlete, opened on the arithmetic that ranked them",
    "Eight weighted components. Bar length is the contribution to the total, not the component alone.");
  // Cropped to the opened row: at full height the screen does not fit under a
  // title, and everything above the row is chrome the question is not about.
  s.addImage({
    path: path.join(SHOTS, "sponsor-match-composition.png"),
    x: M, y: 2.3, w: COL, h: 3.555,
  });
  const points = [
    ["The weights are hand set", "A transparent weighted sum. Learned weights come once there are outcomes, and must beat this."],
    ["Coverage travels with the score", "Three of three platforms, or one of three. A thin score is marked thin, not quietly averaged."],
    ["It reads in plain language too", "Because the person approving the spend is rarely the person running the campaign."],
  ];
  const pw = (COL - 0.6) / 3;
  points.forEach(([head, text], i) => {
    const x = M + i * (pw + 0.3);
    s.addText(head.toUpperCase(), {
      x, y: 6.0, w: pw, h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12, color: C.accent, charSpacing: 2.0,
    });
    body(s, text, { x, y: 6.26, w: pw, h: 0.52, fontSize: 11.5, color: C.ink2, lineSpacing: 15 });
  });
  source(s, "Ranked matches for a live campaign, captured from the running application.");
}

// B3 — the differentiation question, which is always asked about the one
//      comparable that got big. Slide 13 says nobody built both halves; this
//      says what that actually costs them, in the sponsor's own three verbs.
{
  const s = backup("Backup, the comparable that got large",
    "They sell what the market did. We measure what your money did",
    "Slide 13 split the set two and two. This is what the split means to a brand with €2,000 to spend.");

  const cols = [
    ["Sponsoo,\nOpenSponsorship", "The marketplaces", C.ink3],
    ["Hookit,\nSponsorUnited", "The data companies", C.ink3],
    ["Stride", "Both halves, one loop", C.accent],
  ];
  const rows = [
    ["Choose",
     "Browse a roster. Follower counts, self reported",
     "Market intelligence: who sponsors whom, at scale",
     "Ranked against your brief, every score decomposed"],
    ["Price",
     "You negotiate. No benchmark",
     "A media value estimate for a property",
     "A reach projection attached to the offer itself"],
    ["Verify",
     "Screenshots from the athlete",
     "What the market did, from public posts",
     "Delivered against that projection, per athlete"],
    ["The data",
     "The athlete's own claim",
     "Scraped, public, third party",
     "The connector the athlete linked to get paid"],
    ["The buyer",
     "Brands of any size, thin support",
     "Rights holders, agencies, enterprise seats",
     "The clinic, the gym, the dealer"],
  ];
  const labW = 1.8, cw = 3.10, gapC = 0.28;
  const colX = [0, 1, 2].map((i) => M + 1.85 + i * (cw + gapC));

  // A panel behind our column only. The claim is that one of the three does
  // all five rows, so the shading marks the column rather than the rows.
  card(s, colX[2] - 0.18, 2.14, cw + 0.36, 3.56);

  cols.forEach(([head, sub, colour], i) => {
    s.addText(head, {
      x: colX[i], y: 2.26, w: cw, h: 0.52, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 16, color: colour === C.accent ? C.ink : C.ink2,
      charSpacing: 1.2, lineSpacing: 18,
    });
    s.addText(sub.toUpperCase(), {
      x: colX[i], y: 2.8, w: cw, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 10.5, color: colour, charSpacing: 2.0,
    });
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 3.14, w: COL, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });

  rows.forEach(([label, ...cells], ri) => {
    const y = 3.28 + ri * 0.49;
    s.addText(label.toUpperCase(), {
      x: M, y, w: labW, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12.5, color: C.ink3, charSpacing: 2.2,
    });
    cells.forEach((cell, ci) => {
      s.addText(cell, {
        x: colX[ci], y: y - 0.02, w: cw, h: 0.44, margin: 0, isTextBox: true, valign: "top",
        fontFace: BODY, fontSize: 11.5, color: ci === 2 ? C.ink : C.ink3, lineSpacing: 15,
      });
    });
  });

  card(s, M, 5.9, COL, 0.92, C.raised);
  s.addText("WHY THEY CANNOT FOLLOW", {
    x: M + 0.3, y: 6.1, w: 3.0, h: 0.26, margin: 0, isTextBox: true, valign: "top",
    fontFace: DISPLAY, fontSize: 14, color: C.accent, charSpacing: 2.4,
  });
  body(s,
    "Delivery is measured against a projection written onto the deal at the moment the offer is made. " +
    "A company that was not in the transaction never saw the promise, so it has nothing to reconcile " +
    "against. That is a position, not a feature.", {
    x: M + 3.5, y: 6.08, w: COL - 3.8, h: 0.6, fontSize: 13.5, color: C.ink2, lineSpacing: 18,
  });
  source(s, "Plan section 3.2.2 on the competitive set and section 4.6 on the buyer. Neither data company executes a deal.");
  s.addNotes(
    "This is the question I would ask, so let me answer it directly. SponsorUnited has 355 people and " +
    "has raised nearly 39 million euros. What is left for me.\n\n" +
    "They sell a database. It tells a large brand or an agency what the sponsorship market is doing: who " +
    "sponsors whom, what the activations look like, what a property is worth. It is genuinely good, and " +
    "it is bought on enterprise seats by organisations with a sponsorship department.\n\n" +
    "What it cannot tell you is whether your own deal delivered what was promised, and the reason is " +
    "structural rather than technical. We write the projected reach onto the deal row at the moment the " +
    "offer is made, before the athlete has even accepted. The variance you saw on slide nine is that " +
    "projection against what actually landed. A company that was not in the transaction never saw the " +
    "promise, so there is nothing for it to reconcile against. They can tell you what the market did. " +
    "Only the platform that brokered the deal can tell you what your money did.\n\n" +
    "And their data is scraped from public posts. Ours comes through the connector the athlete linked in " +
    "order to get paid by their fans, which is the flywheel slide again: consented, first party, and free " +
    "to acquire because the athlete came for a different reason.\n\n" +
    "One honest point. I am not beating SponsorUnited. If a brand is big enough to buy them, we are not " +
    "in that conversation. Their 355 people are the cost of an enterprise sales motion, and that motion " +
    "cannot be run at a two thousand euro deal. Their size is the reason the bottom of this market is " +
    "still empty."
  );
}

// B4 — pricing
{
  const s = backup("Backup, pricing", "15% sits between the only two published rates in the market",
    "Both ends of the corridor are real competitor economics, derived from filed accounts.");
  const corridor = [
    ["Patreon", "10%", "all-in, on filed accounts", C.ink2],
    ["Stride", "15%", "flat, and no monthly athlete fee", C.accent],
    ["OnlyFans", "20%", "and agencies take 20 to 50% on top", C.ink2],
  ];
  const cw = (COL - 0.6) / 3;
  corridor.forEach(([who, rate, note, colour], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 2.4, cw, 1.95, i === 1 ? C.raised : C.panel);
    s.addText(who.toUpperCase(), {
      x: x + 0.3, y: 2.62, w: cw - 0.6, h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 13, color: C.ink3, charSpacing: 2.4,
    });
    s.addText(rate, {
      x: x + 0.3, y: 2.92, w: cw - 0.6, h: 0.8, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 50, color: colour, lineSpacing: 50,
    });
    body(s, note, { x: x + 0.3, y: 3.76, w: cw - 0.6, h: 0.5, fontSize: 12, color: C.ink3, lineSpacing: 16 });
  });
  body(s,
    "At 15% we undercut the nearest comparable for any athlete earning under €1,380 a month, which is " +
    "the entire long tail we are built for. The decision forfeits €0.5M of Y7 revenue against a 20% take, " +
    "and buys a pricing argument that survives contact with the exact athlete we target.", {
    x: M, y: 4.62, w: COL, h: 0.9, fontSize: 14, color: C.ink2, lineSpacing: 20,
  });
  source(s, "Patreon and OnlyFans published terms and filed accounts; agency rates from published commission guides.");
}

// B5 — scenarios
{
  const s = backup("Backup, scenarios", "The plan survives its own pessimistic case",
    "Each case re-runs the whole model on changed drivers rather than adjusting the base result.");
  const rows = [
    ["Pessimistic", "Fans/athlete −25%, monetise −20%", "€2.34M", "€399k", "€541k", "Y5"],
    ["Base", "As modelled", "€3.01M", "€743k", "€414k", "Y4"],
    ["Optimistic", "Fans/athlete +25%, monetise +20%", "€3.59M", "€1.04M", "€347k", "Y4"],
  ];
  const headers = ["Case", "What changes", "Y7 revenue", "Y7 EBITDA", "Capital need", "Profit from"];
  const colX = [M, M + 1.9, M + 5.3, M + 7.0, M + 8.7, M + 10.4];
  const colW = [1.8, 3.3, 1.6, 1.6, 1.6, 1.35];
  headers.forEach((h, i) => {
    s.addText(h.toUpperCase(), {
      x: colX[i], y: 2.4, w: colW[i], h: 0.26, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.0,
    });
  });
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 2.7, w: COL, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });
  rows.forEach((r, ri) => {
    const y = 2.84 + ri * 0.62;
    if (ri === 1) {
      s.addShape(pres.ShapeType.rect, {
        x: M - 0.12, y: y - 0.08, w: COL + 0.24, h: 0.56,
        fill: { color: C.raised }, line: { width: 0 },
      });
    }
    r.forEach((cell, ci) => {
      s.addText(cell, {
        x: colX[ci], y, w: colW[ci], h: 0.36, margin: 0, isTextBox: true, valign: "top",
        fontFace: ci === 0 || ci > 1 ? DISPLAY : BODY,
        fontSize: ci === 0 ? 17 : (ci === 1 ? 12.5 : 17),
        color: ci === 1 ? C.ink3 : (ri === 1 ? C.accent : C.ink),
      });
    });
  });
  body(s,
    "Even the pessimistic case breaks even, one year later and on €541k instead of €414k. " +
    "The downside here is a slower, smaller company rather than a failed one, and that is the " +
    "property the staged raise is designed to protect.", {
    x: M, y: 5.0, w: COL, h: 0.8, fontSize: 14, color: C.ink2, lineSpacing: 19,
  });
  source(s, "Stride financial model, scenario table.");
}

// B6 — risk
{
  const s = backup("Backup, risk", "Eleven risks scored, and one of them is the thesis",
    "Probability × impact, both on a 1 to 5 scale. Nothing is rated more likely than 3.");
  const risks = [
    ["R1", "Fans do not pay for niche-athlete content", "3 × 5 = 15", "Three months of real revenue from one anchor athlete, before the second tranche", C.critical],
    ["R4", "A funded entrant copies the model", "3 × 4 = 12", "The defence is scoring history and athlete relationships, which take time nobody can buy", C.warn],
    ["R5", "Regulatory: DAC7, age assurance, startup law", "3 × 4 = 12", "Compliance built in rather than retrofitted; reporting is a product feature", C.warn],
  ];
  risks.forEach(([code, what, score, mitigation, colour], i) => {
    const y = 2.4 + i * 1.12;
    card(s, M, y, COL, 0.98);
    s.addText(code, {
      x: M + 0.28, y: y + 0.26, w: 0.6, h: 0.4, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 24, color: colour,
    });
    body(s, what, { x: M + 1.0, y: y + 0.17, w: 4.1, h: 0.6, fontSize: 14, color: C.ink, lineSpacing: 18 });
    s.addText(score, {
      x: M + 5.2, y: y + 0.3, w: 1.5, h: 0.3, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 16, color: colour,
    });
    body(s, mitigation, { x: M + 6.9, y: y + 0.2, w: COL - 7.2, h: 0.62, fontSize: 12, color: C.ink3, lineSpacing: 16 });
  });
  body(s,
    "A risk map that is evenly scattered has not identified which risk is the real one. R1 is the thesis, " +
    "and the entire financing structure exists to buy it down cheaply.", {
    x: M, y: 5.9, w: COL, h: 0.5, fontSize: 13.5, color: C.ink2,
  });
}

// B7 — valuation and dilution
{
  const s = backup("Backup, valuation", "Where the €1.8M pre-money comes from",
    "Two methods that disagree, and the disagreement is the honest part.");
  stat(s, M, 2.4, 3.2, "DCF enterprise value", "€1.23M", "25% WACC, 3% terminal growth. Below the pre-money, which is normal for a pre-revenue venture.", C.ink, 46);
  stat(s, M + 4.3, 2.4, 3.2, "Comparable set", "€1.8M", "Benchmarked against Sponsoo and OpenSponsorship, the two companies running the same model.", C.accent, 46);
  stat(s, M + 8.6, 2.4, 3.2, "Founder and team hold", "65.2%", "After both tranches, the optional growth round and a fully topped 10% ESOP.", C.ink, 46);

  s.addShape(pres.ShapeType.rect, {
    x: M, y: 4.55, w: COL, h: 0.014, fill: { color: C.track }, line: { width: 0 },
  });
  const dil = [["Pre-seed", "€150k at €1.8M", "87.3%"],
               ["Extension", "€250k at €3.5M", "81.5%"],
               ["Growth, optional", "€1.5M at €12M", "72.4%"],
               ["After ESOP", "10% pool", "65.2%"]];
  dil.forEach(([stage, terms, held], i) => {
    const x = M + i * ((COL - 0.6) / 4 + 0.2);
    const cw = (COL - 0.6) / 4;
    s.addText(stage.toUpperCase(), {
      x, y: 4.75, w: cw, h: 0.24, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 11, color: C.ink3, charSpacing: 2.0,
    });
    body(s, terms, { x, y: 5.0, w: cw, h: 0.3, fontSize: 12.5, color: C.ink2 });
    s.addText(held, {
      x, y: 5.3, w: cw, h: 0.42, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 24, color: i === 3 ? C.accent : C.ink,
    });
  });
  body(s, "Founder stake retained through each round", {
    x: M, y: 5.78, w: 6.0, h: 0.3, fontSize: 11.5, color: C.ink3,
  });
  source(s, "Stride financial model: DCF, comparable transactions from PitchBook, and the dilution waterfall.");
}

// B8 — the admission arithmetic
{
  const s = backup("Backup, the gate", "What the admission gate actually costs to run",
    "The one human step in the chain, priced from the policy itself rather than assumed.");
  const nums = [
    ["30.5%", "Admission rate by Y7", "rising from 20% in Y1 as the funnel improves, which makes it a filter rather than a formality"],
    ["4 min", "Median manual review", "priced at the same loaded salary the people line uses"],
    ["0.64 FTE", "Reviewer load at Y10", "at 8,500 athletes. Verification is not a money problem at this scale"],
    ["< 48 h", "Service level", "the reason to automate is latency, not cost: a queued athlete is not earning"],
  ];
  const cw = (COL - 0.75) / 4;
  nums.forEach(([value, label, note], i) => {
    const x = M + i * (cw + 0.25);
    card(s, x, 2.4, cw, 2.5);
    s.addText(value, {
      x: x + 0.26, y: 2.64, w: cw - 0.52, h: 0.7, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 34, color: C.accent, lineSpacing: 36,
    });
    s.addText(label.toUpperCase(), {
      x: x + 0.26, y: 3.38, w: cw - 0.52, h: 0.42, margin: 0, isTextBox: true, valign: "top",
      fontFace: DISPLAY, fontSize: 12, color: C.ink3, charSpacing: 2.0,
    });
    body(s, note, { x: x + 0.26, y: 3.86, w: cw - 0.52, h: 0.9, fontSize: 11.5, color: C.ink2, lineSpacing: 16 });
  });
  body(s,
    "A club nomination brings a roster of 20 to 40 athletes with the verification problem already solved, " +
    "and club-nominated applicants are admitted at 45% against 20% direct. That is the channel the growth " +
    "plan opens at Y3.", {
    x: M, y: 5.1, w: COL, h: 0.8, fontSize: 14, color: C.ink2, lineSpacing: 19,
  });
}

// ── write ───────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: path.join(__dirname, "Stride_Pitch_Deck.pptx") })
  .then((f) => console.log("wrote", f));
