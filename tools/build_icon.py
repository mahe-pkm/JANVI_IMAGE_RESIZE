"""Draw the Janvi Studio crop-frame icon at Windows icon sizes."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
image = Image.new('RGBA', (1024, 1024))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((32,32,992,992), radius=210, fill='#20282b')
draw.rounded_rectangle((228,232,796,792), radius=40, fill='#405d60')
draw.polygon([(230,690),(436,447),(568,593),(661,486),(796,657),(796,750),(230,750)], fill='#b5ceca')
draw.ellipse((596,320,698,422), fill='#e5b96d')
for points in ([(148,354),(148,148),(354,148)],[(670,148),(876,148),(876,354)],[(148,670),(148,876),(354,876)],[(670,876),(876,876),(876,670)]):
    draw.line(points, fill='#e5b96d', width=52, joint='curve')
icon = image.resize((256,256), Image.Resampling.LANCZOS)
for path in (ROOT/'assets/janvi-app.ico', ROOT/'desktop/janvi-app.ico'):
    icon.save(path, sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
icon.save(ROOT/'assets/janvi-studio-icon.png')
icon.save(ROOT/'static/studio-icon.png')
print('Created crop-frame application icon')
