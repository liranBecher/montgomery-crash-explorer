# Fire & Rescue visualization decisions

This record captures the major design and interaction decisions made for the
Fire & Rescue Proximity tab.

## Scope and data meaning

- The tab is named **Fire & Rescue Proximity**.
- It uses mapped fire-station locations to examine **straight-line proximity**
  to crash demand. It does not claim response times, dispatch coverage,
  staffing, service areas, or operational performance.
- The mapped station layer contains 37 usable stations. Station 27 / Public
  Safety Training Academy is excluded because it has no usable coordinates.
- The analysis is based on 0.01-degree geographic cells, rather than individual
  crash dots, to make spatial demand patterns readable.
- Distances use the Haversine straight-line calculation in kilometres.

## Severity and filtering

- The original demand analysis foregrounds suspected-serious and fatal
  crashes; the processed data retains the broader injury classifications for
  flexibility.
- The public severity control offers Fatal Injury, Suspected Serious Injury,
  and Possible Injury. Minor and no-apparent-injury options are intentionally
  omitted from the interface.
- The map has a minimum cell sample control, with a default of three crashes.
- Date range and daypart filters apply to the connected Fire & Rescue views.
- The incomplete 2026 source period is labelled wherever time comparisons may
  be interpreted.

## Map and legends

- Grid cells are mapped as uniform-size circles. **Color alone** encodes the
  filtered crash count, avoiding overcrowding and competing size encodings.
- Fire stations use a rescue-cross marker rather than a circle, so they are
  clearly distinguishable from crash-demand cells.
- The map includes an explicit legend for crash-count color, rescue crosses,
  selected cells, and the selected-station radius/incident context.
- Selecting a station displays its adjustable straight-line radius and the
  filtered crashes inside it. The radius is a proximity aid, not a coverage
  claim.

## Companion views

- The scatterplot compares nearest-station straight-line distance (x) with
  filtered crash count (y). It intentionally avoids an arbitrary composite
  "gap score."
- The station bar chart ranks stations by the number of filtered crashes inside
  the selected radius. It supports **Most active** and **Least active** views.
- Each station is counted independently in the bar chart, so a crash can occur
  in more than one station radius; this is disclosed in the chart caption.

## Interaction decisions

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

## Analytical cautions

- Geographic proximity cannot establish whether stations are operationally
  redundant or "too close for no reason." That conclusion would require
  information such as apparatus, staffing, service areas, and dispatch data.
- Municipality is not used as a primary analysis dimension because it is
  largely missing in the incident data.
