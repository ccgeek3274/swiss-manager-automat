"""Vygeneruje icon.png / icon.ico / icon.icns: šachovnice se zaoblenými rohy
(průhledné okolí), nad ní klávesa "SM". Jednorázový skript, spouštět s Pillow."""
from PIL import Image, ImageDraw, ImageFont

SRC = (
    "/Users/karel/Library/Application Support/CrossOver/Bottles/Chess/"
    "windata/cxmenu/icons/hicolor/32x32/apps/F6BA_SwissManager.0.png"
)
OUT_DIR = "/Users/karel/Soukrome/bin/swiss-manager-automat"
S = 256

# Šachovnice ostře zvětšená, neprůhledná (i bílá pole), pak oříznutá
# zaoblenou maskou — okolí rohů zůstane průhledné
board = Image.open(SRC).convert("RGBA").resize((S, S), Image.NEAREST)
opaque = Image.new("RGBA", (S, S), (255, 255, 255, 255))
opaque.alpha_composite(board)

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((4, 4, S - 4, S - 4), 44, fill=255)

img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
img.paste(opaque, (0, 0), mask)
draw = ImageDraw.Draw(img)
draw.rounded_rectangle(
    (4, 4, S - 4, S - 4), 44, outline=(120, 120, 125, 255), width=4
)

# Klávesa (keycap) přes střed šachovnice
kx0, ky0, kx1, ky1 = 48, 48, 208, 208
r = 28
shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle(
    (kx0 + 6, ky0 + 10, kx1 + 6, ky1 + 10), r, fill=(0, 0, 0, 90)
)
img.alpha_composite(shadow)
draw.rounded_rectangle(
    (kx0, ky0, kx1, ky1), r,
    fill=(245, 245, 247, 255), outline=(70, 70, 75, 255), width=6,
)
draw.rounded_rectangle(
    (kx0 + 16, ky0 + 12, kx1 - 16, ky1 - 24), r - 12,
    fill=(255, 255, 255, 255), outline=(180, 180, 185, 255), width=3,
)

font = None
for path in (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
):
    try:
        font = ImageFont.truetype(path, 84)
        break
    except OSError:
        pass
if font is None:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "SM", font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
cx = (kx0 + kx1) / 2 - tw / 2 - bbox[0]
cy = (ky0 + ky1 - 12) / 2 - th / 2 - bbox[1]
draw.text((cx, cy), "SM", font=font, fill=(40, 40, 45, 255))

img.save(f"{OUT_DIR}/icon.png")
img.save(
    f"{OUT_DIR}/icon.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("hotovo")
