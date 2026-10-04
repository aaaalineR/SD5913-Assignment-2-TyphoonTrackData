# Process

## Tools

I used VS Code and `uv` as my main development environment.

I used Python with Matplotlib and Cartopy to create the required static visualisation. I used Streamlit and Plotly to build an optional interactive version of the same dataset.

I also used ChatGPT during the development process to discuss visualisation ideas, debug Python code, and help develop parts of the plotting and interaction logic. I did not use Playwright, Playwright CLI, or Browser Use in the final project because they are browser automation tools rather than necessary visualisation tools.

## Kept

I kept geographic position as the main visual structure of the project. Longitude and latitude directly determine where each cyclone appears on the map, while the trajectory connects the observations into a journey.

I also kept intensity as a visual variable. The colour gradually changes from cool blue for weaker systems to warmer yellow, orange, and red for stronger systems. This makes the intensity changes visible without adding another chart.

For the interactive version, I kept the idea of a single journey progression slider. One control produces one clear response: moving the slider changes the cyclone's position and updates its time, location, and intensity. This made the temporal dimension easier to explore without replacing the required static overview.

## Rejected

The first interactive version used the raw observation points directly as a Plotly route. The result looked visually cluttered, with many short segments and overlapping lines. I rejected this approach because the individual observations distracted from the overall movement pattern.

I then used a smoothed trajectory to make the movement easier to read. The smoothing is only a visual transformation; the original CSV remains unchanged and is still the source of the data.

I also considered using browser automation tools such as Playwright or Browser Use because they were introduced as possible web-related tools. I rejected them for this assignment because they would add an unnecessary layer between the data, the visualisation, and the user interaction.

During the final interaction design, I tested different directional marker styles. I kept a fixed-size directional marker because it remains visible when the map is zoomed in or out. Although the final marker is more geometric than the earlier custom arrow experiments, it is stable and communicates movement direction clearly.

## What I corrected

AI-generated code initially made several assumptions about how the visualisation should be structured. I checked the output in the browser and changed the visual design when the result did not communicate the data clearly.

In particular, the initial interactive routes were too visually noisy. I changed the route construction to use the existing track transformation and smoothing logic. I also checked the relationship between the slider, the cyclone's actual observations, and the displayed time, position, and intensity instead of treating the animation as purely decorative.

The final result therefore combines AI-assisted coding with visual testing and manual design decisions. The raw data was kept unchanged, and the transformations are performed by the code rather than by editing the source CSV.