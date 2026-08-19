# Visualization decisions

This record captures the major data, design, and interaction decisions for the
Safety Hotspots, Fire & Rescue Proximity, and Police Breathalyzers tabs.

## Shared map language and semantic zoom

### Common visual system

- The three crash maps are intended to behave as one mapping system rather than
  three independently designed visuals.
- They use the same countywide default viewport: latitude `39.12`, longitude
  `-77.13`, zoom `8.6`.
- The countywide view uses 0.01-degree aggregate grid cells so dense crash
  patterns remain readable.
- Aggregate cells use uniform-size circles. Marker size does not encode a
  quantitative value; **color alone** carries the active map measure.
- The maps share the same light CARTO basemap, white cell outline, warm
  sequential low-to-high palette, hover highlighting, and dark selected-cell
  ring.
- The warm color scale is recalculated whenever the active filters change. The
  lowest visible value is assigned the light end of the palette and the highest
  visible value the dark end, with the other values distributed between them.
  This improves contrast within the current result set, especially when a
  filter leaves a narrow range of counts.
- Because the scale's minimum and maximum can change, color is only comparable
  within the current map state. A dark-red cell might represent 12 crashes in
  one filter state and 80 in another; identical shades do not guarantee
  identical counts across tabs or filter states. The legend updates to show the
  current numeric range, so users should consult it after changing a filter
  rather than comparing colors from memory.
- Legends use the same visual vocabulary for the quantitative gradient and
  selected grid cell. Domain-specific symbols, such as Fire & Rescue station
  crosses and station-radius context, are added without changing the base map
  language.

### Standard crash-cell semantic zoom

- Selecting a crash grid cell is the standard semantic zoom interaction across
  Safety Hotspots, Fire & Rescue Proximity, and Police Breathalyzers.
- In the default state, only aggregate grid cells are shown and the map stays at
  the countywide viewport.
- Selecting a cell recentres the map on that cell, zooms to street level
  (`zoom=13`), keeps the selected-cell ring and aggregate context, and reveals
  the individual crash coordinates belonging to that selected cell.
- Individual crashes use small circular markers with a subtle white outline,
  fixed pixel sizing, sufficient opacity for overlap, and pickable tooltips.
  They intentionally do not reuse the large aggregate-cell marker style.
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
- The default date window is the latest five years, bounded by the available
  data.
- The incomplete 2026 source period is labelled wherever time comparisons may
  be interpreted.

### Map and semantic drill-down

- Countywide crash concentrations are shown as uniform-size grid-cell circles,
  with color encoding crash count.
- Selecting a grid cell uses the shared semantic zoom behavior: the map moves to
  street level, retains the selected-cell context, and reveals the exact crash
  coordinates inside that cell.
- Clearing the selection returns to the countywide aggregate view.
- The selected-cell detail summarizes crash count, county share,
  suspected-serious/fatal count, dominant route type, and common roads.

### Condition fingerprint

- The hotspot fingerprint compares the selected cell with the active county
  baseline rather than presenting raw local percentages without context.
- The comparison uses grouped condition families for Weather, Surface, and
  Light.
- Categories are ordered by county prevalence so the selected hotspot and the
  baseline remain directly comparable.
- Small selected samples are explicitly cautioned because percentages can be
  unstable when the hotspot contains few crashes.
- The fingerprint uses a ridge-style SVG for each condition family so the visual
  encoding stays compact while still comparing a selected hotspot against the
  county baseline.
- The ridge outline is intentionally a fixed reference: a fully opaque stroke
  marks the constant benchmark, while the fill opacity inside that outline tracks
  how different the selected hotspot is from the county pattern.
- The outline color matches the groove/family color to make cross-family
  comparison easy without requiring a separate legend to decode the border.
- The ridge outline was widened so the reference remains legible at small sizes.
- The central neutral interior was softened away from stark black/gray/white to
  reduce visual dominance and to keep the focus on the family color and the
  relative fill opacity.
- The Light family uses a blue accent to remain visually distinct from the teal
  Weather and warm orange Surface strokes while still fitting the shared map
  palette.

### Linked crash timing

- A weekday-by-hour heatmap shows the temporal distribution for the county or
  the selected hotspot.
- Selecting a weekday-hour cell filters the map and condition fingerprint to
  that time window.
- Selecting a map cell changes the heatmap geography to that selected cell.
- Double-clicking the timing heatmap clears its time selection, while the main
  clear action resets both the spatial and time selections.

### Analytical cautions

- The hotspot view describes recorded crash concentrations and conditions. It
  does not estimate underlying traffic, pedestrian, or cyclist exposure and
  does not establish causal risk.
- The county comparison includes the selected cell; it is a contextual baseline
  rather than a statistically independent control group.

## Fire & Rescue Proximity

### Scope and data meaning

- The tab is named **Fire & Rescue Proximity**.
- It uses mapped fire-station locations to examine **straight-line proximity**
  to crash demand. It does not claim response times, dispatch coverage,
  staffing, service areas, or operational performance.
- The mapped station layer contains 37 usable stations. Station 27 / Public
  Safety Training Academy is excluded because it has no usable coordinates.
- The analysis is based on 0.01-degree geographic cells for the countywide
  overview, with exact crash locations revealed only during semantic
  drill-down.
- Distances use the Haversine straight-line calculation in kilometres.

### Severity and filtering

- The original demand analysis foregrounds suspected-serious and fatal
  crashes; the processed data retains the broader injury classifications for
  flexibility.
- The public severity control offers Fatal Injury, Suspected Serious Injury,
  and Possible Injury. Minor and no-apparent-injury options are intentionally
  omitted from the interface.
- The map has a minimum cell sample control, with a default of three crashes.
- Date range and daypart filters apply to the connected Fire & Rescue views.
- The default date window is the latest five years, bounded by the available
  data.
- The incomplete 2026 source period is labelled wherever time comparisons may
  be interpreted.

### Map and legends

- Grid cells are mapped as uniform-size circles. **Color alone** encodes the
  filtered crash count, avoiding overcrowding and competing size encodings.
- Fire stations use a rescue-cross marker rather than a circle, so they are
  clearly distinguishable from crash-demand cells.
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

- The scatterplot compares nearest-station straight-line distance (x) with
  filtered crash count (y). It intentionally avoids an arbitrary composite
  "gap score."
- The station bar chart ranks stations by the number of filtered crashes inside
  the selected radius. It supports **Most active** and **Least active** views.
- Each station is counted independently in the bar chart, so a crash can occur
  in more than one station radius; this is disclosed in the chart caption.

### Interaction decisions

- Map selection details appear in a compact overlay at the map's bottom-left,
  instead of shifting the charts below the map.
- Clicking a station bar selects that station and recentres the map at a
  deliberately moderate zoom level, keeping nearby stations and context in
  view.
- Hovering station bars is tooltip-only. It does not update map state or
  trigger a rerender.
- Clicking an empty area of the map clears both station and grid-cell
  selections.
- Only the linked visualization block rerenders on map, scatterplot, or bar
  selection; the tab header and filter controls remain in place.

### Analytical cautions

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
- Date, included alcohol categories, measure, and minimum all-crashes-per-cell
  controls apply to the connected views. The default date window is the latest
  five years, bounded by the available data.
- The minimum all-crashes-per-cell control is a reliability/context filter on
  the denominator, not a minimum number of alcohol-related crashes.
- When a weekday-hour heatmap cell is selected, the map minimum automatically
  drops to one crash per cell. A narrow time slice should not disappear merely
  because it no longer meets the broader countywide sample threshold.

### Map and semantic drill-down

- The countywide map aggregates crashes into cells to keep dense patterns
  readable. Uniform marker size leaves color as the single quantitative map
  encoding.
- Selecting an aggregate cell follows the shared semantic zoom behavior: the
  map recentres at street level, retains the selected-cell/aggregate context,
  and overlays the exact coordinates of the underlying active alcohol-related
  crashes. Clearing the selection restores the countywide aggregation.
- Exact coordinates identify recorded crash locations, but they still do not
  by themselves identify a safe, legal, or operationally suitable checkpoint
  position.

### Linked time and place exploration

- The weekday-by-hour heatmap reveals recurring timing patterns and supports a
  selected time window that filters the map.
- The timing heatmap uses a radial layout because hour of day is periodic:
  23:00 and 00:00 are adjacent observations rather than unrelated endpoints.
  Hours are mapped around the circle and weekdays are mapped to concentric
  rings, aligning the same hour across all seven days on one radial spoke.
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
- Selecting a map cell filters the heatmap to that geography. Selecting a
  heatmap cell filters the map to that weekday and hour.
- A single clear action resets both spatial and time selections, and the
  summary text always states whether the current context is countywide or a
  selected cell and time.
- The heatmap time axis runs from 06:00 through 05:00 so daytime/evening/night
  patterns read as one continuous daily cycle rather than splitting the night
  at midnight.

### Analytical cautions

- Historical incident concentration can help prioritize further operational
  review, but deployment decisions also require traffic volume, road safety,
  legal constraints, staffing, jurisdiction, and current conditions.
- Counts show incident volume; shares show relative alcohol involvement among
  recorded crashes. Neither measure estimates the prevalence of impaired
  driving in the general traffic population.
