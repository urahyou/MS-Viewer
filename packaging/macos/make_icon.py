"""Draw a native-code application icon: antenna dish and visibility wave."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
path = root / "build/macos-assets/MSViewer.icns"
path.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
d = ImageDraw.Draw(image)
d.rounded_rectangle((24, 24, 1000, 1000), radius=210, fill="#11283e")
d.arc((190, 110, 840, 760), start=25, end=155, fill="#67ddca", width=43)
d.line((270, 550, 665, 270), fill="#d8e8ed", width=23)
d.line((510, 625, 410, 788), fill="#d8e8ed", width=32)
d.line((510, 625, 610, 788), fill="#d8e8ed", width=32)
d.line((355, 795, 665, 795), fill="#d8e8ed", width=35)
d.arc((650, 140, 795, 285), 210, 310, fill="#e9b955", width=17)
d.arc((623, 109, 835, 321), 210, 310, fill="#e9b955", width=17)
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 128)
d.text((512, 850), "MS", font=font, anchor="mm", fill="white")
image.save(path, format="ICNS")
print(path)
