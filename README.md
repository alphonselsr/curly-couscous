# Orbit Lab

An interactive 2D/3D n-body gravity sandbox written in Python with the pygame API. The 3D mode uses real depth, 3D gravity, perspective scaling, and depth-sorted rendering.

## Run it

```bash
python -m pip install -r requirements.txt
python nbody.py
```

## Controls

- Adjust `PLANETS`, `GRAVITY`, `TIME SCALE`, and `SOFTENING` with the sliders.
- Switch between `MODE: 2D` and `MODE: 3D`. In 3D, depth changes apparent size and bodies attract each other in all three axes.
- Press `RESET SYSTEM` to regenerate the selected number of planets.
- Left-click empty space to add a planet.
- Drag a planet to move it; release to give it launch velocity in the drag direction.
- Right-click a planet to select it and inspect its current speed.
- Toggle trails and velocity vectors, or pause the simulation.
