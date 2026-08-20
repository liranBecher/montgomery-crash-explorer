# Visualization decisions

This record captures the major data, design, and interaction decisions for the
Safety Hotspots, Fire & Rescue Proximity, and Police Breathalyzers tabs.

## Record scope and provenance

- Reconciled on 2026-08-20 against committed implementation through `387b73a`.
- The review includes the agent-host session checkpoint ranges
  `beb043c..23722dc`, `f562e8e..ba949d8`, and `e8d427a..9bb1792`, plus the
  subsequent named implementation commits through the reconciliation point.
- This is a decision record rather than a commit-by-commit changelog: session
  work is recorded below when it changed the shipped data meaning, visual
  encoding, interaction, layout, or analytical caveats.

## Shared application structure and filters

- The application now has exactly three connected analysis tabs: **Safety
  Hotspots**, **Fire & Rescue Proximity**, and **Police Breathalyzers**. The
  former Vehicles & Injuries prototype and its documentation references were
  removed so the submitted system contains only implemented, data-backed views.
- A persistent shared sidebar provides the **From** and **To** date filters used
  by all three tabs. This replaces duplicate per-tab date controls and keeps the
  active time window consistent when moving between analyses.
- The default shared date window is the latest five years, bounded by the
  available crash data.
- A municipality/area filter was briefly introduced but removed because the
  incident municipality field is too incomplete to serve as a reliable shared
  analysis dimension. The shared filter contract therefore currently carries
  only the date range.
- **Reset filters** restores the default date window and clears active map,
  station, and weekday/hour selections. Chart selections remain local to the
  analysis where they are meaningful; only the date subset is shared across
  tabs.

## Shared map language and semantic zoom

### Common visual system

- The three crash maps are intended to behave as one mapping system rather than
  three independently designed visuals.
- They use the same countywide default viewport: latitude `39.12`, longitude
  `-77.13`, zoom `8.6`.
- The countywide view uses fixed 0.01-degree aggregate grid cells so dense crash
  patterns remain readable and the same spatial unit is used across analyses.
- Aggregate cells are rendered as geographic **grid tiles** with a `PolygonLayer`.
  Tile area represents the fixed spatial aggregation unit and does not encode a
  quantitative value; **fill color alone** carries the active map measure.
- The maps share the same light CARTO basemap, white tile outline, warm
  sequential low-to-high palette, hover highlighting, and selected-cell
  treatment.
- The warm color scale is recalculated whenever the active filters change. The
  lowest visible value is assigned the light end of the palette and the highest
  visible value the dark end, with the other values distributed between them.
  This improves contrast within the current result set, especially when a
  filter leaves a narrow range of counts.
- Because the scale's minimum and maximum can change, color is only comparable
  within the current map state. A dark-red tile might represent 12 crashes in
  one filter state and 80 in another; identical shades do not guarantee
  identical counts across tabs or filter states. The legend updates to show the
  current numeric range, so users should consult it after changing a filter
  rather than comparing colors from memory.
- The selected tile is removed from the hoverable base layer and redrawn as a
  separate, non-pickable polygon. Its fill becomes nearly transparent while its
  outline preserves the tile's quantitative color, keeping the selection clear
  without replacing the encoded value with an unrelated selection color.
- Legends use the same visual vocabulary for the quantitative gradient and
  selected grid cell. Domain-specific symbols, such as Fire & Rescue station
  crosses and station-radius context, are added without changing the base map
  language.

### Standard crash-cell semantic zoom

- Selecting a crash grid cell is the standard semantic zoom interaction across
  Safety Hotspots, Fire & Rescue Proximity, and Police Breathalyzers.
- In the default state, only aggregate grid tiles are shown and the map stays at
  the countywide viewport.
- Selecting a cell recentres the map on that cell, zooms to street level
  (`zoom=13`), keeps the selected-cell outline and aggregate context, and reveals
  the individual crash coordinates belonging to that selected cell.
- Individual crashes use small circular markers with a subtle white outline,
  fixed pixel sizing, sufficient opacity for overlap, and pickable tooltips.
  They intentionally do not reuse the aggregate-tile style.
- Incident-marker radius is expressed as the literal `"pixels"` deck.gl unit so
  point size remains stable while zooming and cannot expand into a large
  geographic-radius disk.
- Tooltip fields are normalized so aggregate cells and individual incidents can
  share the deck-level tooltip structure while still exposing tab-specific
  details such as date/time, severity, road, or alcohol status.
- Clearing a cell selection removes the incident layer and restores the
  countywide aggregate viewport. If filtering makes the selected cell invalid,
  the selection and zoom are also reset.
- A cell selected through a linked visualization should trigger the same map
  drill-down behavior as a cell selected directly on the map.
- Map selections use a fresh Streamlit map generation when the active semantic
  level changes so the new viewport is actually applied rather than preserving
  the previous client-side camera state.
- Fire & Rescue station selection remains a separate semantic zoom mode and
  takes priority over cell zoom when a station is selected.

## Safety Hotspots

### Purpose and scope

- The tab asks where, when, and under which recorded conditions crashes
  concentrate.
- It uses the same 0.01-degree geographic cells as the other crash maps so the
  spatial unit and interaction language stay consistent.
- Users can switch between all classified crashes and a focused
  suspected-serious/fatal mode.
- The shared sidebar supplies the active date range; the incomplete 2026 source
  period is labelled wherever time comparisons may be interpreted.
- Weather, Surface, and Light can also be filtered locally through the Safety
  conditions popover. A dedicated **Clear all condition filters** action resets
  these local category filters without changing the shared date range.

### Map and semantic drill-down

- Countywide crash concentrations are shown as 0.01-degree grid tiles, with
  color encoding crash count per tile.
- Selecting a grid cell uses the shared semantic zoom behavior: the map moves to
  street level, retains the selected-cell context, and reveals the exact crash
  coordinates inside that cell.
- Clearing the selection returns to the countywide aggregate view.
- The selected-cell detail summarizes crash count, county share,
  suspected-serious/fatal count, dominant route type, and common roads.

### Condition fingerprint

- The hotspot fingerprint compares the selected cell with the active county
  **average** rather than presenting raw local percentages without context.
- The comparison uses grouped condition families for Weather, Surface, and
  Light.
- Categories are ordered by county prevalence so the selected hotspot and the
  county average remain directly comparable.
- Small selected samples are explicitly cautioned because percentages can be
  unstable when the hotspot contains few crashes.
- The fingerprint uses a compact ridge-style SVG with one ridge per condition
  family. Similarity is encoded as **colored stroke progress along a fixed ridge
  path**, rather than by changing the ridge's overall thickness or filling the
  whole shape with variable opacity.
- The full ridge path acts as the reference extent; the colored portion shows
  similarity to the active county pattern, with a legend explicitly explaining
  that encoding.
- Weather, Surface, and Light retain distinct family accents so the three ridges
  can be identified quickly without competing with the map's quantitative
  color scale.
- The fingerprint is positioned beside the condition comparison charts to keep
  the main Safety analysis visible with minimal scrolling.

### Linked crash timing

- A weekday-by-hour heatmap shows the temporal distribution for the county or
  the selected hotspot.
- Selecting a weekday-hour cell filters the map and condition fingerprint to
  that time window.
- Selecting a map cell changes the heatmap geography to that selected cell.
- Double-clicking the timing heatmap clears its time selection, while the main
  clear action resets both the spatial and time selections.
- The timing heatmap uses the shared blue-to-purple sequential heatmap palette,
  keeping ordered magnitude perceptually distinct from the warm map palette.

### Analytical cautions

- The hotspot view describes recorded crash concentrations and conditions. It
  does not estimate underlying traffic, pedestrian, or cyclist exposure and
  does not establish causal risk.
- The county comparison includes the selected cell; it is a contextual average
  rather than a statistically independent control group.

## Fire & Rescue Proximity

### Scope and data meaning

- The tab is named **Fire & Rescue Proximity**.
- It uses mapped fire-station locations to examine **road-network proximity**
  to crash demand. It does not claim response times, dispatch coverage,
  staffing, service areas, or operational performance.
- The mapped station layer contains 37 usable stations. Station 27 / Public
  Safety Training Academy is excluded because it has no usable coordinates.
- The analysis is based on 0.01-degree geographic cells for the countywide
  overview, with exact crash locations revealed only during semantic
  drill-down.
- The main distance measure is shortest drivable OpenStreetMap distance in
  kilometres. Haversine straight-line distance remains secondary context and
  powers the station-radius comparison and map circle.
- Road distances use a cached, directed OpenStreetMap `drive_service` graph.
  Crashes and stations are snapped to its largest strongly connected component,
  point-to-node connector distances are included, and shortest paths respect
  one-way directionality.
- The processed crash table stores the road-nearest station, road distance, and
  crash-to-network snap distance. All 122,367 crashes route successfully; the
  maximum station snap is 71.3 metres and the maximum crash snap is 929.1
  metres. Snap distance is retained so this approximation remains auditable.

### Severity and filtering

- The original demand analysis foregrounds suspected-serious and fatal
  crashes; the processed data retains the broader injury classifications for
  flexibility.
- The public severity control offers Fatal Injury, Suspected Serious Injury,
  and Possible Injury. Minor and no-apparent-injury options are intentionally
  omitted from the interface.
- The map has a minimum cell sample control, with a default of three crashes.
- The shared sidebar date range applies to Fire & Rescue; daypart and severity
  remain local filters because they are specific to this analysis.
- The incomplete 2026 source period is labelled wherever time comparisons may
  be interpreted.

### Map and legends

- Crash demand is mapped as the same fixed 0.01-degree grid tiles used in the
  other tabs. **Color alone** encodes the filtered crash count.
- Fire stations use a rescue-cross marker rather than a grid tile or crash
  point, so they are clearly distinguishable from crash-demand cells.
- The map includes an explicit legend for crash-count color, rescue crosses,
  selected cells, and the selected-station radius/incident context.
- Selecting a station displays its adjustable straight-line radius and the
  filtered crashes inside it. The radius is a proximity aid, not a coverage
  claim.
- Selecting a crash cell follows the shared semantic drill-down: the map zooms
  to the cell, keeps aggregate context, and shows the underlying filtered crash
  coordinates. Clearing the selection restores the aggregate county overview.
- Fire-station markers remain visible during the cell drill-down so exact
  incidents retain their proximity context.
- Station selection remains independent from cell selection. When a station is
  selected, the station-specific viewport/radius behavior takes priority over
  the regular cell semantic zoom.

### Companion views

- The scatterplot compares median crash-to-nearest-station **road distance**
  within each grid cell (x) with filtered crash count (y), with median
  straight-line distance retained in the tooltip as secondary context. It
  intentionally avoids an arbitrary composite "gap score."
- Median reference lines support quadrant-style comparison while keeping the
  two underlying measures explicit.
- Map-cell and scatterplot tooltips also show an **approximate apparatus travel
  time** calculated from median road distance with the RAND/ISO model
  `T = 0.65 + 1.7D`, where `T` is minutes and `D` is road distance in miles.
  The model and assumptions are sourced from the [University of Tennessee
  MTAS travel-time reference](https://www.mtas.tennessee.edu/reference/estimating-travel-time-fire-apparatus).
- A teal long-dashed vertical line marks the modelled four-minute point at
  approximately **3.17 km** on the scatterplot's road-distance axis. It is
  visually distinct from the grey median reference lines and is presented as
  context only, not as a cap, pass/fail threshold, or good/bad classification.
- The station bar chart ranks stations by the number of filtered crashes inside
  the selected radius. It supports **Most active** and **Least active** views.
- Each station is counted independently in the bar chart, so a crash can occur
  in more than one station radius; this is disclosed in the chart caption.
- [NFPA 1710](https://www.nfpa.org/api/files?path=%2Ffiles%2FAboutTheCodes%2F1710%2F1710_A2019_FAC_AAA_FRReport.pdf)
  includes four-minute first-responder travel-time objectives in relevant fire
  and EMS contexts. The interface cites this only as planning context; it does
  not claim that every recorded crash is governed by that objective.

### Interaction decisions

- Map selection details appear in a compact overlay at the map's bottom-left,
  instead of shifting the charts below the map.
- The map header contains the clear-selection action so the reset control stays
  visually attached to the visualization it affects.
- Clicking a station bar selects that station and recentres the map at a
  deliberately moderate zoom level, keeping nearby stations and context in
  view.
- Hovering station bars is tooltip-only. It does not update map state or
  trigger a rerender.
- Clicking an empty area of the map clears both station and grid-cell
  selections.
- Only the linked visualization block rerenders on map, scatterplot, or bar
  selection; the tab header and filter controls remain in place.
- The cached Fire & Rescue loader carries an explicit data-schema version and
  validates the road-distance field. This prevents a running Streamlit process
  from reusing a pre-road-distance cached DataFrame after the Parquet schema is
  upgraded.

### Analytical cautions

- Road-network distance remains the primary geographic measure. The derived
  RAND/ISO value is a modelled estimate, not observed response time, and does
  not include live traffic, apparatus restrictions, dispatch decisions,
  staffing, turnout, availability, or actual emergency response performance.
- The Haversine station-radius view remains intentionally straight-line and is
  not interchangeable with the road-distance scatterplot measure.
- Geographic proximity cannot establish whether stations are operationally
  redundant or "too close for no reason." That conclusion would require
  information such as apparatus, staffing, service areas, and dispatch data.
- Municipality is not used as a primary analysis dimension because it is
  largely missing in the incident data.

## Police Breathalyzers

### Purpose and terminology

- The tab supports county and police exploration of where and when previously
  recorded alcohol-related crashes occurred, to inform possible breathalyzer
  placement and timing.
- The analysis is descriptive. A police crash record is not a BAC test, a
  causal finding, proof of impairment, or an enforcement recommendation.
- The interface uses **alcohol-related crashes**, not **drunk drivers**, because
  the source includes confirmed, contributing, suspected, and combined-
  substance descriptions with different levels of certainty.

### Alcohol classification and preprocessing

- Source substance labels are normalized into Alcohol present/contributed,
  Suspected alcohol use, Combined substance, No alcohol indication, and
  Unknown.
- The inclusive `alcohol_related` definition combines the first three positive
  categories so the many source descriptions of actual or possible alcohol
  involvement are not fragmented across the analysis.
- Explicit negative labels such as not suspected and none detected are not
  alcohol-related. Drug-only and medication-only labels are also excluded.
- Missing, unknown, N/A, and unrecognized labels remain Unknown rather than
  being assumed positive or negative.
- Original combined source labels are retained for auditability.
- Only valid Montgomery-area coordinates enter the mapped datasets. Stable
  0.01-degree cells support countywide aggregation, while the crash-level
  output retains exact latitude and longitude for drill-down.

### Measures and filtering

- Users can switch between alcohol-related crash count and alcohol-related
  share. Share uses all geocoded crashes in the same active geography and time
  window as its denominator.
- The shared sidebar supplies the date range. Included alcohol categories,
  measure, and minimum all-crashes-per-cell remain local controls.
- The minimum all-crashes-per-cell control is a reliability/context filter on
  the denominator, not a minimum number of alcohol-related crashes.
- When a weekday-hour heatmap cell is selected, the map minimum automatically
  drops to one crash per cell. A narrow time slice should not disappear merely
  because it no longer meets the broader countywide sample threshold.

### Final map-measure decision

- The final map should use **alcohol-related crash count as its only color
  measure**; the current count/share switch is therefore slated for removal.
- A share map can be misleading when denominators are small. For example, one
  alcohol-related crash among one total crash produces a 100% share and could
  appear more important than a cell containing many more alcohol-related
  crashes among a larger number of total crashes.
- The map's primary question is where recorded alcohol-related crashes
  concentrate, so color should answer that question directly: a darker cell
  means more alcohol-related crashes. Total crash count and alcohol-related
  share remain useful supporting context in the tooltip but do not control the
  tile color.
- Cells with zero selected alcohol-related crashes are intentionally omitted
  from this count map to avoid adding visually irrelevant tiles. This is
  appropriate for a concentration map; it would not be appropriate for a share
  map, where a valid 0% cell is meaningful comparative evidence.
- If a share view is revisited later, it should retain eligible 0% cells, use a
  clearly differentiated title and legend, and require a stronger denominator
  threshold (approximately 10–20 total crashes) so sparse cells do not dominate
  the visual interpretation.

### Map and semantic drill-down

- The countywide map aggregates crashes into the same fixed grid tiles used by
  the other tabs to keep dense patterns readable. Color is the single
  quantitative tile encoding.
- Selecting an aggregate cell follows the shared semantic zoom behavior: the
  map recentres at street level, retains the selected-cell/aggregate context,
  and overlays the exact coordinates of the underlying active alcohol-related
  crashes. Clearing the selection restores the countywide aggregation.
- Exact coordinates identify recorded crash locations, but they still do not
  by themselves identify a safe, legal, or operationally suitable checkpoint
  position.

### Linked time and place exploration

- The weekday-by-hour view reveals recurring timing patterns and supports a
  selected time window that filters the map.
- The timing visualization uses a **radial heatmap** because hour of day is
  periodic: 23:00 and 00:00 are adjacent observations rather than unrelated
  endpoints. Hours are mapped around the circle and weekdays are mapped to
  concentric rings, aligning the same hour across all seven days on one radial
  spoke.
- This layout is intended primarily for detecting recurring daily patterns,
  quiet periods, and broad similarities across weekdays. It also provides a
  visually distinct time view while remaining consistent with course guidance
  that cyclical time may be represented circularly.
- The radial layout is a deliberate exception to the usual left-to-right rule
  for linear time axes. It preserves the daily cycle, but it does not make
  Sunday and Monday spatially adjacent because weekdays are concentric rings.
- Color is the quantitative encoding; ring area is not intended to encode
  magnitude. Outer-ring cells are physically larger than inner-ring cells, so
  the chart is not used for precise area comparison. Tooltips expose the exact
  weekday, hour, alcohol-related count, total crash count, and share on demand.
- Weekday abbreviations are centred on their rings, while hour labels sit just
  inside the outer ring to keep the left-side labels from being clipped. Inline
  help and a caption state the ring and hour mapping rather than relying on
  users to infer the radial structure.
- Selecting a map cell filters the radial heatmap to that geography. Selecting
  a radial heatmap cell filters the map to that weekday and hour.
- A single clear action resets both spatial and time selections, and the
  summary text always states whether the current context is countywide or a
  selected cell and time.
- The clear action sits beside the map heading so the reset remains attached to
  the linked view it affects without consuming a separate full-width row.
- The time sequence runs from 06:00 through 05:00 so daytime/evening/night
  patterns read as one continuous daily cycle rather than splitting the night
  at midnight.

### Analytical cautions

- Historical incident concentration can help prioritize further operational
  review, but deployment decisions also require traffic volume, road safety,
  legal constraints, staffing, jurisdiction, and current conditions.
- Counts show incident volume; shares show relative alcohol involvement among
  recorded crashes. Neither measure estimates the prevalence of impaired
  driving in the general traffic population.
