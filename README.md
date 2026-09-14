# Orbit Lab

An interactive 2D n-body gravity sandbox written in Python with pygame. It combines pairwise gravity, stable elastic planet collisions, automatic framing, trails, and a particle background.

## Run it

```bash
python -m pip install -r requirements.txt
python nbody.py
```

## Controls

- Adjust `PLANETS`, `GRAVITY`, `TIME SCALE`, and `SOFTENING` with the sliders.
- Press `RESET SYSTEM` to regenerate the selected number of planets.
- Left-click empty space to add a planet.
- Drag a planet to move it; release to give it launch velocity in the drag direction.
- Right-click a planet to select it and inspect its current speed.
- Toggle trails, velocity vectors, collisions, or pause the simulation.
- `TRACK: ON` keeps every planet inside the visible space by following the group and adjusting the zoom. Toggle it off for a fixed view.
- Collisions separate overlapping planets and apply mass-aware elastic impulses in the physics core.
