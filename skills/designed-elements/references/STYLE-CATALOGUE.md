# Style catalogue — recognition and grammar, never skin

Sixty-six motion and film styles from two published libraries, each read in full and rewritten here in our own words:
fifty-one film styles from a library of style prompts (each a fixed eleven-section STYLE.md with a code-rendered demo) and
fifteen motion-design styles from a set of one-prompt films (each with checkable signature techniques). A style brief
([`STYLE-BRIEF.md`](STYLE-BRIEF.md)) uses this file in two ways only:

- **Recognition.** Each entry's **Essence** and **Not** lines say what a frame must show to read as that style, and what
  it is confused with. They exist to name the neighbours a brief must stay clear of (brief § 1), and to say what a
  reference the operator sent belongs to. **They are never a look to wear:** a brief's palette, typefaces and motion
  signature come from its subject (CRAFT § Style comes from the subject), and a medium is taken only when the operator
  or the client names it ([`STYLE-BRIEF.md`](STYLE-BRIEF.md) § Where a look may come from).
- **Grammar.** The **Camera** rows (move → what it expresses or serves), the **Native moves** with their *fits*, and the
  **Checkable techniques** of the motion-design entries are moves and numbers a brief may borrow for § 5, § 6 and § 8,
  written in the subject's own terms.

**Renders with** says what each style needs, read from its own demo code (2026-10-25) or its prompt's stated route:

| render class | in our lane? |
|---|---|
| Canvas 2D · DOM / SVG | yes — native to HYPERFRAMES-CONTRACT |
| a WebGL2 shader pass | possible — `det_check.py prove` passes it only under the software-rasteriser tolerance; untested here at length |
| three.js 3D | unvalidated — no determinism proof of a three.js scene in this lane yet; a brief naming one (`webgl-3d`) WARNs until it is proved and ruled |
| an offline 3D renderer | no — outside the HyperFrames lane |
| real source material | a sourcing and licence job before any render (imagery, scans, data, CAD) — every evidence-film style needs it |

The in-medium transitions several styles carry (a scan front, a page turn, an ink bloom, a dot wipe) are described in
their entries only; this kit ships no transition presets.

**Provenance.** `lemomo-ai/lemo-opuscar` @ `b5e8ef9393` (2026-10-19), `styles/*/STYLE.md` — MIT License, Copyright (c)
2026 LemoLab. `Vincentwei1021/mg-styles-15` @ `49052d80bf` (2026-10-05), `prompts/*.md` — MIT License, Copyright (c) 2026
Vincentwei1021. The entries are paraphrased and condensed from those files; the libraries' MIT notices apply to this
derived text, and both notices are reproduced in full under § Licence notices. Their demo films, code, palettes and copy are not reproduced. Where a style is defined by a named film,
show or game, the entry describes its grammar and names none of them; a slug in backticks is the upstream folder name.

---

## Part 1 — film styles

### Evidence films

#### Satellite briefing (`satellite-briefing`)
- **Renders with:** a WebGL2 shader pass over real source material (licence-clean imagery).
- **Essence:** real, licence-clean imagery of a real place, graded to an analyst's grey; thin white hairlines are what was measured; one zoom from orbit to the ground built from nested plates; one finding per screen in a single accent; true colour returns only where the story turns.
- **Not:** a paper chart, a glowing HUD, a blueprint, an isometric diorama, a keynote.
- **Camera:** oblique orbit with the limb → scale, an opening or a return · log-zoom dive to nadir → checking a claim · locked nadir with a slow creep → time running in one place, a measurement · push-in on a point → singling out · track along a line → a distance, a river, a border · whip pan → "meanwhile", a counter-example · climb back to orbit → consequence, an ending.
- **Native moves:** the map against the photograph (a printed claim torn away by a scan to show the ground — fits: a lake still on maps, a city never built) · time rings in a locked frame (dated plates scan in, the lost band flashes — fits: a glacier, sprawl, a burn scar) · the range line (a ticked line grows A→B with a rolling reading — fits: a shore that moved, a village to its well) · the dive and the climb · colour returns only on the subject (fits: a refilled reservoir) · the reticle opens into the title frame.

#### Engineering briefing board (`briefing-board`)
- **Renders with:** Canvas 2D over real source material (photographs cut out with a matte).
- **Essence:** one filmed whiteboard wall (enamel, window light, erased ghosts) with real cut-out photographs landing on it with weight; magnets, tags, a ruler, stamps; marker ink in three fixed meanings (graphite = names, blue = measurement, red = the decision only); every shot is a crop of the finished wall, seen whole once at the end.
- **Not:** a hand drawing line art on a flat page, a paper data chart, a keynote with headers and page turns.
- **Camera:** ride a line with the pen → measuring, lengths compared · tilt along projection lines → the same quantity in another view · slow push with a slight Dutch → an approaching problem · pull back and sideways → stating a rule · whip with the line, overshoot, settle → a result that exceeds · rise along a leader → evidence to verdict · staircase framing → items in sequence · judgement frame held ≥ 2.5 s → pass/fail against a limit · long pull-back to the whole wall → the summary.
- **Native moves:** the whole-wall reveal (design the wall as a poster first, every shot a crop, one zone kept for the end — fits: a roadmap, a budget) · the subject passes through the answer · ride the dimension line (a quantity as a real length — fits: four cars' ranges) · projection lines between two views · magnets as countable units (clack on, pop off — fits: seats in a vote) · erase to a ghost (last year's plan under this one) · the stamp verdict · the physical answer laid down · a leader from the deciding number to the conclusion.

#### LiDAR survey (`lidar-survey`)
- **Renders with:** three.js 3D point and surface shaders over real source material (airborne laser returns).
- **Essence:** real airborne laser returns floating as a measured cloud in the dark; a scan front or a cutting plane condenses them into a solid raking-lit surface; classes (ground, trees, buildings, water) are layers to peel; one hairline reading at a time in the accent.
- **Not:** an invented hologram interface, overhead photographs, a blueprint, low-poly terrain, a product render.
- **Camera:** locked nadir with a slow push → "what a photo shows", a before · crane down to oblique → entering the data · low oblique close to the cloud → volume, things standing up · slow orbit → studying while the plane does the work · rising pull-back → the scale of what was found · lateral track → travelling a wall, a road, a coast · push to a section → the detail that proves it.
- **Native moves:** photo to points (a scan line crosses an aerial photo — fits: a site visit, a quarry's real volume) · the canopy peel (a plane descends by height and lifts the returns above it — fits: ruins under forest, flood channels) · points condense into a surface (fits: a building scan to a shell) · the section with its profile chart (fits: a levee's height, a bridge clearance) · the window — the measured area as a stage inside dim unmeasured points · the regrowth — the removed layer returns as a ghost.

#### Projection on a white model (`white-model`)
- **Renders with:** three.js 3D over real source material (building footprints and heights).
- **Essence:** a matte white massing model of a real place on a plinth in a dark room; data arrives only as projected light, brighter on faces turned to the projector, spilling a little past the plate; one layer at a time, each with its own light gesture; lights out starts the data, lights up ends it.
- **Not:** an icon diorama, invented terrain, wireframes, satellite imagery, a laser scan.
- **Camera:** macro glide at rooftop height, shallow focus → the model is a real object · crane up and back → a pattern only seen from above · slow orbit with a rise → layers accumulating · boom down to a low angle against black → height, a skyline · side-on track along a line → a shadow, a route, a view line · pull back as the house lights return → the data stops, an ending.
- **Native moves:** lights out, lamp on (relay, darkness, the lamp strikes) · the hole (light only the set that answers a question and let the gap draw the shape — fits: a damaged centre, land one owner holds) · layers by time (buildings switch on by decade, each faster — fits: a campus by phase) · the rising level (a band of light climbs every facade — fits: flood depth, a height limit) · the sun clock (a real sun for a real date sweeps the shadows, one traced and measured) · the pick-out (one building alone with a pin) · lights up.

#### Data physicalisation (`data-physical`)
- **Renders with:** three.js 3D (PBR) over real source material (published statistics).
- **Essence:** statistics built as countable objects — one plate, block or coin per stated unit, exact scale, every tenth unit in a heavier material so the stack is its own ruler; studio product lighting on real materials; data grows by pieces being placed, never by scaling; once, the chart is revealed as an installation.
- **Not:** a flat icon infographic, a product hero render, a paper chart, a black neon stage, a toy.
- **Camera:** macro dolly along a stack's edge with a rack focus → the unit is real · low lateral track along the series → time, growth · locked three-quarter on two stacks → a comparison · crane with the rising top → accumulation · pull back to near top view → the whole as an object · slow orbit of the base → a title, a breath.
- **Native moves:** the unit close-up (one piece bracketed "= X" — fits: CO₂ as steel plates, a budget as banknote bricks) · the paired climb (two materials on one base, the crossover held before the verdict) · the feed (this period's increase lands piece by piece on last period's level, the counter tied to landed pieces) · chart to installation (pull back until bars become a dial, a skyline) · the last object (one heavy piece lands carrying the total).

#### Exploded teardown (`teardown`)
- **Renders with:** three.js 3D (PBR) over real source material (the product's CAD and board files).
- **Essence:** a real product built from its own engineering files, lit like a studio packshot and taken apart on one axis with even gaps; every number is pinned to its part by a leader or a perspective dimension line; the camera never stops travelling — orbit outside, macro inside — and the product closes into one object again.
- **Not:** a single-object material-beauty render, a line drawing on a grid, a keynote stage, an assembly manual with step numbers and hands.
- **Camera:** orbit while layers separate → the order of assembly · grazing macro dolly → touch, finish · dive between layers → being inside, a hidden part · slow push on one still part → the part that matters · rise through the stack → one subsystem to the next · fast pull back → synthesis, a close · high three-quarter drift → sizes, pitch, thickness.
- **Native moves:** the wave lift (repeated parts rise in a wave ordered from a corner — fits: battery cells, solar tiles) · inside the gap (the camera enters between two lifted layers) · the leader that lands on the part (a macro label ending on the component) · dimensions drawn on the closed object in perspective · one real motion (a part performs its true mechanism once — a shutter, a buckle) · lights on inside (emitters switch on while it is apart).

#### Microscope story (`microscope`)
- **Renders with:** Canvas 2D over real source material (micrographs with their pixel size).
- **Essence:** real micrographs of one specimen; one continuous log-zoom from the slide in the hand to a single cell through nested levels of the same scan; focus breathes at each magnification change and a focal plane sweeps on landing; scale bar, field of view and readings come from the file's own metadata; the stain keeps its true colour; one reading per screen.
- **Not:** a grey-graded satellite briefing, a hologram HUD with crosshairs, a paper chart, a keynote.
- **Camera:** the dive (log zoom with roll) → going to look for yourself · locked frame with a slow creep → a measurement · truck at one magnification → a second sample, "meanwhile, nearby" · pull back to frame two marks → the verdict · focal-plane sweep → arriving, depth · the climb (reverse dive) → consequence, an ending.
- **Native moves:** the dive with the turret clicking at each real level change (fits: a biopsy to its cells, a coating to its crystals) · counting the colour (a circle, a scan front, every counted pixel lit, the share rolling to its landing value — fits: porosity, coverage) · two circles, one verdict (treated against untreated) · the focal sweep and the ring around one structure with its size · the climb back to the eye's scale.

#### Archive light table (`archive-lighttable`)
- **Renders with:** a WebGL2 shader pass over real source material (archive scans and catalogue records).
- **Essence:** real archive objects — glass negatives, slides, letters, clippings — on a cool backlit light table; a loupe lands and inside the lens the object changes state (a negative turns positive, one line of type lights, a photograph opens into depth); real catalogue numbers and dates pinned to each object; one signal colour; clean and modern, no vintage filter.
- **Not:** a newsprint halftone dossier, ground seen from orbit, a chart, a keynote.
- **Camera:** table glide → surveying, the next piece of evidence · loupe landing and push into the lens → "look closer", the claim · tracking along a line inside the lens → reading a ledger or a caption · photograph space with dolly and parallax → being there · rise out of the lens → the evidence noted · pull back to the whole table → an index, a close.
- **Native moves:** negative to positive under the loupe (a develop front from the lens centre — fits: a founder's portrait plate, an X-ray becoming the product) · the line lights up (one line brightens, the rest dims, one number lifts into a card — fits: a ledger entry, a patent claim) · into the photograph (the rim grows past the frame, the picture gains layered depth) · measuring on the photograph (a perspective ruler landing on the recorded figure) · two records side by side, held until read, one struck · the table becomes the index (every tag flies into one list).

### Hand-drawn and painting

#### Crayon picture book (`crayon-book`)
- **Renders with:** Canvas 2D strokes into a WebGL2 shader pass.
- **Essence:** a picture-book page drawn live in wax crayon on toothy paper — a box of about a dozen crayons, dark non-black outlines, colour spilling past the line, every line boiling on twos — with at most one watercolour wash that wax resists; drawing and colouring are the plot; narration is the page's printed words.
- **Not:** cute vector art behind a crayon filter, a whiteboard with a marker hand, a watercolour painting (the wash is a guest), a chalkboard.
- **Camera:** locked full page → paper before drawing, a tableau · push toward a character → "this one" · locked medium close-up → substitution poses act, comedy · tilt along a gaze → discovery, something huge · tight follow → the world draws itself ahead of the subject · held wide while the brush moves → weather, night falling · slow truck across the page → a list, a family · pull out past the page edge → the page as an object · page turn → a new chapter, a time jump.
- **Native moves:** wax resist (white crayon invisible until the wash finds it — fits: a hidden message, a product's hidden feature) · drawn live (the world drawn just ahead of the hero — fits: a bridge plank by plank, a timeline) · colouring is an action (fits: a town lighting window by window) · the boil calmed to quiet the film · child logic (wrong perspective, faces on objects, numbers in the sky) · it is a book (pull back, turn the page).

#### Watercolour brush (`watercolor`)
- **Renders with:** Canvas 2D.
- **Essence:** a journal page that paints itself on warm cotton paper — every form is translucent brush strokes with dry-brush flying white, structure before detail; the paper is the white and the eraser (paper-coloured mist); a hand-written note with a pen leader beside each specimen; the palette may carry the data.
- **Not:** ink tones with a calligraphic gesture, thick knife paint, a crayon picture book, vector art under a watercolour texture.
- **Camera:** long lateral dolly over one continuous painted world → a gradient, a journey, a transect · vertical tilt along one object → scale · locked sheet while things paint in → a specimen plate, a recipe · slow push into a detail → leaning in · pull back to a map → the whole re-framed · mist wash to blank paper → a chapter end · page turn → a new entry · a change in time on a locked view → growth, decay.
- **Native moves:** painting-in as reveal (fits: the stages of a building, a dish's ingredients) · burst (a whole group paints in under a second for a peak) · palette as data (sky and ground blend by a measured value — fits: pollution along a river) · specimen and note · mist erase (fits: forgetting, a site demolished) · map in time (fills change through years) · painted transformation (an object cross-fades to burnt or wet and regrows).

#### Chinese ink wash (`ink-wash`)
- **Renders with:** Canvas 2D strokes into a WebGL2 shader pass.
- **Essence:** xieyi ink on rice paper in five ink tones plus one vermilion (the seal, one tiny accent at most); forms made by loaded "boneless" strokes whose dark edge is the contour, wet washes that bleed, dry fast strokes of flying white; 60–80 % of the frame is empty paper; things are painted into existence, not cut to.
- **Not:** colour watercolour, vector art with a brush texture, a calligraphy title sequence.
- **Camera:** locked frame on the paper → a thing forming · right-to-left handscroll pan → time and distance as one painting · vertical hanging-scroll tilt → stages stacked, generations · lateral track with slow far parallax → travel · high wide with a tiny figure → solitude, scale · low angle on a towering dark mass with a slow push → threat · hard cut to an extreme close-up (the only hard cut) → a shock, a decision · push into an ink bloom or mist → passing between states · pull back until a mark joins the whole → irony of scale · return to an earlier framing → what changed.
- **Native moves:** one stroke is everything (fits: a product born from one line, a city from one street) · emptiness is matter (lifting ink reveals paper — fits: a crowd parting, an absence in a portrait) · stroke order as choreography (fits: a signature, knife work) · one fast flying-white stroke out of a silence (fits: a sprint finish, a decision) · the ink-bloom transition (fits: memories, eras) · the handscroll seen whole at last (fits: a supply chain, a day in a street) · splitting a mass (fits: a barrier falling).

#### Impasto, palette knife (`impasto`)
- **Renders with:** a WebGL2 shader pass (a height field raked by light).
- **Essence:** a moving oil painting of knife strokes — flat, sharp-edged planes with ridges, lips and dragged second colours, raked by light over a height field; value structure first (it must read at thumbnail size), hard edges and the smallest strokes only at the focus; static paint never moves; the purest chroma reserved for the subject.
- **Not:** a swirling Van Gogh filter, a brush texture over vectors, transparent watercolour, a painterly photo filter.
- **Camera:** slow truck and push on a wide → a world observed · push-in through a silence → inner pressure · tilt up from the ground or a reflection → discovery from below · pull back from a close-up → the world answering · rotating overhead crane-out → a pattern emerging from many · the same wide repeated → before/after · locked frame while the light moves → time and weather as the actor · macro slide along the paint → the matter itself · whip pan into a new plate → energy, a list.
- **Native moves:** colour re-laid by the knife (a grey world repainted to colour stroke by stroke — fits: a town waking, a relaunch) · the one coloured thing in a grey world (fits: one person in a crowd, a warning light) · motion paints the picture (paths seen from above leave paint — fits: delivery routes, migration) · raking light dropped to grazing at the peak · the paint-over transition with a scrape · sound made visible as a paint ribbon (fits: a broadcast, a rumour spreading).

#### One-line drawing (`one-line`)
- **Renders with:** Canvas 2D.
- **Essence:** a single ink line on warm white paper that never lifts — characters, places and time are all that one line; no fills, no second weight; we watch it drawn, the camera following the nib with a little lag; the pen appears only as a soft shadow; one accent colour at most, used once; scenes morph, never cut.
- **Not:** a whiteboard explainer with a hand, ink-wash tones, line-art animation with cuts and many strokes.
- **Camera:** follow the nib → travel, a thread of time · composed frame with little follow → a scene read whole, a joke · macro on the nib → the act of making, a signature · hold with a slow push → a stop, a loss · mirrored framing → rhyme across time · continuous pull-back → everything was one picture · lateral scroll with the line running ahead → a horizon, a chart · roll with the line → vertigo, play.
- **Native moves:** the pen never lifts (fits: a river source to sea, a production line) · the line is time (its character ages or strains) · transformation (seed → tree → table; a sketch → a product) · stopping is an event (the nib stops, ink pools, the music drops to silence for 1.5–3 s) · the reverse-designed scale reveal (every vignette is part of one final picture — fits: milestones forming a logo) · the handoff to another hand's shadow · the line as a graph (a heartbeat, a match's momentum).

#### Whiteboard explainer (`whiteboard`)
- **Renders with:** Canvas 2D.
- **Essence:** one glossy dry-erase board drawn live with no hands — single-line handwriting written stroke by stroke, floating markers with real cast shadows, magnets that move, an eraser that rewinds, ghosts of old lessons; each idea owns a region of the board and the camera travels between regions instead of cutting; at most three marker colours with fixed meanings; every stroke sounds.
- **Not:** a blueprint sheet, a crayon picture book, a kinetic-type explainer with text animated as blocks.
- **Camera:** pull back from a tiny drawing → scale · ride the line the pen draws → one idea leading to the next · hold still → read now, an equation · whip to a new region → a twist, a "but" · return to an earlier region → a free callback · split view of two regions → before/after · slow push into one symbol → this term is the point · track along a long diagram → a pipeline, a timeline · pull back past the board edge → the whole lesson as one picture.
- **Native moves:** writing in stroke order, finishing on the spoken word (fits: compound interest term by term) · the pen leads the camera (fits: a nerve signal, a supply chain) · magnets as the only movers (fits: a truck on a route, a player on a pitch) · the eraser rewinds (fits: an undo, "what if we hadn't…") · two pens at once as a duet (fits: two savings plans) · ghosts of the old lesson become relevant (fits: last year's forecast) · the full-board view.

#### Urban sketch, pen and wash (`urban-sketch`)
- **Renders with:** Canvas 2D strokes into a WebGL2 shader pass.
- **Essence:** a location sketchbook page — a thin sepia fineliner that wobbles, overshoots and breaks, with loose transparent watercolour dropped on top 1–3 px off the line; paper white reserved; the page frays into dabs at its edge, leaving margins for handwritten date and place; colour can be withheld and arrive as an event.
- **Not:** line-free wet watercolour, a marker explainer, brush calligraphy — line and wash, both, always.
- **Camera:** push-in → a detail observed · lateral follow on a spring → an object carried, a walker · crane up → a skyline, a view opening · whip-tilt with slight roll → a gust, a surprise · punch-in with a short shake → an impact · pull back to the whole page → the sketch as an object · tilt into the margin → from picture to notes · slow pan over a line-only area → the world before colour · hold while the pen draws → noticing · page turn → another day or place.
- **Native moves:** line before colour (the drawing is the spectacle — fits: a façade, a chef plating) · colour as arrival (a wet front spreads from a source and paints the page — fits: a sunrise over a harbour, market lights switching on) · the one coloured thing (fits: a red umbrella in the rain, a kite) · the page as frame (pull back to the whole page with margin notes — fits: a travel diary) · carrot people for distant crowds.

### East Asian traditions

#### Shadow puppetry (`shadow-puppet`)
- **Renders with:** Canvas 2D pieces into a WebGL2 shader pass.
- **Essence:** a cotton screen lit from behind by flickering oil lamps; flat jointed puppets of translucent dyed hide, carved like lace, so colour arrives by transmitted light — holes glow brightest, overlaps darken; visible rivets and rods; live theatre, so puppets tremble and loose parts swing; brightness is a lamp count, never a grade.
- **Not:** a black silhouette film, front-lit paper-cut, stained glass with lead lines, flat vector cut-out animation.
- **Camera:** audience seat with heads below → "this is a show" · push through the frame onto the cloth → entering the tale · lateral pan across a wide cloth → a journey, a procession · follow one puppet → being with one figure · crash zoom of a few frames on a percussion hit → an entrance, a pose · whip pan along a moving piece → cause to effect · locked wide → counting, stages · medium-close with empty cloth between two pieces → a parting · close on a carved detail → a vow, a clue · tilt from the ground strip up → hierarchy · truck round to the back (mirror view) → the trick revealed · pull back into the dark room → the story ending for the night.
- **Native moves:** the light is the world (lamp count drives heat and colour — fits: servers switching on, a fever) · off the screen is big and blurry (a piece pulled toward the lamp — fits: a rumour growing, a deadline snapping sharp) · go behind the screen (fits: how it is really made, who controls a market) · carved and translucent (open faces vs solid — fits: an x-ray of a system) · hand-held tremor (fits: a nervous interview) · piece swap on a rod (fits: seasons, a machine's states) · strip lift-off (fits: geological layers, an old town under a new one).

#### Ukiyo-e (`ukiyoe`)
- **Renders with:** Canvas 2D.
- **Essence:** every shot is a complete woodblock print — washi, a double ink border, flat colour from separate blocks slightly out of register with the black key line, woodgrain and baren rubbing, hand-wiped bokashi skies, a vertical title cartouche and a red seal; depth only by stacked flat layers, mist bands and bold cropping; most of the frame never moves.
- **Not:** flat vector art under a paper overlay, bleeding ink wash, anime cel shading.
- **Camera:** locked on one sheet → reading a print on a wall · handscroll slide right to left between sheets → travel, the next station · very slow push toward a framing device (a window, a fan) → attention narrowing · tilt past the border into the mount → something larger than the print · pull back from one sheet to many → the series whole · crash zoom into the paper texture → a dream, a memory dissolving · pan across a triptych → a scene too wide for one sheet · hard cut to a blank sheet → a held breath.
- **Native moves:** a series of views (one constant subject placed differently each time — fits: a product in five homes, a street in four seasons) · the handscroll (fits: a supply chain, a recipe's steps) · printing block by block, each colour snapping into register (fits: a building going up) · paper is the white (white floods and washes the print back to a blank sheet — fits: a snowfall erasing a town) · the frame is an object something breaks out of (fits: a runaway success) · alternate impressions (one key block, new colour blocks: day → night) · the triptych that only reads joined.

#### Red paper-cut (`papercut-red`)
- **Renders with:** Canvas 2D.
- **Essence:** front-lit opaque red cut paper laid flat on paper grounds — the cut is the drawing, detail and expression come only from what was cut away (sawtooth, crescent, cloud, swirl cuts, fold-symmetric rosettes); jointed cut-out figures step at 12 fps; ground and hero are different paper families; gold foil once, late; backlight is a special event saved for the moment that needs it.
- **Not:** backlit shadow puppetry with hide and rods, flat vector art with strokes and gradients, a silhouette film.
- **Camera:** extreme close-up following the scissor tip → making, a precise act · flat locked front view → the cut-out as an emblem, a title · slow pan across paper layers → a world laid out, a timeline · low wide with a shape standing up from the ground layer → threat, a deadline arriving · top-down tabletop → folding, cutting, sorting as the plot · push to a lit piece then pull back to many → one act spreading · page turn or sheet peel → day to night, chapters · pull back to the object in a room → the film was a thing someone made · rotation around a rosette → a cycle, a team.
- **Native moves:** fold, cut, unfold on a strong beat (one cut becomes many — fits: one design mass-produced, one teacher many students) · holes are light (a backlit piece projects its pattern onto the world) · symmetry replicates (rosette → window flowers → fireworks — fits: a franchise, a song spreading) · scraps have a future (offcuts return as snow or stars — fits: recycling, small failures adding up) · everything is one flat sheet (a ridge stands up and becomes a creature) · a mirrored pair cut from one fold (fits: twins, a partnership).

#### Paper-cut lightbox (`paper-lantern`)
- **Renders with:** three.js 3D.
- **Essence:** a shallow shadow box of 6–9 cut card sheets lit from behind — a value ladder from bright translucent back layers to a near-black opaque front is the depth; warm light glows through the paper, windows and moons burn through holes, every layer casts a soft shadow on the one behind; the camera is a macro lens inside the lamp; the film may step out to the real lamp on a table.
- **Not:** flat paper-cut animation, shadow puppetry on a single screen, a 3D diorama — every element is a flat sheet parallel to the box front.
- **Camera:** slow near-frontal dolly in → being drawn into a place · slow dolly out → loneliness, the whole place · rack focus between layers → attention moving in depth, now and then · lateral travel with depth parallax → a journey · top-down on the layer stack → a made thing as a craftsman sees it · push into or pull out of the box → the frame as an object, a story told · locked frame with only the light changing → a vigil, a night passing · tilt up or down the stack → a mountain, a well · near-plane occluder wipe → a curtain between chapters.
- **Native moves:** the lamp turns on (source, far layers, then windows one by one — fits: a shop at dawn, a stadium before a match) · two windows, one light (two places sharing one moon — fits: a long-distance friendship, sister cities) · depth as distance (layers move by depth — fits: a migration, shipping a parcel) · paper that writes itself on the spoken word · the box as keepsake in a real room (fits: an anniversary, an unboxing) · light bursting from an opened thing · a silhouette in a window.

### Print and printmaking

#### Risograph print (`risograph`)
- **Renders with:** Canvas 2D plates into a WebGL2 shader pass.
- **Essence:** animation printed frame by frame on a stencil duplicator — 2–3 translucent spot inks on warm paper, overprints making extra colours, per-plate halftone screens, grain, pinholes and fixed misregistration; flat colour fields and silhouettes, no outlines; at most two plates per area, one as a tint; every main colour carries the first plate, so a one-ink frame still reads.
- **Not:** flat vector art with noise, CMYK pop-art halftone, opaque screen-print posters; never the machine maker's brand.
- **Camera:** wide lateral track with a small figure and empty sky → travel, routine · static wide with the subject crossing → comedy of scale · locked horizon, disc and figure → stillness, the one pause · low angle with big foreground shapes → energy, a launch · medium two-shot held for a look → a reaction · straight top-down with long shadows → a pattern, a map · push into a halftone field until dots are shapes → entering the print · pull back to reveal the paper → it was one sheet · match cut on a flat shape → a time jump, cause and effect.
- **Native moves:** plates as narrative (the world gains an ink at each turn — fits: a product arriving as a new ink, colour returning in a recovery) · two inks with a third where they meet (fits: a merger, two data sets whose overlap is the finding) · the overprint transition (a shape of one ink grows over the frame and shrinks into the next key shape) · registration as rhythm (kicks on accents, drift in a held moment, snap on the downbeat — fits: nerves, a memory coming into focus) · reflections as separated plates · knockout reveal (a shape of missing ink, its plate arriving later) · halftone scale (dots grow into shapes — fits: a crowd that turns out to be people) · it is a sheet of paper (stacked, folded, pinned).

#### Halftone dossier (`halftone-dossier`)
- **Renders with:** DOM / SVG, with a Canvas 2D paper and grain layer.
- **Essence:** a retro print case file on cream archive paper — halftone dots in a few flat inks for all shading, huge black-weight headlines with misregistered shadows, rubber stamps that slam, thick-outlined characters with boiling lines; case numbers, numbered exhibits, height charts and name plates as the frame; one idea per 2–4 s card with a keyword-highlighted caption bar.
- **Not:** a grainy two-ink riso zine, grid-driven Swiss kinetic type, a candy-coloured game show; dots, paper and stamps are in every frame.
- **Camera:** locked frontal with a small beat pulse → the page as a poster · slow push 1 → 1.05–1.08 → scrutiny before a verdict · shake with quadratic decay → a stamp, an impact · flash frames capped near 0.5 → a mugshot, evidence found · pan across a pinned board → connections, a timeline · snap zoom into a halftone detail until the dots are huge → "look closer" · page turn or folder slide → the next file · pull back to the whole desk → one file among many.
- **Native moves:** the accusation frame (a topic as "the case of X" with its counts — fits: a bias on trial) · numbered exhibits behind each beat (fits: five causes of a blackout) · the stamp verdict (APPROVED, EXPIRED) · the mugshot with height chart and flash (fits: a new species, the suspect in a bug report) · the evidence board linked with string, then shaken (fits: a supply chain, a heist timeline) · dot density as emotion (dots crowd the edges for tension, bloom for joy) · redaction bars lifting one by one (fits: a leaked memo, spoilers).

#### Woodcut print (`woodcut`)
- **Renders with:** Canvas 2D mask into a WebGL2 shader pass.
- **Essence:** a relief print that carves itself — black is the uncut wood, white is what the knife removed, so light is carved; cut direction follows the form and width follows the tone; pictures appear cut by cut, coarse gouges first; one colour plate at most, printed only into carved white, reserved for the one thing that burns; letters read mirrored until the sheet is pulled.
- **Not:** a swelling-line copper engraving, a flat-colour linocut poster, a photo through a threshold filter.
- **Camera:** track the knife tip → making, a route drawn · continuous pull-back as cuts spread → a line becoming a world · locked plate → a page of a wordless novel, reading time · slow macro push on a sculpted close-up → labour, touch · snap zoom and hold → the detail that breaks · frame in a frame (door, window) → exclusion, waiting · hard cuts on the beat, each a new impression → accumulation, days passing · crane up from a detail → consequence · rack between plates via the paper peel → one state printed over another.
- **Native moves:** light is carved (a burst of radial cuts — fits: a grid switched on, an insight) · carving is time (fits: a year of training, a building rising) · the mirrored block becomes the true print (fits: a vote result, a name cleared) · stab cuts frozen mid-air or inked back (fits: rain stopping, a disease receding on a map) · the one colour plate spreads and withdraws (fits: a single lit window in a blackout) · filter a sculpt or a frame into form-following cuts · wordless-novel sequencing of self-contained plates (fits: a life in seven plates).

#### Copperplate engraving (`engraving`)
- **Renders with:** Canvas 2D.
- **Essence:** an intaglio plate that engraves itself — every line swells and tapers like a burin cut, tone is built only from line families (one for half-tone, a crossing family for shadow, a third for the deepest dark), never from fills; a natural-history plate layout with numbered magnification roundels, leaders and engraved roman and italic lettering; transparent hand-laid wash comes afterwards, ink always on top.
- **Not:** a woodcut, a loose pen sketch, an engineering drawing, a sepia filter.
- **Camera:** the loupe following the burin tip → making, a signature · log-zoom pull-out → the line was part of something larger · push to a part and ride with its roundel → where → what in one take · tilt or pan along the sheet at reading zoom → labels in order, a parts list · pull back while something flies → everything placed in relation · locked frame or a ≤ 2 % breathing push → the plate as document · raking view across the copper → the cost of craft · cut from mirrored copper to the true proof → reversal.
- **Native moves:** the cut (burin mid-stroke, swarf rising) · the three passes (form gains volume pass by pass — fits: a building from its plan, a skill improving) · the magnification roundel scribed, flown to a margin with a leader, its label cut on landing (fits: a gear in a clock, a harbour inset on a chart) · the proof pulled (mirrored copper becomes true paper — fits: a draft made final, a coin's die and strike) · states of the plate (a region burnished out and re-cut — fits: a design revision) · hand colouring blooming on one part · natural size (a tiny true-scale figure beside the enlargement) · the finished plate with every label locked (fits: a museum label, a certificate).

#### Silkscreen travel poster (`silkscreen-poster`)
- **Renders with:** Canvas 2D.
- **Essence:** a poster printed on camera, one opaque flat ink per squeegee pull, 4–6 inks, later ink covering earlier completely; no halftone, no line work, no gradients — skies are stepped bands; 1–3 px registration slips leave paper slivers; values step light (far) to dark (near); one rare bright accent; a dark info band printed last; one template re-inked in a new palette per item makes a series. A scene style with jobs: a trail guide, an event poster, a destination series, a product drop, a seasonal notice.
- **Not:** translucent riso with halftone grain, ukiyo-e key-block lines with bokashi, carved woodcut line, low-poly 3D facets.
- **Camera:** truck with the squeegee, slight roll, frame edge in view → colour arriving, a hook · locked top-down full sheet → layers stacking · fast pull-back as the screen lifts → a layer complete, a title · push and tilt to the info band → reading facts, a price · truck through a foreground silhouette → into the next poster · crane through loose planes → depth, a route inside the print · slow dolly along a row of prints → a series, colourways · push into the mesh → the craft · log-zoom pull-back to the wall → the poster in the world, a final lockup.
- **Native moves:** one ink, one beat — facts print last, when they are read (fits: museum hours, a ferry timetable) · split fountain (several inks in one pull — fits: a festival sky) · palette re-ink (same geometry, new palette — fits: summer vs winter hours, three colourways) · registration slip → snap on one hit before the key facts (fits: a race date, a launch price) · paper as a colour (fits: a ski slope, a lighthouse beam) · the route stamped segment by segment in the accent · the series wall as the final lockup (fits: a tour's dates, a product family).

### Graphic and type

#### Swiss motion graphics (`swiss-motion`)
- **Renders with:** Canvas 2D.
- **Essence:** International Typographic Style in motion — a modular grid, one neo-grotesque family, flush left, paper, ink, light greys and one signal colour; every element snaps to the grid on a beat with one precise ease and no bounce; extreme scale contrast (a giant numeral beside tiny notes); the whole frame obeys a system so the one element that doesn't becomes a character.
- **Not:** a keynote with gradients and devices, a lyric video where words fly and spin, a data chart, a Bauhaus pastiche of primary shapes.
- **Camera:** locked spread → cause (left) → effect (right) · hard pan by one page or column → the next step in a system · rotate 90° and stop → the same thing read another way · pull out to a wall of artifacts → one programme, many outputs · push into one module → the unit of the system · the grid extends past the page → the system is bigger than the artifact · split into equal cells → parallel cases · vertical scroll through a column → a spec sheet, a manifesto.
- **Native moves:** the grid means something (columns and rows become hours, floors, years) · snap = beat (every arrival a percussion hit — fits: a feature list, a countdown) · programme (rules applied one by one to one artifact, then generating many — fits: a brand identity, a set of stamps) · extreme scale contrast (fits: a record statistic, a price) · the exception (one element linear and unsnapped — fits: an outlier, a rebel) · knife cut (a line crosses an element, it collapses — fits: budget cuts, removing a feature) · re-flow nearest-first around a change (fits: a team reorganised, a layout adapting to a phone).

#### 60s spy title sequence (`spy-titles`)
- **Renders with:** Canvas 2D.
- **Essence:** a cut-paper, four-ink opening title for a film that never existed — flat opaque inks, hand-cut edges with gaps and small paper shadows, figures abstracted to profile silhouettes with one colour accent; the credits are the architecture, props and vehicles; brass stabs are the edit points; one goal, a few locations, one reveal; strong 30° diagonals.
- **Not:** flat vector motion graphics, a halftone print, a Swiss grid, a gadget-and-gun-barrel spy parody.
- **Camera:** wide on a full credit line, then truck in → reading, then action · lateral track in one screen direction → pursuit, a delivery · hard cut on a brass stab → a new location · graphic match cut (same shape, same place) → rhyme, acceleration · locked single shape on a flat ground → mystery, an icon · silhouette against a giant circle → the hero moment · diagonal split into a grid → fragmentation, a team · vertical pan down a column of type → descent, a roster · push into a letter until it is a place → a door, a tunnel.
- **Native moves:** type is the set (each location is one credit line built as architecture — fits: a conference programme as a city, a menu as a restaurant) · credits as rhythm, landing on beats (fits: a feature list, a festival line-up) · graphic match cuts on an interval that shrinks as tension rises (fits: coin → planet → clock) · the diagonal grid that multiplies and later assembles something (fits: a logo assembled) · silhouette puppets acting in outline and timing (fits: a courier on a deadline) · the stop-time gag (freeze on a stab in silence — fits: a near miss, a price reveal) · the object of the chase becomes the title (fits: a product launch).

#### Art deco (`art-deco`)
- **Renders with:** Canvas 2D.
- **Essence:** gold engraved keylines on warm lacquer black, airbrushed hard-edged volumes with a gold rim on one lit side, every composition on one sacred vertical axis; ornament is the picture (sunbursts as backgrounds, stepped arches as frames, a dial as a progress bar, a bulb marquee as the reveal); motion is mechanical and symmetrical — unfolding from the centre, doors splitting on the seam, light switching on in counted order; one saturated accent for the protagonist.
- **Not:** a gold-foil slideshow, Art Nouveau curves, a flat vector poster, a 60s silhouette title.
- **Camera:** symmetric door split or revolving-door wipe → a threshold crossed · leaves sliding shut over the live shot → the end of an era · extreme low-angle tilt → aspiration, a tower · architectural section pull-out to a cutaway → progress through a structure, a company's floors · mirrored rotating overhead → people become pattern · push-in on a dial or clock → the number is the plot · match cut on shape → two places, one rhyme · low oblique along a marquee → light travelling letter by letter · pull back from detail to skyline → where the moment sits.
- **Native moves:** counted light (a bulb sign lights one letter per beat — fits: a launch countdown, votes tallied) · threshold doors at every scene change (fits: a company's departments, a museum's rooms) · the machine kaleidoscope (people or parts lock into a symbol — fits: a team becoming a logo) · dials carry the plot (fits: a funding thermometer, the altitude of a climb) · the architectural cutaway with the protagonist as a coloured dot (fits: data through a server stack) · sheen sweep and gold draw-on on a hit (fits: unveiling a trophy, a signature) · the one colour in a gold world (fits: the one product among competitors).

#### Blueprint (`blueprint`)
- **Renders with:** Canvas 2D drafting into a WebGL2 shader pass.
- **Essence:** one sheet of cyanotype paper on a dark drafting table; white line work on uneven Prussian blue drawn in drafting order (centre lines → outlines → detail → hatching → dimensions → balloons → labels); 2D orthographic or oblique projection only, never 3D rendering; the designed thing is the character, acting through its parts; blue and white only, plus one stamp ink used exactly once for the verdict.
- **Not:** a glowing 3D hologram, a marker whiteboard, a copperplate tonal engraving.
- **Camera:** whole sheet on the table → the document as an object, a verdict · medium on a figure with sky on one side → the design being drawn · track along a path of force (chain, pipe, beam) → cause and effect · 2× close-up cut on a downbeat → the mechanism's heart · locked hold → deliberation · oblique depth factor 0 → 0.5 → the flat drawing gains thickness · section line sweeping across → inside vs outside · lateral pan Fig. 1 → Fig. 2 → Fig. 3 → revisions, stages · slow wordless push → wonder.
- **Native moves:** drafting order, a layer per beat (fits: a bridge, a kitchen renovation) · live annotations (dimensions measure moving parts and their numbers change — fits: a heart valve, a folding bicycle) · fig. numbers as transitions ("FIG. 1" struck and rewritten — fits: product versions, construction phases) · projection as camera (exploded parts along the depth axis — fits: flat-pack furniture) · a symbol made real, once (a hatch becomes rain, a centre line becomes a road) · cyanotype and water (drops bloom and soften lines — fits: a flood defence) · the title block as story (status field = verdict, revision rows = history — fits: a rejected permit, an approval after years).

#### Stained glass (`stained-glass`)
- **Renders with:** Canvas 2D pieces into a WebGL2 shader pass.
- **Essence:** a stained-glass window seen from inside a dark stone hall — cut coloured glass in lead cames, faces and folds painted in brown grisaille, glowing only where the sun is behind it and throwing a soft coloured copy onto the floor; figures move rigidly piece by piece and freeze when the light leaves; the sun's colour is the clock; secular subjects only.
- **Not:** vector art with black outlines, a kaleidoscope or Voronoi filter, Tiffany Art Nouveau, reflective mosaic.
- **Camera:** truck sideways with the band of light → time passing, chapters · locked close-up on one pane → this panel is "now" · pull back to the whole window → the rule, the whole story · tilt down the shafts to the floor, then top-down → the picture leaves the glass and becomes light · hold through a crack with no cut → the medium breaking · slow push toward a small light → a secret, hope · tilt up to a rose → something above governs the panels · rack between a lit and a dark pane → past and present · low angle along the embrasure → institution, history · return to an earlier framing under new light → what changed.
- **Native moves:** light is time and the camera (only the lit pane is alive — fits: a recipe's steps, a factory's shifts, four seasons on one farm) · glass projects onto stone (a key scene plays in the floor patch, stretching as the sun sinks — fits: a trend drawn by lengthening light) · glass cracks, lead mends (pieces slide along the leads into a new picture — fits: a reinvention, an injury and recovery) · a window holds its own light at night (fits: a night-shift nurse, a server that never sleeps) · the window as a diagram (lancets as columns, a rose as a dial — fits: a product lineup, a cycle).

#### Pictogram motion (`pictogram-motion`)
- **Renders with:** Canvas 2D.
- **Essence:** a beat-locked flash-card catalogue film — one item per card: one faceless geometric pictogram (round-capped bars, a disc head) doing one action on a sun disc, a huge 900-weight title, a second-language line, a mono "07 / N" index and an N-tick progress HUD; a square-grid core pattern of discs, half-discs and tiny motif cells in five tones of one hue, whole rows cut and shifted sideways; each chapter owns one hue; every cut lands on a drum hit.
- **Not:** isometric depth, a Swiss type-only system, an emoting cartoon, a data chart.
- **Camera:** locked flat card → clarity, a spec that must be read · lateral track with a one-screen whip per beat → a family in one line, a route · slow drift along a row → browsing, a menu · vertical scroll by grid rows → a ranking, descent · push into one motif cell until it is the next frame → zooming into a part · pull back to a tiled wall of items → the whole set · tiles collapsing to one point → many become one · split along a grid line → versus, before/after.
- **Native moves:** one card = one item, the count is the hook (fits: every station of a line, every tool in a workshop) · chapter = colour (fits: orchestra sections, a company's departments) · one verb per item (fits: yoga poses, kitchen techniques) · the pace-ladder run at double speed (fits: four knife cuts, weekday routines) · a long take down a track of stations · the count-up slam on a bar (fits: tonnes recycled, years of a company) · the icon wall that turns one colour (fits: a year in summary, a team roster).

#### ASCII / CRT terminal (`ascii-crt`)
- **Renders with:** Canvas 2D glyph grid into a WebGL2 shader pass (the CRT).
- **Essence:** every image is real glyphs on a monospace grid chosen by ink density, glowing in one monochrome phosphor on curved glass with scanlines and afterglow; the only camera is the grid's font size (bigger characters push in, smaller pull out); subtitles are typed terminal output in a log strip; cold, patient, machine-calm, with at most one soft second colour switched on once.
- **Not:** an image through an ASCII filter, green "hacker" rain, pixel-art sprites, a vector sci-fi HUD.
- **Camera:** static 80-column terminal → waiting, procedure · push in (cells grow) → attention, a name, a decision typed · pull out (cells shrink) → one entry among thousands · push into a single glyph → what a symbol is made of · scroll the buffer → accumulation, a changelog · clear screen / hard redraw → a cut, a reboot · text becomes image as the grid shrinks → words turning into world · power on/off, degauss → birth, sleep, shock · pull back off the glass into a drawn room → who is reading.
- **Native moves:** the picture is made of words (a sentence's letters sorted by density become an image of only those letters — fits: a recipe becoming the dish, a manifesto becoming a crowd) · font size = camera (one character holds a sub-grid of text — fits: a company name made of employee names) · typing rhythm = editing rhythm (machine-even vs human-uneven; a blinking cursor as performance — fits: an apology, a password remembered) · CRT physics (power on as dot → line → frame) · a single colour change, once (fits: a first green leaf in a data log) · the log file tells the story (timestamps, error codes — fits: a launch day, a rescue).

### Information and keynote

#### Data storytelling (`dataviz`)
- **Renders with:** Canvas 2D over real source material (an openly licensed dataset).
- **Essence:** the chart is the film — real, openly licensed data drawn mark by mark on cream paper by a visible red-and-blue pencil, the chart type chosen by what the data is about; handwritten notes pinned in data space to the numbers; colour encodes only the value (a diverging ramp on a meaningful reference mean, never stretched); each mark is sonified as a pitch so the trend is heard before it is read.
- **Not:** a dashboard, a keynote with charts, decoration.
- **Camera:** extreme close-up on one mark following its leader → one fact, one life · full view first then dive to one mark → the pattern before the case · pull back as axes grow out of the marks → the frame arrives with the unit · track the pencil with the newest mark at ~60 % of width → progress · pedestal with rising data and a creeping Dutch angle → escalation · punch-in over 2 frames with a decaying shake and a jolt on rescale → an outlier · fast pull-out with roll and tremor → a rush, a panic · locked-off → a morph, a slow reading · hold on one mark then pull back → a verdict · pull and pan to add more real data → a scale switch · lateral pan across the memory zone → a biography.
- **Native moves:** one mark = one fact (fits: a chain's first store) · axes grow when the narration first names the unit · pinned annotations whose content and colour carry the arc (fits: an athlete's season) · breaking the frame, the torn edge kept as a scar (fits: a viral spike, a record flood) · the encoding morph (bars → a waffle of people, a map → a ranking) · the scale switch to a longer real record, never extrapolated · the empty next cell, a dashed slot for the value nobody knows yet (fits: next year's election).

#### Isometric infographic (`iso-infographic`)
- **Renders with:** Canvas 2D.
- **Essence:** a living system diagram on a floating isometric board with visible strata at its edges — flat blocks in three fixed face tones, no outlines on solids, no perspective, the projection never rotating; ink only for infographic furniture (leaders, pins, cut lines, hatched sections, tracking rings, a legend); numbers built from identical icons that add up; one hue per meaning, the subject's hue reserved.
- **Not:** low-poly 3D with perspective and lighting, a flat 2D explainer, a blue-line blueprint.
- **Camera:** follow along a route → process, cause → effect · hold wide with a circular inset → the system and the individual together · push through nested cutaways → a fall into scale · fast log pull-out → the big picture after a detail · locked frame while things accumulate → a system filling, overload · lateral follow over emptiness → a breath, distance · top-to-bottom tilt through strata → layers, a software stack · switch to a second board → here vs there, two eras.
- **Native moves:** the cutaway (cut line, the skin slides away, hatched rims stay — fits: a server rack, a beehive) · the Isotype number in a new arrangement each time (fits: votes, litres of water per product) · focus and context (everything greys except the subject — fits: one packet in a network) · a frame within the frame (a leader grows into a circular close-up inset — fits: a crack in a bridge) · the scale reveal ending on a finished infographic · a tracked subject with a "you are here" ring (fits: a letter through the post, a vaccine dose) · the strata cross-section as the story (fits: a mine, a building's floors).

#### Dark tech keynote (`dark-keynote`)
- **Renders with:** Canvas 2D.
- **Essence:** a software launch film where the interface is the star — a near-black gradient stage, a hairline grid, soft cool light, an original UI kit drawn in code, one luminous brand accent reserved for what the product is or does; everything snaps to the grid and lands on the beat with one small overshoot; a problem colour exists only while the problem does; the giant number gets its own screen; shot changes are UI elements expanding or collapsing.
- **Not:** a physical-product glass render, a real-OS screencast, a scanline hologram, a chart film.
- **Camera:** locked extreme close-up on a tiny UI element → one thing alive on a screen · continuous log pull-back keyed per bar → accumulation, a network growing · push-in through a frozen frame → the instant before a commit · whip pull-out in one beat → cause and effect at once, a deploy landing everywhere · log-zoom dive into an element plus a match cut → going inside the detail · half-second inserts expanding from their source → overload, notification storms · near-locked frame while an object turns under a light sweep → the product as hero · slow lateral track across a UI plane → a pipeline · top-down plan over the grid → architecture, permissions · return to an earlier framing → what changed.
- **Native moves:** generated accumulation (UI spawned by rule, hundreds of items — fits: tickets piling up, cloud costs creeping) · the snap grid (everything flies into a grid in one beat — fits: a scheduler filling a week, an audit turning green) · the living element (the cursor or a status dot as protagonist) · freeze (everything stops mid-air at digital-zero silence — fits: a breach caught, the second before "send") · light reveal (only lit pixels turn on — fits: a redesign, a pricing page) · a number from glyph noise, digits locking one per sixteenth (fits: latency cut, a price) · type streams on coloured trails (fits: an inbox triaged, logs routed by severity) · put-away, one part per beat until one element is left (fits: focus mode, "less is more").

#### Living screencast (`living-screencast`)
- **Renders with:** DOM / SVG (the redrawn product UI).
- **Essence:** a product walkthrough that looks like a real screen recording but is fully redrawn UI (every label and shortcut matching the real product), with a low-resolution square-pixel mascot living in the high-resolution interface and acting out what the software does; the cursor is the user, the mascot is the software, never a hand; the mascot stands only on measured top edges of real elements; the camera behaves like screen-recording software (auto-zoom to the cursor, push-ins on clicks).
- **Not:** an invented abstract UI on a black stage, a pixel-art game, a real capture or screenshot.
- **Camera:** push-in to the cursor or caret → "this is where it happens" · slow drift at rest → the app alive while we listen · whip pan between panes with blur → cause here, effect there · push-in with a vignette freeze → the one promise to remember · rack focus between panes → attention moving · pull back to the full window → the whole workflow · follow the mascot along a list → the software working through items · split-window reframe → two sessions at once.
- **Native moves:** match-cut origin (the mascot climbs out of something already in the UI — a logo, a spinner) · the diegetic title as a real UI element the mascot lands on · the moving floor (the mascot rides a caret, an upload bar, a sent message) · time-lapse with an "N×" tag · the spotlight freeze on the badge that holds the promise ("Saved", "Encrypted") · the film changes state (a toggle like dark mode takes over the whole film) · cell division (a new window splits the screen and the mascot) · cursor and mascot as characters (it pokes, the mascot reacts) · karaoke-ball words (the mascot hops word to word as spoken).

#### Sci-fi hologram HUD (`hologram-hud`)
- **Renders with:** Canvas 2D (a projected wireframe).
- **Essence:** an object scanned into a glowing line wireframe above a round projector pad on a near-black stage; target boxes lock onto parts, each opens in a local exploded view along its assembly axis, a leader pulls out and its value rolls from garbage glyphs into the real number; one cold hue plus a warm accent spent only on locked values; three depth layers always present; it may ignite once into a solid Fresnel hologram. A scene style with jobs: a spec walkthrough, a loop screen, a teardown, an upgrade, an assembly order.
- **Not:** a type-driven keynote, a drafting sheet, a product render.
- **Camera:** high three-quarter slow orbit craning down → examination, a scan-in · top-down plan → layout, an inventory · eye-level locked profile → the object in use · push-in then drift → this part matters · whip following the target box → attention jumping to the next part · orbit around a part's own axis → rotors, hinges, lenses · lateral dolly along a long part → a cable run · pull back with a loupe inset → where and what together · crane to eye level → a transformation · turntable 360° → every side · nearly static slow dolly → reading time.
- **Native moves:** scan growth = "this is real data" · target lock = "look here now" (fits: a car's sensors, a laptop's ports) · local explode = "why the number is true" (fits: the layers of a shoe sole, a lens's elements) · rolling digits as the payoff beat (fits: a tolerance in microns, a price) · chip accumulation docked in a rail as reading time · the loupe for two scales at once (fits: a screw inside a watch) · the solid hologram and beam, once (fits: a launch reveal, v2 replacing v1).

### Cartoon and anime

#### 1930s rubber-hose cartoon (`rubber-hose`)
- **Renders with:** Canvas 2D.
- **Essence:** black-and-white hand-inked early-sound-era animation in a 4:3 gate — equal-width tube limbs with no elbows, white four-finger gloves, pie eyes, big shoes, balloon squash and stretch; every object breathes in time with a hot jazz band; soft grey watercolour backgrounds; worn 35 mm print damage; characters own pure white and ink black, backgrounds live in the middle greys.
- **Not:** a 1950s limited-animation colour cartoon, a silent film, a retro filter over modern jointed animation.
- **Camera:** locked stage-wide at eye level → a proscenium, a group number · hard cut to a face close-up → the reaction is the joke · trucking pan beside a runner → a chase, a delivery · medium follow shot → every step is a note · tilt with a fall or rise → gravity as rhythm · slightly high single unbroken shot → the hazard and the answer in one frame · tabletop pan with flat characters before a turning model set → the world is a real place · pull back from a close-up to a packed medium-full → one feeling spreading · iris in or out, which a character can grab → the film is an object.
- **Native moves:** everything breathes on the beat, the whole world dancing at the peak (fits: a factory at shift change, a city waking) · Mickey-mousing (every step a note, a prop becomes an instrument — fits: stairs as a piano, a typewriter as a drum kit) · rubber-hose stretch in one unbroken shot (fits: a long-distance handshake) · transformation mid-motion (fits: an idea turning into a product) · the bouncing-ball singalong (fits: a jingle, a slogan to remember) · the film is a physical object (title cards roll up like shades, the iris is pulled shut — fits: a brand reveal, a "the end?" twist) · the ink bottle (an artist's pen draws the hero, who argues with it — fits: a mascot introduction).

#### 80s cel anime (`cel-anime-80s`)
- **Renders with:** Canvas 2D cels into a WebGL2 shader pass (tape and CRT).
- **Essence:** four layers whose contrast is the look — an airbrushed background plate with a matching emissive plate; flat two-tone cels with hard shadow and highlight shapes and coloured (never black) outlines, stepped at 12 or 8 fps; backlit light glowing through signs and title letters with flares and halation; playback as late-80s videotape on a CRT; a colour model per lighting, never a filter; the protagonist owns one accent.
- **Not:** modern digital anime, moe eyes and hatched blush, vector clip-art with uniform black lines, a film-print pastiche.
- **Camera:** multiplane crane over a tall plate → a world revealed layer by layer · side tracking through 3–4 parallax layers → steady momentum · rear view into a pseudo-3D canyon → speed, pressure ahead · held bust while light bands sweep → speed or tension without animation · insert with bokeh and a sliding highlight → this object matters · extreme close-up on eyes → resolve · slow pan across a painted still → awe, a held breath · radial speed lines with a one-beat freeze → the instant before impact · truck-in through a window or screen → another world, a flashback · locked two-shot with lip flaps → conversation · an earlier composition repainted → what changed.
- **Native moves:** a small flat hero in a huge painted world (fits: a first day at a big company, a lone researcher at an observatory) · stillness as drama (a held close-up or a painted "harmony" still — fits: an exam result, a goodbye) · backlit light (fits: a lantern festival, a screen full of code) · speed grammar (speed lines, looping plates, impact frames — fits: a sprint final, a packet crossing the world) · a light band sweeping a held cel (fits: a night train, a scanner) · a song as an object (tape, radio, jukebox — fits: a band's origin) · tape artefacts as punctuation (fits: a rewind to the past) · a colour-model change for another hour (fits: a day in a shop).

#### Sci-fi sitcom toon (`scifi-toon`)
- **Renders with:** Canvas 2D.
- **Essence:** adult-animation sitcom grammar — uniform thick near-black outlines that boil constantly, flat fills with hard shadow shapes, big white eyes with tiny pupils, elastic parametric mouths; dialogue-driven comedy with reaction close-ups after every absurd image, awkward pauses and a last-second reversal; a tiny mundane goal pursued with absurd sci-fi means; one 3–5 colour palette per world; the travel device is the only thing that glows. Invent the cast, props and device; never echo an existing show.
- **Not:** a kids' cartoon, anime, a vector explainer.
- **Camera:** medium two-shot → the relationship, who reacts how · hard cut to a close-up → an interruption, a face breaking · insert extreme close-up of an object → the absurd detail · reaction close-up → the laugh lives on the face · tight close-up with a short shake on one word → panic · rush zoom into the portal with a swirl wipe → leaving a world · the same framing repeated across worlds → only the world changes · very slow push on a still two-shot → a cold silence · wide with the device and both leads → the whole situation · over-the-shoulder onto a screen → reading bad news · whip pan between two faces → an overlapping argument.
- **Native moves:** parallel worlds (each jump = new palette, cue, creature — fits: versions of a product, careers you could have had) · duo contrast, deadpan vs panic (fits: a veteran and a new hire, an AI and its user) · rule of three → machine-gun (fits: failed prototypes) · the suspiciously normal world (the calm is the joke) · dead-air reversal (a long silence after the twist, then one revealing line — fits: a price reveal, a fine-print clause) · hardware as junk (world-bending tech for a petty chore) · the callback button (the last line repeats the first).

#### Mid-century cartoon (`midcentury-toon`)
- **Renders with:** Canvas 2D.
- **Essence:** 1950s flat colour and limited animation for follow-along films — every fill a separate cel printed a few px off its thin breathing broken ink line, re-jittered on twos; geometric people whose bodies hold still while hands, eyes and mouth do the work; rooms are one colour plane, a floor band and a gapped horizon line; atomic-age ornaments (sparkles, starbursts, kidney shapes); a calm classroom narrator. A scene style with jobs: a set-up guide, a safety card, a recipe card, app onboarding, a store notice — the viewer should be able to do the thing.
- **Not:** a black-and-white 1930s bouncing cartoon, a whiteboard "why" explainer.
- **Camera:** slow push of a few % → collecting the eye · iris through a numbered medallion → the number is the door to the next step · round call-out with a leader → context and detail at once, a hand action · tilt led by a pointing finger → the one action that matters · push into a device and pan along signal rings → pairing, connecting · iris from a round object into a top view → a dial, a lid, a button starting a job · pull back with counter-rotation from a detail to a plan → one lane becomes a pattern · colour-block wipe → turning the manual's page · split frame in two colour blocks → right vs wrong · dead still ≥ 3 s → the frame to screenshot · iris-out onto one object → the closing circle.
- **Native moves:** off-register colour makes an info card hand-made and warm (fits: museum rules, hotel check-in) · limited animation points the eye — the hand is the step, one action per step on a beat (fits: threading a sewing machine, setting a thermostat) · the round call-out as the close-up, its data landing on the action beat (fits: a dosage on a measuring cup) · the numbered medallion that stamps on and opens the next step (fits: a pool's five rules, a pre-flight checklist) · the payoff turns function into ornament (a route or schedule draws itself and reads as a textile — fits: a sprinkler's coverage, a week of medication).

### Games

#### 16-bit pixel RPG (`pixel-rpg`)
- **Renders with:** Canvas 2D (an indexed framebuffer).
- **Essence:** a film that looks, sounds and behaves like a mid-90s console RPG — a 320×180 indexed framebuffer scaled ×6, a limited palette changed by lookup table, ordered dither instead of blends, 20–34 px sprites and 32×32 portraits; the story told in the game's systems (typing dialog boxes as subtitles, menus, battles, save files, item fanfares); colour depth can stand for time; one or two protected colours survive every palette effect as the film's thread.
- **Not:** a lit pixel-sprite diorama with depth and bloom, CRT nostalgia with scanlines, a parody.
- **Camera:** side scroll with parallax → a journey, a timeline · locked frame with UI on one third → a choice, a system speaking · battle side view → conflict as a system (an exam, an illness) · top-down overworld pan → a city, a company map · integer-pixel tilt up something tall → awe · hold while the palette changes → loss or change without motion, nightfall · back view at a threshold → resolve, a departure · mosaic zoom into a thumbnail → a flashback, a save slot.
- **Native moves:** palette collapse or flood (colour depth drops one level per beat, or floods back by dither — fits: a city blackout, burnout and rest) · the protected-colour match cut across eras (fits: an heirloom, a brand colour over decades) · save files as memory (NEW FILE refuses to overwrite — fits: product versions, chapters of a career) · game UI as narration (a greyed-out name, a stat screen — fits: a team member leaving, a budget) · level up with a fanfare (fits: a funding round, learning a language) · the encounter swirl into danger (fits: a deadline, a diagnosis) · the era shift (the same characters redrawn in older hardware — fits: a town's history).

#### Lit pixel-sprite diorama (`hd-2d`)
- **Renders with:** three.js 3D.
- **Essence:** flat stepped pixel sprites standing like paper cut-outs inside a lit, fogged 3D diorama of pixel-textured boxes, always seen from above through a tilt-shift focus band so the world reads as a tabletop model; light is the subject — practicals throw the sprites' shadows, fog and shafts hang in the air, strong bloom and vignette; sprites step while camera, light and focus glide; a small RPG dialogue box with typewriter text.
- **Not:** cubic voxel characters, a flat 2D pixel RPG, a tilt-shift photo of a real miniature.
- **Camera:** very high, very far slow push with the band on one tiny subject → preciousness, the place as a map · medium-high three-quarter near-static drift → two figures on one stage · lateral track leading slightly with blurred foreground → a path through a world · dive low and close as a figure kneels → the toy world turned personal · rising pull-back handing focus from figure to object → the act spreading outward · half orbit round a building → an object from all sides · straight top-down with the band as a strip → a board game, a plan · rack focus between two depths in a locked frame → attention changing hands · return to an earlier framing, changed → what changed.
- **Native moves:** shadows jump when a light is lit (fits: a shop opening at dawn, a server rack powering up) · the carried light as a meter (bright → guttering → relit — fits: a phone battery on a long trip, a heart monitor) · tilt-shift preciousness on one tiny subject (fits: one delivery van in a city, one stall in a night market) · lights popping on one by one across the map (fits: users joining a network, a village getting electricity) · RPG grammar — chapter cards, named dialogue, biomes (fits: onboarding a new employee, a history in eras) · weather passing over the diorama (fits: a market crash, a hard week).

#### Microgame frenzy (`microgame`)
- **Renders with:** Canvas 2D per medium into a WebGL2 shader pass material passes.
- **Essence:** a rapid-fire party-game film — each microgame is a shouted command word, 2.5–4 s, one action and one result; every microgame is drawn in a different visual medium, and the jolt of each switch is the joke and the beat; one fixed home stage with a host, a lives counter and a frame-within-the-frame holds it together; tempo, game length, dwell, command hold and frame rate step up together; the hero keeps two or three silhouette marks through every medium.
- **Not:** a single-style rhythm game show, a style sampler reel without stakes, a montage.
- **Camera:** start inside a game with the command already slamming → the rules explain themselves · pull back out of the game screen → it was one screen on a show · locked frontal home frame → the constant, only the score changes · slot reels of earlier frames → acceleration, a summary · extreme insert on the trigger prop → the start, felt · lights cut to one top spot → the last life · tile flip of past games into a new frame → the past as material for the finale · push into a detail and hold → the viewer notices first · snap back to wide on one beat → release · split screen, two media → rivalry.
- **Native moves:** a style switch per game (each task in the medium that suits it — fits: baking bread step by step, a nurse's day) · the command word as script, subtitle and downbeat (fits: SCAN!, SIGN!) · lives as UI, 3 → 2 → 1 blinking (fits: retries on a driving test) · SPEED UP, everything stepping together (fits: rush hour, dinner service) · failure becomes the solution in the final game (fits: a bug that becomes a feature) · the boss built from earlier media (fits: a final exam, launch day) · the instant replay (fits: a typo that shipped, a goal-line decision).

#### Game show flat (`game-show`)
- **Renders with:** DOM / SVG.
- **Essence:** a rhythm-game variety show in flat vector — toy mascots built from one bean construction with thick ink outlines and hard offset shadows, on candy stripes, dots and sunbursts, one saturated hue per round; everything on one fast tempo grid where every pop, drop, stamp and punch is also a sound event; each round is a repeatable verb ending on a judgement word; telops carry the meaning; shouts, not sentences.
- **Not:** a microgame frenzy with timers and a medium per game, a painted mid-century cartoon, a slow-reveal keynote.
- **Camera:** beat punch of 0.8–5 % decaying in ~0.16 s → the hit felt in the frame · several punches in one bar → the frame breathing with the music · locked frontal wide → the stage as a game board · hard cut on the bar line with a short white flash → a new round · split stage → two sides answering each other · shrink a finished bit into a slot → memory, accumulation · vertical scroll of the set → rising stakes · snap zoom onto one prop → this detail is the joke.
- **Native moves:** rounds with a card on a jingle (fits: recipe steps, a startup's stages) · call-and-response, speeding up from quarters to eighths as the plot (fits: a customer's order and the barista's reply) · the judgement word on the last hit (fits: "Delivered!", "Approved!") · stats as game UI — podium scores, counters racing, bars growing per beat (fits: fundraising progress, downloads) · the remix board (each item gets centre stage, then shrinks into a slot; all slots bounce at the end — fits: a year in review, a release list) · the crowd drop, one per beat with a pitched pip (fits: every member of a club, a dish's ingredients) · the next-level tease · the typewritten report card with a grade stamp (fits: a quarterly review).

### Cinema and eras

#### 1920s silent film (`silent-film`)
- **Renders with:** Canvas 2D into a WebGL2 shader pass (redraw and print).
- **Essence:** an engraved-ink, silver-wash silent film as projected — a flickering, weaving, scratched 4:3 print between velvet curtains; nobody speaks, beats are told by action in wide shots and a few intertitle cards; motion sampled hand-cranked at 16 fps while the print damage changes every frame; deadpan faces, bodies that act; tint and damage are mood controls per section; a cinema piano plays every event; one colour at most.
- **Not:** a noir with hard-shadow mood and voice-over, a sepia filter on modern animation, a pastiche of the most famous tramp.
- **Camera:** locked-off extreme wide → cause and effect seen whole, the wait is the joke · locked full shot → the premise in one frame · tracking with foreground passing → pursuit, a delivery against the clock · iris in or out → attention on one thing · a half-open iris, held → a character sharing a look with the audience · slow motivated push-in → tenderness, a letter read · masked shot (keyhole, binoculars) → point of view, spying · split screen or double exposure → a phone call, a daydream.
- **Native moves:** the chain in one take (A triggers B, B leaves frame, the audience waits, B returns and hits C — fits: a supply chain gone wrong, a rumour spreading) · the near-miss (a hand closes where the object was a frame ago — fits: catching a bus, missing a deal) · the intertitle twist that reframes the next shot (fits: "The machine had other ideas.", a statistic as a punchline) · undercranked chaos, speed and damage rising together (fits: rush hour, a stock crash) · the iris stopping half-way for a glance at the audience · redrawn footage, real video pushed through the ink pass (fits: a company archive, a family film) · the echo gesture repeated by someone else with a new meaning (fits: a handover, a tradition).

#### Liminal found footage (`backrooms`)
- **Renders with:** three.js 3D.
- **Essence:** one continuous first-person 1990s camcorder recording through an empty, familiar-but-wrong interior that repeats — humming flat fluorescent light with no shadows, restrained decay, no people; dread from emptiness, repetition, bureaucratic rules on printed notices and a polite PA voice, and the camera's own machinery failing (focus hunting, auto-exposure lag, tracking tears); the OSD is evidence; exactly one saturated signal colour; no score. Invent every rule and voice; never borrow the internet-folklore names.
- **Not:** a horror film with monsters and stings, a phosphor terminal piece, a ruin.
- **Camera:** walking POV down a corridor → routine, the endless · slow pan off a detail to the space → the space goes on · glance down at the feet → obedience, not looking · crouch and hold on printed text, lens parallel to the page → reading a rule · zoom with a focus hunt into the distance → seeing / not seeing · identical framing after a tear with only the OSD changed → time removed · turn a corner and hold → a threshold · slow silent push-in → the pull of something · backing away while filming → retreat · camera set down, recording alone → abandonment · whip toward a sound, then nothing → expectation denied.
- **Native moves:** autofocus and exposure hunting (something is there only while focus is correct — fits: a shape at the end of a hospital corridor) · tape tracking damage as a cut the universe made (same framing, the clock jumped — fits: a night-watch log) · the OSD as plot (REC, battery, date as evidence — fits: an alibi, a countdown) · rules as text in frame that drift wrong and finally address the viewer (fits: a pool's safety rules, a museum after hours) · emptiness and repetition (the same notice elsewhere, one detail changed — fits: an office after layoffs, an airport at 4 a.m.) · the almost-human figure, small, far, in dead lights.

### Materials and 3D

#### Brick toy (`brick-toy`)
- **Renders with:** three.js 3D (PBR).
- **Essence:** stop-motion interlocking plastic bricks on a real desk, shot like macro toy photography — glossy ABS with clean rectangular softbox highlights, studs on every top face, seams darkened by contact shadow, real household objects as landscape out of focus behind; characters built from bricks step on twos in big held poses while the camera glides; effects (fire, water, light) are bricks too. Never a brand name or the famous minifigure silhouette.
- **Not:** a low-poly floating island, clay or felt stop-motion that deforms, a clean product render of a toy.
- **Camera:** extreme macro on one brick with the room blurred → the toy scale is the world · low angle at character eye level → a tiny character made heroic · high wide over the whole surface → the scale reveal, it was a toy all along · low lonely frame with the character small in a corner → a setback · frontal close-up with hands and brick in focus → a decision, a repair · handheld shake on impact → physical shock · tracking alongside a moving object with its destination ahead → momentum toward a goal · top-down plan → sorting parts, a map · rack focus from a real object to a brick → big world, small maker · orbit around a finished build → pride.
- **Native moves:** snap-together building (pieces fly in on arcs and click home — fits: a first product assembled, a recipe ingredient by ingredient) · break without harm (failure yields spare parts — fits: a pivot, recycling) · toy on a real desk (a keyboard as a city grid, a coffee spill as a flood) · hand-made stop-motion with brick flames and water (fits: a weather report, a volcano demo) · rebuild into something else from the same pieces (fits: one career turning into another) · the scale reveal (fits: a big ambition still small).

#### Paper pop-up book (`paper-popup`)
- **Renders with:** three.js 3D.
- **Essence:** a hardcover pop-up book on a real desk as a stage — flat saturated cut-paper actors with a thick off-white border and a grey cardboard edge perform in front of paper sets that spring up from the page back to front, under real lamp light, casting cut-out-shaped shadows and going soft in real macro lens blur; one hue family per spread so a page turn is a colour change; speech bubbles type on with blips.
- **Not:** a backlit one-colour papercut, a round-modelled 3D cartoon, squishing claymation.
- **Camera:** eye-level macro track with shallow focus → inside the story at the actors' size · pull up to a three-quarter view of the spread → the mechanism, a map · descending dolly from human height → entering the book's scale · push-in on a face → a wish, a fear · reverse shot from inside the book to the blurred room → the world beyond the page is huge · rack focus paper ↔ real object → cause and effect, a real product in a paper story · top-down over the open spread → a board game, two sides of the gutter · locked frame on a pull-tab → the trick is the event · rising crane leaving the book small → aftermath, time passing.
- **Native moves:** the book opens and the world pops up (fits: a project launch, a first school day) · page turn = scene change, old pieces folding as new ones spring (fits: a farm's seasons, a biography's chapters) · pull-tab mechanisms (flipping slats, sliding strips, a hinged door — fits: a forecast, old way/new way) · paper as character, crumpled, torn, taped (fits: a rejected draft becoming the design) · the edge of the page, crossing between paper and the room (fits: a drawing coming true) · the real object plays a part (a lamp as a sun, a mug as a tower) · typed bubbles and ratings (fits: a tutorial, a small victory).

#### Tilt-shift miniature (`tilt-shift`)
- **Renders with:** three.js 3D.
- **Essence:** a photoreal place seen from high above through a tilted lens — only a thin horizontal strip is sharp, the rest melts into blur, so the world reads as a model; saturated sunny model-railway colour with clean blue shadows; time-lapse stutter (the world updates at a low rate and holds each position while the camera stays smooth); a time-lapse clock as the audience's speedometer; a drop to real time is the native event.
- **Not:** a toy or clay render, a game's flat top-down view, drone footage.
- **Camera:** high oblique wide with a very slow slide → a whole system at a glance · the band following one subject across a wide → "this one" · rack of the band between two subjects → a handover, cause and effect · slow push on an intersection or yard → a system heating up · straight top-down, slowly rotating → the world as a board or machine · continuous dive from high to actor height with a speed ramp → the one small thing that matters · the band narrowing to a sliver → intimacy · vertical rise with logarithmic height → letting go, a summary · lateral track along a rail, river or road → a process in order · locked frame across hours → time as the actor.
- **Native moves:** the speed drop ×40 → ×1 on one detail (fits: a proposal on a crowded pier, a child dropping an ice cream) · the band as pointer (fits: a courier through a market, one wrong-way skier) · the god's-eye system, the place as a sequencer (fits: a port unloading, an airport turnaround) · long-exposure light trails at dusk (fits: ferries crossing a bay, lanterns on a river) · the scale reveal until the place becomes a pattern · cloud shadows sweeping the model (fits: a season turning, a mood change).

#### Low-poly isometric island (`lowpoly-island`)
- **Renders with:** three.js 3D.
- **Essence:** a tiny faceted world of flat-shaded primitives (hex tile columns, box buildings with prism roofs, cone and icosahedron trees) under an orthographic isometric camera, floating in a faceted sea with no horizon — distance dissolves into a sky gradient; light, not texture, tells the time as every facet recolours with the sun; every arriving piece bounces in with a note; pastel, low contrast, no outlines, no black.
- **Not:** a voxel game, a tilt-shift photograph of a real place, a smooth-shaded 3D cartoon.
- **Camera:** turntable azimuth sweep → the thing from every side, assembly · pure orthographic zoom → scale without perspective, a world among worlds · elevation change (low widens the sky, high reads as a map) → night and stars, a plan · locked three-quarter wide → the world living on its own · tight close-up on one arrival → the bounce and the splash, a milestone · side angle trailing a mover → a delivery, a route · lateral truck along a row of tiles → steps of a process · time-lapse sun sweep with the camera still → light as the time machine.
- **Native moves:** building is composing (every landing piece plays a note; a later sweep replays them as a melody — fits: a skyline whose floors are notes, a team assembling a product) · procedural growth (tiles rise, floors stack, trees pop — fits: a startup's first year, a reef recovering) · scale by pure zoom (fits: one user among millions, a data centre inside a network) · the turntable around the thing being made · light as clock (fits: a shop's day, a farm's year) · emissive blocks lighting one by one in the dark (fits: a network going live, volunteers joining).

#### Glass product render (`glass-product`)
- **Renders with:** three.js 3D (PBR, transmission).
- **Essence:** a single fictional hero object of clear and frosted glass, metal and light floating in an infinite black studio; long strip lights behind and beside it turn the glass into a thin white outline with dispersion at thick edges; the internals show through like a display case; one accent colour family reserved for light (emission, pulses travelling inside, caustic rings on a black gloss floor); everything slow and precise, every cut, sweep and snap on the beat. Never a real product silhouette, brand or typeface.
- **Not:** a white-cyclorama catalogue shot, a wireframe HUD, a keynote slide.
- **Camera:** a sweep over a dark object with a slow push → contour before content · slow high three-quarter orbit → the whole object in one move · macro rack focus surface → part inside → nothing to hide · side macro orbit → material contrast, a seam · exploded view at ~40° to its axis with an orbit → technical beauty, suspension · straight-on front with a slight push → a declaration, a single number · top-down macro → a pattern at full size · top-down on the floor → the effect leaving the object · low orbit under the object → monument, weight · slow pull-back into negative space → room for type.
- **Native moves:** transparency (the inside is the hero — fits: a watch movement, a capsule's layers) · lensing through a thick dome (fits: a camera module, a water filter) · dispersion as a sweep crosses a thick edge · light travelling inside as energy (fits: a battery filling, a kettle heating) · caustics (an internal pulse becomes a ring spreading over the floor — fits: a speaker's range, a wireless charger's field) · the exploded view snapping shut on a downbeat (fits: a modular backpack, a repairable phone) · frost to clear (fits: a privacy feature, an honest price breakdown).

---

## Part 2 — motion-design styles

Each entry adds **Checkable techniques** (the numbers a render is held to) and a **Beat shape** (the order of a
10-second canonical film), from the prompt's signature section and its creative seed.

#### Flat vector motion graphics (`01-flat-vector`)
- **Essence:** the explainer mainstream — flat geometric characters and scenes, no gradients, no or minimal outline, a bold 5–6 colour brand palette, clean negative space, every element entering and leaving elastically; one continuous shot is its canonical form.
- **Checkable techniques:** overshoot on `cubic-bezier(0.34,1.56,0.64,1)`; entrances in three phases — anticipation, overshoot, settle; staggered entrances 2–4 frames apart and only one hero moving at a time; ~10 % squash and stretch on moves; limbs rigged by anchor rotation; transitions are a shape wipe or an element flying out and carrying the cut.
- **Beat shape (10 s):** a single shape drops with anticipation → it becomes part of a world that pops up piece by piece → a push into one detail where a character reacts → a notification expands to fill the frame as the wipe → everything collapses into a lockup, ~1 s held with micro-motion.
- **Renders with:** DOM / SVG with a tween library (shape morphs, custom bounce); sub-frame motion blur on fast moves.

#### Line art (`02-line-art`)
- **Essence:** one thin monochrome line is the only drawing language — it draws itself on, extends, turns and becomes the next figure, so the whole film is one stroke; large negative space; a line-to-fill moment; at home in luxury, finance and architecture brand films.
- **Checkable techniques:** stroke draw-on (`stroke-dashoffset` over the path length); constant line width 2–4 px for the whole film with round caps; draw speed eases into corners on `cubic-bezier(0.65,0,0.35,1)`; the tail of each figure is the start of the next; line-to-fill — the outline's own path fills from an anchor; older segments dim (~35 %) as the camera follows the tip; the end dollies out to the whole drawing composed as a poster.
- **Beat shape:** a seed → a sapling → its branches become a building's structural lines → a skyline → the horizon loops into a monogram → the monogram fills → a thin tracked serif wordmark.
- **Renders with:** DOM / SVG paths with a virtual camera following the pen tip.

#### Isometric 2.5D (`03-isometric`)
- **Essence:** a miniature world (a small city, an office slice, a server room) in true isometric projection — no vanishing point, everything to scale, buildings that grow, a camera that only slides in parallel; dense information that stays friendly; the standard for architecture and app-feature animations.
- **Checkable techniques:** faces built by scale-shear-rotate (vertical 86.6 %, skew ±30°, rotate ∓30°) or a true orthographic camera at 35.264° elevation and 45° azimuth — ground axes at 30° (slope ≈ 0.577); z-order = screen y; the upstream also asks movement to keep a 2:1 pixel slope, which is the pixel-art approximation (26.565°, slope 0.5), not true isometric — choose one projection and hold it; a building grows base first, walls scaleY from 0 with overshoot, the roof lands 2–3 frames later; camera moves are group translations with no rotation and parallax at 1 : 0.8 : 0.6 for front, middle and back.
- **Beat shape:** ground tiles drop in as a wave from the centre → buildings grow, trees pop, windows light in sequence → life loops (cars, a train, drones carrying packets, data streams) under a parallel slide → a pull-back reveals the island floating in a pastel void, the title set on the isometric plane.
- **Renders with:** three.js 3D (an orthographic camera, soft shadows, AO), or DOM / SVG faces built by the scale-shear-rotate formula.

#### 3D render, soft CGI (`04-3d-render`)
- **Essence:** physically based material motion design — soft-touch candy plastic, glass, metal, cloth — with cloner arrays and physics, under soft studio light and shallow depth of field at film frame rate; the product-ident and launch-film mainstream.
- **Checkable techniques:** a cloner field animated by an effector wave; the material trio — subsurface (gummy), glossy plastic, frosted glass or chrome — with AO and HDRI three-point light; long-tail easing (80 % of the travel in the first 20 % of the time) with motion blur; 24 fps and an f/1.8-like depth of field, against the 30 fps snap of the 2D styles; a hero object with a damped-spring jiggle that collides with and displaces the field; a clean hero composition held ~1 s.
- **Beat shape:** the field ripples → the hero drops in and jiggles → it collides with and displaces the field → the camera settles on the hero frame.
- **Renders with:** an offline 3D renderer (a scripted scene to a PNG sequence), with an optional HTML type pass on top — outside our HyperFrames lane.

#### Cel animation and line boil (`05-cel-boil`)
- **Essence:** hand-drawn frame-by-frame texture, or hand-drawn cel effects over vector animation; the signature is the line boil — lines jitter every few frames so the picture breathes; smear frames, hand-drawn smoke, splashes and speed lines; a paper ground; the anti-digital-polish lever.
- **Checkable techniques:** on twos at 24 fps for most action, on ones for fast action, on threes for a hold; boil = 3–4 slightly different line drawings cycled every 2 frames (or a displacement re-seeded every 2 frames and posterised to 12 fps); a smear frame stretches the moving object 150–300 % for one frame; fills slightly off-register; paper grain multiplied at 10–15 %; a 3–4 colour palette.
- **Beat shape:** a fast action on ones with a smear → a character born from it acts on twos → it bursts into cel effects (smoke, sparks, speed lines) → the effects re-form into hand-lettered title that keeps boiling on threes through the hold.
- **Renders with:** Canvas 2D (a variable-width brush from a centreline and pressure, boil variants cycled, a paper multiply).

#### Collage and cut-out (`06-collage`)
- **Essence:** retro-surreal reassembly of cut-out old photographs, newspaper and torn paper — rough white scissor edges, halftone, newsprint texture, mismatched proportions, a mouth that flaps on its own, stop-motion stepping; the lineage of absurdist sketch-comedy cut-outs and constructivist posters, now merged with the editorial magazine look.
- **Checkable techniques:** cut-outs carry a 2–4 px white edge plus a halftone filter; puppet joints pivot at shoulder, elbow and jaw, the mouth swaps between two or three drawings; motion deliberately stepped to 12 fps or even 6 fps with ±2 px hand-placement jitter; layer order paper ground → big colour shapes → photo cut-outs → doodles and tape → grain; transitions are a hand slapping an element on or a whole-page paper flip.
- **Beat shape:** a portrait cut-out whose head flips open like a lid → a world spills out of it → hands slap elements onto the page → a torn-paper or page-flip transition to the end card with bold diagonal type.
- **Renders with:** DOM / Canvas 2D with matted cut-outs, CSS/SVG edge and halftone filters, stepped on a 12 fps grid.

#### Liquid motion (`07-liquid`)
- **Essence:** shapes behave like liquid — they flow, stretch into necks, drip and fuse; a transition is a splash of paint across the screen, a logo coalesces from one drop; organic, satisfying, high energy; nothing is ever a straight line.
- **Checkable techniques:** a liquid wipe's wavy front carries 3–5 phase-offset bulges; metaball fusion by a ≥ 20 px blur and a tight alpha threshold (or SDF smooth-min); stretch → snap → 2–3 frames of rebound on each end; flung easing `cubic-bezier(0.22,1,0.36,1)`, never uniform; secondary droplets follow 2–3 frames late and squash flat on landing; a specular highlight and fresnel rim so it reads as thick liquid, not flat blobs.
- **Beat shape:** droplets fall and splash → blobs merge with necks and rebound → a wave floods the frame as the transition → the liquid coalesces into a wordmark → a last drip falls and ripples; hold.
- **Renders with:** a WebGL2 shader pass (2D SDF metaballs with lighting from the field gradient, a text SDF for the logo).

#### Shape morph (`08-morph`)
- **Essence:** one shape becomes another without a break — a phone into a map pin, a cup into a sunset; the core grammar of visual storytelling and the hardest-earned part of keynote motion.
- **Checkable techniques:** both paths share a vertex count and a matched first vertex, or the morph knots; a complex A → B passes through a simple intermediate (a circle or capsule), 8–12 frames each side; 10–15 % squash and stretch plus a slight rotation through the morph; fastest mid-move on `cubic-bezier(0.7,0,0.3,1)` with 3-frame cushions at both ends; sub-parts morph in sync; every morph's midpoint still is checked for tangles; the background colour field changes with each morph by a clean wipe.
- **Beat shape:** a chain of 6–8 meaningful icons, one per beat, ending in an invented brand mark with its wordmark.
- **Renders with:** DOM / SVG with a vertex-matching morph library.

#### Bauhaus geometric (`09-bauhaus`)
- **Essence:** circles, triangles and rectangles making exact moves on a strict grid in red, yellow, blue and black on cream — mechanical, rational order that fits a beat naturally; the language of the kinetic poster.
- **Checkable techniques:** every move is a whole number of grid modules and every landing is on a grid line; easing restrained to quad in-out or linear with no overshoot (the mechanism is the point); one action per beat — a quarter circle turns 90° about a corner, a semicircle slides one module, a triangle flips, a square splits; rotation pivots alternate between own centre, a corner and frame centre; a phase-offset cascade across the grid on the drop; a slight print misregistration allowed.
- **Beat shape:** grid lines draw and the first shape lands → the composition assembles beat by beat into a poster → a phase-shifted wave runs across the grid → it freezes into a finished poster with Swiss typography.
- **Renders with:** DOM / SVG or Canvas 2D on a modular grid driven by a beat grid.

#### 80s synthwave, VHS and Y2K (`10-synthwave`)
- **Essence:** a whole-era media quotation — synthwave's neon perspective grid, striped sunset sun and chrome lettering; VHS's scanlines, colour offsets and tape noise; Y2K's liquid chrome, acid green and purple, skeuomorphic system windows and low-fi 3D.
- **Checkable techniques:** a one-point perspective grid scrolling toward the camera; a sunset disc of stacked gradient bands with horizontal cut-outs; a double glow (a tight ~4 px core plus a wide ~30 px low-opacity halo); chrome type from a high-contrast multi-stop metal gradient with a bevel highlight and a glint sweep; the VHS chain — RGB channels offset 1–2 px, 2 px scanlines at 10 % black, 1–2 random glitch skips a second, a rounded 4:3 mask; Y2K pop-up windows, cursor clicks and window drags as narrative; a deliberately unstable frame rate (15 fps passages, two-frame reverses for tape stutter).
- **Beat shape:** tracking noise and a PLAY OSD → a low flight over the grid as the sun rises → the chrome title slams in with a flare → a neon script word writes on with flicker → a sustained ride ending on the hero frame.
- **Renders with:** a WebGL shader pass (grid, sun, mountains) with Canvas 2D chrome text and a VHS pass.

#### Aurora gradient and glassmorphism (`12-aurora-glass`)
- **Essence:** large blurred colour blobs drifting slowly as a mesh-gradient ground, frosted translucent glass cards floating above, 1 px highlight edges, low-contrast adjacent hues, a slow breathing rhythm — the default look of 2024–26 AI-product launches: slow, translucent, expensive.
- **Checkable techniques:** 3–5 solid circles blurred 80–150 px, each on a 20–40 s bezier loop; glass card = a 20–40 px backdrop blur, a 5–10 % white fill, a 1 px 30 % white inner stroke and a large radius; 2–3 adjacent hues only (complementary pairs turn muddy), bright blobs on a dark base; 3–5 % noise dither against banding; near-linear or sine easing everywhere, text entering by opacity and an 8 px rise only — a fast move breaks the look at once.
- **Beat shape:** blobs drift → cards float in with parallax and a slight tilt, their micro-UI animating → a refractive lens with a dispersive rim glides across and magnifies the scene → the title in a light sans.
- **Renders with:** a WebGL shader pass (mesh gradient, refraction with dispersion) under DOM / CSS backdrop-filter cards.

#### Variety-show kinetic captions, hanazi (`18-hanazi`)
- **Essence:** emotional decorative captions from TV variety post-production — multi-layer-stroked rounded heavy type with elastic entrances, colour and shape following the person's emotion, each landing on a sound hit; now the general packaging language of vlogs, pet videos, interviews and comedy re-edits, over footage.
- **Checkable techniques:** three type layers — fill, a thick white stroke, a coloured outer stroke or drop shadow (stacked text-shadows or SVG stroke); entrance overshoot scale 0 → 1.15 → 1.0 in about 8 frames, or a per-character bounce staggered 2 frames; emotion matching — a slanted hand face for a wisecrack, a radial burst frame with speed lines for shock, a sweat drop for embarrassment; the caption lands 2–3 frames after the laugh or the sound (later than the voice reads more natural); a gentle wiggle on any caption that holds; high-saturation pink, yellow and cyan with white strokes, each moment with its own decoration (sparkles, a stamp, bouncing question marks).
- **Beat shape:** footage (Ken Burns, a slight handheld shake, punch-ins on the moments) with captions popping on the beats: a title, a reaction, a shock in a burst frame, a whispered aside, a stamp.
- **Renders with:** DOM / SVG caption components over a footage layer — our native lane.

#### Bold-outline sticker explainer (`19-paperclip`)
- **Essence:** the knowledge-video standard from Chinese explainer channels — real photographs cut out with a thick white outline into "stickers", laid with flat icons and exact data charts on one giant canvas that a camera pans and zooms across; a calm blue-grey or off-white ground, 2–3 colours and one accent, equal-weight sans; very dense, one new visual per sentence.
- **Checkable techniques:** every photo matted with an 8–12 px white outline so mixed sources read as one set; one huge canvas (e.g. 6000 × 3000 px) under a camera transform on long eases, one continuous move linking every point; charts that grow — bars to scale, count-ups, routes drawing; every narration sentence introduces a new element; strict alignment.
- **Beat shape:** a sticker object → its exploded parts with leader labels → a grid of tiles lighting up → a bar chart counting up to a number → a map with routes drawing → a pull-out to a heavy-sans title card with one huge number and a small caption.
- **Renders with:** DOM / Canvas 2D on one large canvas with a camera transform, SVG charts.

#### Pixel art, 8-bit (`20-pixel`)
- **Essence:** big hard-edged pixels, a limited palette, low-frame-rate sprite animation, dithered gradients, an optional CRT pass — the retro game look of indie-game channels, chiptune videos and nostalgia marketing.
- **Checkable techniques:** an internal raster such as 320 × 180, scaled by a whole number with nearest-neighbour (no antialiased edges); an 8–32 colour palette; sprite cycles of 6–8 frames for a run and 2–4 for breathing at 8–12 fps; stepped timing, never smooth easing on sprites; parallax layers moving by whole pixels; dithered sky gradients; any CRT pass (scanlines, slight barrel, phosphor glow) must not blur pixels.
- **Beat shape:** an attract sequence — the hero runs, jumps, collects, bops an enemy while the palette shifts day → sunset → a chest opens with a light burst → a typing dialogue box → a chunky logo drops with a shine sweep.
- **Renders with:** Canvas 2D at the internal raster, integer-scaled.

#### Cyberpunk HUD / fictional UI (`22-hud`)
- **Essence:** a sci-fi film or game interface as packaging — cyan and orange neon line work, target lock brackets and crosshairs, radar and ring sweeps, monospace data streams and typewriter text, hex grids and glow; the default "tech" skin of gadget reviews, game edits and aerospace explainers.
- **Checkable techniques:** line work draws on (dash-offset), elements unfolding in staggered hierarchical order; a conic radar sector rotating with blinking blips; numbers jump randomly for 3–5 frames, then land on the true value; typewriter lines with a blinking cursor; lock brackets shrink from 1.4 → 1.0 onto the target, fast out, slow in; one alert state flips the whole palette to orange; glow, slight chromatic aberration and scanlines over everything, micro-glitches restrained.
- **Beat shape:** lines draw on in hierarchy → the data comes alive → a target is found → the brackets lock → everything flips to the alert colour with "locked" and a coordinate.
- **Renders with:** DOM / SVG and Canvas 2D layers with a three.js wireframe at the centre and a glow-and-scanline pass.

---

## Licence notices

The entries above are derived from the two libraries named under Provenance, each under the MIT License:

```text
MIT License

Copyright (c) 2026 LemoLab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

```text
MIT License

Copyright (c) 2026 Vincentwei1021

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
