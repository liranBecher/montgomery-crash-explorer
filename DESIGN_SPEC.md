# Montgomery County Crash Explorer - Design Specification

This specification records the intended analytical and interaction design before
preprocessing begins. It does not claim that the visualizations, measures, or
findings are implemented.

## Primary research question

Where and when do crashes concentrate in Montgomery County, and which
conditions, response context, alcohol-related patterns, and vehicle
characteristics distinguish those crashes and their injury severity?

The four application tabs answer complementary parts of this question. The
Safety Hotspots tab is the overview and entry point; the other tabs provide
focused follow-up analyses.

## Intended users

- Montgomery County road-safety and transportation analysts
- Public-safety and first-responder planners
- Law-enforcement planners evaluating historical alcohol-related crash patterns
- Residents exploring local crash patterns

These are intended users inferred from the project scope. User research has not
yet been conducted.

## Exploration flow

The interface follows Shneiderman's mantra:

1. **Overview first:** begin with the countywide Safety Hotspots map.
2. **Zoom and filter:** narrow the view by date, area, severity, map extent, or
   a chart selection.
3. **Details on demand:** reveal exact counts, percentages, sample sizes, and
   record-level fields through tooltips or a focused details panel.

A persistent selection summary will show the active subset. Clearing the
selection will restore the countywide overview.

## Planned views and encodings

### 1. Safety Hotspots - primary overview

**Crash hotspot map**

- Purpose: locate geographic concentrations of recorded crashes.
- Marks: map points or aggregated spatial cells; the choice will be validated
  after coordinate quality and density are inspected.
- Encodings: longitude and latitude to position; crash count to size or color;
  severity to a filtered category or a palette of no more than six categories.
- Details on demand: location/area, crash count, severity composition, selected
  date range, and the geographic aggregation used.

**Hotspot fingerprint**

- Purpose: compare conditions in the selected hotspot with the countywide
  reference distribution.
- Marks: grouped horizontal bars.
- Encodings: condition category on the vertical axis; share of crashes on the
  horizontal axis; two colors for selected area and county reference.
- Correctness: the percentage axis starts at zero; categories are sorted by a
  stated rule; sample sizes remain visible.

**Crash timing**

- Purpose: show when crashes in the active geography occur.
- Marks: day-of-week by hour heatmap, subject to data validation.
- Encodings: hour from 00:00 to 23:00 from left to right; day of week on the
  vertical axis; crash count or share to sequential color.
- Details on demand: day, hour, count, share, active geography, and date range.

### 2. Fire & Rescue Proximity

- Main map: filtered crash demand and mapped fire stations as separate,
  clearly labeled layers. Fatal, suspected-serious, and possible injury are
  available; suspected-serious and fatal are selected by default. Minor and
  no-apparent-injury records remain in processed data but are not UI options.
- Linked detail view: occupied grid cells plotted by crash count and Haversine
  distance from cell center to the nearest mapped station. Grid-cell circles
  use a uniform size so position remains the only quantitative encoding.
- Station comparison: a ranked horizontal bar chart counts filtered crashes
  inside an adjustable straight-line radius around each
  mapped station, with controls for the most-active or least-active end of the
  ranking. Overlapping radii may count a crash for multiple stations.
- Map selection details appear in a compact bottom-left overlay rather than
  moving later charts. Clicking a station bar focuses the map; hovering only
  shows the chart tooltip and does not rerun the page. Empty-map clicks clear
  selection.
- The view describes straight-line proximity only. It does not represent road
  travel time, dispatch history, service areas, staffing, or response performance.

### 3. Police Breathalyzers

- Main map: recorded alcohol-related crash count and share by area.
- Timing view: day-of-week by hour heatmap using a left-to-right time axis.
- The alcohol-related definition and any prioritization rule must be documented
  before the view can make recommendations. Until then, the view describes
  historical recorded patterns only.

### 4. Vehicles and Injuries

- Age comparison: 100% stacked bars only if injury categories form a complete
  distribution within each vehicle-age group; otherwise use grouped bars.
- Make-by-age comparison: a matrix of serious-injury share with visible sample
  size and a minimum-sample rule.
- Vehicle-age bands, injury grouping, make normalization, and minimum sample
  size remain undecided until preprocessing is complete.

## Brushing and linking behavior

| User action | Views updated |
| --- | --- |
| Change a shared date, area, or severity filter | Every visualization in the active tab and the selection summary |
| Select a hotspot or map area | Hotspot fingerprint, crash timing, and selection summary |
| Select a time cell or interval | Active map, comparison view, and selection summary |
| Select a responder-demand area | Coverage-gap detail and selection summary |
| Select an alcohol-related area or time cell | Alcohol map, timing view, and selection summary |
| Select a vehicle-age group or matrix cell | Vehicle comparison, injury distribution, and selection summary |
| Clear selection | Restore the shared-filter overview in the active tab |

The Streamlit prototype currently describes these interactions but does not
implement chart selection, brushing, or linking.

## Visualization correctness constraints

- Every chart needs a specific title, explicit legend where color encodes data,
  axis names, units, and factual tooltip labels.
- Bar-chart quantitative axes start at zero.
- Stacked bars are used only for parts of a whole; normalized stacks sum to
  100% within each group.
- Lines are reserved for ordered continuous data, particularly time series.
- Time runs from earlier to later, left to right.
- Categorical palettes use no more than six to eight distinguishable colors.
- No 3D charts and no dual quantitative axes.
- Flat or analytically uninformative views are removed or redesigned after the
  processed data are inspected.
- Counts, shares, rates, and severity measures must be named precisely. A rate
  is not used unless a valid exposure denominator exists.
- Recommendations are not presented until their definitions, assumptions, and
  validation are documented.

## Definition of done for the interactive core

The core is complete when processed data are connected; every displayed
measure has a documented definition; the county overview supports filters and
details on demand; at least two visualizations in the primary view are linked
in both directions; the selection summary and clear action work; axes, legends,
units, tooltips, and color choices pass the correctness constraints above; and
automated tests cover the principal interactions without relying on fabricated
data or findings.
