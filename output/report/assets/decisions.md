# Visualization decisions

This record captures the major data, design, and interaction decisions for
the Fire & Rescue Proximity and Police Breathalyzers tabs.

## Fire & Rescue Proximity

### Scope and data meaning

- The tab is named **Fire & Rescue Proximity**.
- It uses mapped fire-station locations to examine **straight-line proximity**
  to crash demand. It does not claim response times, dispatch coverage,
  staffing, service areas, or operational performance.
- The mapped station layer contains 37 usable stations. Station 27 / Public
  Safety Training Academy is excluded because it has no usable coordinates.
- The analysis is based on 0.01-degree geographic cells, rather than individual
  crash dots, to make spatial demand patterns readable.
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
- Countywide demand is aggregated into readable cells. Selecting a cell is the
  semantic drill-down: the map zooms to that area and shows the underlying
  crash coordinates; clearing the selection restores the aggregate overview.
- Fire-station markers remain visible during the cell drill-down so exact
  incidents retain their proximity context.

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
- Selecting an aggregate cell is the semantic zoom action: the map recentres at
  street level and replaces the cell aggregation with the exact coordinates of
  its underlying alcohol-related crashes. Clearing the selection restores the
  countywide aggregation.
- Exact coordinates identify recorded crash locations, but they still do not
  by themselves identify a safe, legal, or operationally suitable checkpoint
  position.

### Linked time and place exploration

- The weekday-by-hour heatmap reveals recurring timing patterns and supports a
  selected time window that filters the map.
- Selecting a map cell filters the heatmap to that geography. Selecting a
  heatmap cell filters the map to that weekday and hour.
- A single clear action resets both spatial and time selections, and the
  summary text always states whether the current context is countywide or a
  selected cell and time.
- For the day-time heatmap, we wanted to show the difference between day and night,
  therefore the time axis is 6:00-5:00

### Analytical cautions

- Historical incident concentration can help prioritize further operational
  review, but deployment decisions also require traffic volume, road safety,
  legal constraints, staffing, jurisdiction, and current conditions.
- Counts show incident volume; shares show relative alcohol involvement among
  recorded crashes. Neither measure estimates the prevalence of impaired
  driving in the general traffic population.
