# Student guide: prompts and visualizations

This app turns a natural-language question into read-only DuckDB SQL, validates it, runs it against the Spotify data, and displays the results. Before execution, inspect the generated SQL in the app. The default result limit is 5 rows unless you ask for a different number; the maximum is 100.

The data is split across two tables:

- `tracks`: track names, artists, albums, popularity, and genre tags.
- `audio_features`: numeric measurements such as energy, valence, and tempo.

Questions that combine track details with audio features require a join on `track_id`. The agent usually handles this when the question needs both.

## Bar chart

Bar charts are useful for comparing categories or ranking tracks.

Try:

> Show the five most popular tracks tagged acoustic. Include track name, artist, and popularity.

Expected result: a table of tracks and a popularity bar chart. The app uses a bar chart when the results include `track_name` and `popularity`.

> Show the top 5 genres by average popularity with total track count

## Line chart

Line charts are useful for showing how a measurement changes along an ordered numeric axis. This dataset has no date or year field, so use an ordered feature such as tempo instead of treating the tracks as a timeline.

Try:

> Group tracks into 10-BPM tempo bands. For each band, calculate average energy and average valence. Return the tempo band first, then both averages, order by tempo band ascending, and recommend a line chart.

Expected result: one point per tempo band, with separate lines for average energy and valence. Putting the x-axis column first and ordering by it helps the app draw a meaningful trend.

## Scatter plot

Scatter plots show how two numeric measurements relate. Each dot represents one track; in this app, popularity is used for dot size when that column is included.

Try:

> For 20 tracks tagged happy, show track name, artist, energy, valence, and popularity. Recommend a scatter plot of valence versus energy.

Expected result: valence on the horizontal axis, energy on the vertical axis, and larger dots for more popular tracks.

## Table

Tables are best when you want specific details and are not comparing numeric values.

Try:

> List five tracks tagged acoustic with their track name, artist, album, and genre. Do not include numeric measurements; return this as a table.

The data table is always available. If the result has no numeric columns, the visualization tab explains that there is no numeric chart to show.

## Audio features in plain language

- **Tempo** is the speed of the beat, measured in beats per minute (BPM). A tempo of 120 BPM means about 120 beats each minute. It is not the same as perceived energy: a fast song can still feel gentle.
- **Energy** estimates how intense and active a track sounds. Lower values often feel calmer; higher values often feel busier or more forceful. It is not simply the recording's volume.
- **Valence** estimates how positive or cheerful the musical mood sounds. Lower values can feel darker or more somber; higher values can feel brighter or happier.
- **Danceability** estimates how suitable the rhythm is for dancing, based on qualities such as beat stability and rhythmic regularity.
- **Acousticness** estimates whether a track sounds acoustic rather than electronic.

Genre values such as `acoustic`, `study`, `happy`, and `club` are dataset tags. They are not guarantees about every track's sound.

## Before you run a prompt

Check that the generated SQL selects the columns needed for the chart. A line chart needs an ordered numeric x-axis followed by numeric series; a scatter plot needs both `energy` and `valence`; and a popularity bar chart needs `track_name` and `popularity`. The app displays the generated SQL and executes that validated query against DuckDB.
