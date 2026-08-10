# Project Requirements

This is a structured English transcription of the course brief. The original,
authoritative Hebrew PDF is included in the repository as
[פרוייקט ויזואליזציה הוראות.pdf](./פרוייקט%20ויזואליזציה%20הוראות.pdf).

## Project format

- Submit in teams of exactly three.
- Build an original visualization page or system that answers a question or
  investigates a problem in a dataset.
- Choose a dataset from the supplied dataset list. A different dataset requires
  the instructor's approval.
- Use a sufficiently rich dataset. The recommendation is at least 100 rows,
  around five or more attributes, and time or location data.
- The result should help users discover insights that would be difficult or
  time-consuming to find without the visualization, such as trends, patterns,
  or outliers.
- The visualization should emphasize a meaningful aspect of the data and reach
  a high overall standard.
- All tools and libraries used must be listed in the report.

## Implementation

The project may use Tableau or another web-based tool such as D3.

For a web-based project:

- Host the code and application on a server; GitHub may be used for the code.
- The system must work in a browser from any computer.
- Submit a working link.
- Use multiple views and interaction to explore the data from several
  perspectives. For a good-or-better project, the views should be connected
  through linking and brushing so a selection in one view updates the others.

The Tableau-only requirement of at least two dashboards, or one dashboard and
one story, does not apply to this Streamlit project.

## Functional and interaction requirements

The following course guidance expands the formal brief into concrete design
and implementation requirements.

### Full interactivity

- The system must be dynamic and interactive. It must not consist only of
  static chart images.
- The visualization system must be organized around a clear research question
  or defined analytical goal, rather than an unrelated collection of charts.
- Multiple visualizations must be connected through brushing and linking. For
  example, selecting a map region or time interval should update the other
  relevant views automatically.

### Shneiderman's mantra

The dashboard should support a gradual exploration workflow:

1. **Overview first:** present the overall picture first, normally in the
   upper-left or otherwise most prominent part of the interface.
2. **Zoom and filter:** provide interactive controls, such as sliders, date
   ranges, category filters, map zoom, or area selectors, for focusing on
   relevant subsets.
3. **Details on demand:** reveal exact values and raw details through tooltips,
   focused selections, or drill-down interactions instead of showing all
   details at once.

### Interface and chart presentation

- The interface should be professional, attractive, and easy to use. The
  course guidance emphasizes the principle "What is beautiful is usable."
- Every chart must have a clear title and accurate axis labels, including units
  where relevant.
- Every color encoding that requires interpretation must have an explicit,
  clearly labeled legend.
- Labels, legends, axes, and tooltips must use consistent terminology and
  accurately describe the underlying data.

## Visualization correctness constraints

These constraints should be treated as design-review checks for every chart:

- Do not include uninformative charts that are flat, show no meaningful
  variation, or provide no analytical value. Try different cuts, aggregations,
  and comparisons until the view supports a useful finding.
- Use line charts only for continuous ordered data, especially time series. Do
  not connect unrelated categorical values with a line.
- Limit categorical color palettes to approximately 6-8 distinguishable
  colors. Use grouping, filtering, small multiples, or another encoding when
  there are more categories.
- Bar charts and stacked bar charts must start their quantitative axis at zero.
  A non-zero baseline may be considered for line or point charts only when it
  is clearly justified and does not distort interpretation.
- Use stacked bars only when the segments represent parts of a whole. For a
  normalized stacked bar, the segments must sum to 100%.
- Avoid dual quantitative axes. They are prohibited in most cases because they
  can create misleading apparent correlations and intersections.
- Do not use 3D charts. Perspective distorts heights, areas, and comparisons.
- Build an exploratory visualization system, not a static explanatory poster
  or infographic.
- Time axes must run from left to right, from earlier to later, including in a
  Hebrew-language interface.

## Data preparation

- Data may be processed or joined with other tables and external sources.
- Any preparation tool may be used, including Python or Excel.
- The report must explain exactly what preprocessing or manipulation was
  performed. Examples include normalization, missing-value completion, pivoting
  to long format, and joining multiple sources.

## Submission dates

- Early submission: July 19, 2026.
- Regular submission: August 20, 2026.
- Students who want a course grade before August may submit early and email the
  instructor after submission. Regular-submission grades are expected around
  September.

## Submission and report

Report Link [Link](https://docs.google.com/document/d/1lxUd-5fLB0UovdxjrY3h26qI2YNxPsfp/edit?usp=sharing&ouid=114896909654094115564&rtpof=true&sd=true)

- Put a working project link at the beginning of the report.
- Submit the report through the submission box of one team member.
- The report must not exceed 10 pages.
- The report must contain:
  1. Project link, project topic, and every team member's name and ID number.
  2. An introduction describing the topic, the problem or main research
     question, potential users, and why the topic matters.
  3. A description of every project data file, links to the data, row counts,
     and important columns.
  4. A description of all preprocessing and data manipulation.
  5. For a non-Tableau project, a complete list of visualization tools,
     JavaScript libraries, and LLMs used.
  6. An explanation of the solution: the main chart, how users should use the
     visualizations and interactions, why the design was chosen, and its
     advantages and disadvantages.

## Grading

### Effectiveness - 25%

- The questions are interesting and non-trivial.
- The selected visualizations answer the stated questions.
- The visualizations investigate the presented problem effectively.

### Correctness - 25%

- Data is mapped correctly to visual variables.
- The visualizations follow the principles taught in class.
- Color is used correctly.
- Interaction is present and implemented correctly.
- Legends, axis titles, and other labels are correct.

### Creativity and scope - 20%

- The project shows creativity in the problem, presentation, or a local
  solution.
- The scope goes beyond a collection of simple charts.
- Data is shown interactively through multiple perspectives and views.
- Linking and brushing between views is expected for a strong submission.

### Aesthetics - 15%

- The application should look professional and attractive.
- Visual polish should support perceived usability as well as appearance,
  following the course principle "What is beautiful is usable."

### Report - 15%

- The report must cover all required sections in detail.
- Missing details, including data links or the list of tools, reduce the grade.
