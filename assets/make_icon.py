"""Generate assets/icon.ico (network nodes with a check mark). Requires Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill="#0D1424", outline="#00D4FF", width=14)
nodes = [(256, 120), (120, 330), (392, 330)]
for a in nodes:
    for b in nodes:
        d.line((a, b), fill="#243352", width=18)
for x, y in nodes:
    d.ellipse((x - 46, y - 46, x + 46, y + 46), fill="#16213A", outline="#00D4FF", width=12)
d.line(((200, 300), (245, 350), (330, 240)), fill="#00E5A0", width=34, joint="curve")
out = Path(__file__).with_name("icon.ico")
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(out.with_name("icon.png"))
print("wrote", out)
