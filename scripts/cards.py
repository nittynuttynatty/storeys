"""Draw a 1200x630 link-preview card for each project (used by pages.py)."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONTS = os.path.join(ROOT, "assets", "fonts")
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)

INK, MUTED, CREAM = (58, 44, 38), (110, 93, 84), (255, 253, 247)
FACADES = [("#F4C6B0", "#D9A08A", "#E58F73"), ("#CDE3C6", "#A3C39C", "#6FA374"), ("#F5E1A6", "#D8BD7B", "#D9A23F"),
           ("#CCE2F2", "#9FC0DA", "#5E95C4"), ("#F1CFD9", "#D3A3B4", "#C9738F"), ("#EEE5D5", "#CFBEA2", "#B48E62")]

def jshash(s):  # same as the app's hash(), so each project keeps its colour
    h = 7
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h

def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))

def wrap(d, text, f, width, maxlines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        while d.textlength(lines[-1] + "…", font=f) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines

def dashed(d, pts, fill, dash=8, gap=7, width=2):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L = max(1, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5)
        n, t = int(L // (dash + gap)) + 1, 0
        for i in range(n):
            a, b = i * (dash + gap) / L, min(1, (i * (dash + gap) + dash) / L)
            d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=fill, width=width)

def card(path, name, kind, pct, when_label):
    W, H, S = 1200, 630, 2  # draw at 2x then downsample for smooth edges
    im = Image.new("RGB", (W * S, H * S))
    d = ImageDraw.Draw(im)
    top, bot = rgb("#8CCDF0"), rgb("#EEF7EE")
    for y in range(H * S):
        d.line([(0, y), (W * S, y)], fill=mix(top, bot, y / (H * S)))
    s = lambda v: int(v * S)
    G = 560
    # sun, clouds, hazy skyline
    d.ellipse([s(1080), s(40), s(1150), s(110)], fill=rgb("#FFE07A"))
    for cx, cy, r in [(800, 120, 26), (826, 108, 32), (856, 122, 24), (980, 220, 18), (1000, 212, 22)]:
        d.ellipse([s(cx - r * 1.4), s(cy - r * .7), s(cx + r * 1.4), s(cy + r * .7)], fill=(255, 255, 255))
    for x, w, h in [(700, 60, 150), (765, 45, 210), (1120, 50, 180), (1060, 55, 120)]:
        d.rectangle([s(x), s(G - h), s(x + w), s(G)], fill=rgb("#CFE2EC"))
    d.rectangle([0, s(G), s(W), s(H)], fill=rgb("#A6D98F"))
    d.polygon([(0, s(G + 34)), (s(W), s(G + 12)), (s(W), s(G + 36)), (0, s(G + 58))], fill=rgb("#F3E6CC"))
    # tower
    F = FACADES[jshash(name) % len(FACADES)]
    cf, cs, ca = rgb(F[0]), rgb(F[1]), rgb(F[2])
    N, fh, fx, fw, dx, dy = 16, 24, 840, 180, 70, -35
    built = max(1, round(N * min(pct or 0, 100) / 100)) if pct else 0
    done = (pct or 0) >= 100
    topy = G - N * fh
    ghost = mix(INK, bot, .6)
    dashed(d, [(s(fx), s(G)), (s(fx), s(topy)), (s(fx + fw), s(topy)), (s(fx + fw), s(G))], ghost)
    dashed(d, [(s(fx), s(topy)), (s(fx + dx), s(topy + dy)), (s(fx + fw + dx), s(topy + dy)), (s(fx + fw + dx), s(G + dy))], ghost)
    dashed(d, [(s(fx + fw), s(topy)), (s(fx + fw + dx), s(topy + dy))], ghost)
    glass, glass2 = rgb("#BFE3F5"), rgb("#86BEE0")
    for i in range(built):
        y = G - (i + 1) * fh
        front = mix(cf, (0, 0, 0), .12) if i == 0 else cf
        side = mix(cs, (0, 0, 0), .12) if i == 0 else cs
        d.rectangle([s(fx), s(y), s(fx + fw), s(y + fh) + 1], fill=front)
        d.polygon([(s(fx + fw), s(y)), (s(fx + fw + dx), s(y + dy)), (s(fx + fw + dx), s(y + fh + dy) + 1), (s(fx + fw), s(y + fh) + 1)], fill=side)
        d.rectangle([s(fx), s(y), s(fx + 8), s(y + fh)], fill=ca)
        if i:
            d.rectangle([s(fx), s(y + fh - 3), s(fx + fw), s(y + fh)], fill=mix(front, (255, 255, 255), .5))
            for k in range(4):
                wx = fx + 22 + k * 40
                d.rectangle([s(wx), s(y + 5), s(wx + 24), s(y + 15)], fill=glass if (i + k) % 3 else glass2)
            for k in range(2):
                sx = fx + fw + 14 + k * 28
                sy = y + 5 + (14 + k * 28) * dy / dx
                d.polygon([(s(sx), s(sy)), (s(sx + 16), s(sy + 16 * dy / dx)), (s(sx + 16), s(sy + 16 * dy / dx + 10)), (s(sx), s(sy + 10))], fill=glass2)
        else:
            d.rectangle([s(fx + 8), s(y + 4), s(fx + fw - 6), s(y + fh)], fill=mix(cf, INK, .35))
    if built:
        yb = G - built * fh
        roof = mix(cf, (255, 255, 255), .35) if done else rgb("#DAD3C8")
        d.polygon([(s(fx), s(yb)), (s(fx + dx), s(yb + dy)), (s(fx + fw + dx), s(yb + dy)), (s(fx + fw), s(yb))], fill=roof)
        if not done:
            net = rgb("#7CC48A")
            d.rectangle([s(fx - 3), s(yb), s(fx + fw + 3), s(yb + min(2, built) * fh)], fill=mix(net, cf, .25))
            d.rectangle([s(fx - 8), s(yb - 3), s(fx + fw + 8), s(yb + 1)], fill=rgb("#E98A3C"))
    if not done:
        C, K = rgb("#F2B33D"), rgb("#9C7124")
        cx, mt = fx + fw + dx + 40, max(40, min(topy - 6, G - built * fh - 80))
        d.rectangle([s(cx - 6), s(mt), s(cx + 6), s(G + dy * .4)], fill=C)
        for y in range(int(mt), int(G + dy * .4) - 12, 14):
            d.line([(s(cx - 6), s(y)), (s(cx + 6), s(y + 14))], fill=K, width=2)
        d.rectangle([s(cx - 250), s(mt - 6), s(cx + 70), s(mt + 4)], fill=C)
        d.rectangle([s(cx + 40), s(mt + 4), s(cx + 66), s(mt + 18)], fill=rgb("#9A9086"))
        hx = fx + fw * .4
        hy = max(mt + 40, G - built * fh - 44)
        d.line([(s(hx), s(mt + 4)), (s(hx), s(hy))], fill=K, width=2)
        d.rectangle([s(hx - 22), s(hy), s(hx + 22), s(hy + 14)], fill=rgb("#F29AAE"))
    for tx, r in [(700, 26), (1160, 22)]:
        d.rectangle([s(tx - 3), s(G - 6), s(tx + 3), s(G + 22)], fill=rgb("#A47B57"))
        d.ellipse([s(tx - r), s(G - 6 - 2 * r), s(tx + r), s(G - 6)], fill=rgb("#6FBF7F"))
    # info panel
    d.rounded_rectangle([s(44), s(44), s(660), s(586)], radius=s(36), fill=CREAM)
    x = 84
    fTag, fName, fBig, fTxt, fSmall = font("Figtree-SemiBold.ttf", s(24)), font("Fraunces-SemiBold.ttf", s(58)), font("Fraunces-SemiBold.ttf", s(112)), font("Figtree-Medium.ttf", s(28)), font("Figtree-SemiBold.ttf", s(24))
    tw = d.textlength(kind, font=fTag)
    d.rounded_rectangle([s(x), s(82), s(x) + tw + s(28), s(120)], radius=s(19), fill=rgb("#BDE8F5" if kind == "BTO" else "#FFD3B5"))
    d.text((s(x + 14), s(87)), kind, font=fTag, fill=INK)
    y = 140
    size = 58
    while size > 38:
        fName = font("Fraunces-SemiBold.ttf", s(size))
        lines = wrap(d, name, fName, s(540), maxlines=9)
        if len(lines) <= 2:
            break
        size -= 4
    for line in wrap(d, name, fName, s(540)):
        d.text((s(x), s(y)), line, font=fName, fill=INK)
        y += round(size * 1.14)
    y += 8
    if pct is not None:
        big = f"{round(pct)}%"
        d.text((s(x - 4), s(y - 10)), big, font=fBig, fill=INK)
        bw = d.textlength(big, font=fBig) / S
        d.text((s(x + bw + 16), s(y + 38)), "of the wait", font=fTxt, fill=MUTED)
        d.text((s(x + bw + 16), s(y + 72)), "to keys is over", font=fTxt, fill=MUTED)
        y += 132
        d.rounded_rectangle([s(x), s(y), s(620), s(y + 18)], radius=s(9), fill=rgb("#EFE7DA"))
        d.rounded_rectangle([s(x), s(y), s(x + max(18, (620 - x) * min(pct, 100) / 100)), s(y + 18)], radius=s(9), fill=rgb("#62C07A"))
        y += 40
    d.text((s(x), s(y)), when_label, font=fTxt, fill=MUTED)
    d.text((s(x), s(528)), "TOP Already?", font=fSmall, fill=INK)
    d.text((s(x) + d.textlength("TOP Already?  ", font=fSmall), s(528)), "site photos from people nearby", font=font("Figtree-Medium.ttf", s(22)), fill=MUTED)
    im = im.resize((W, H), Image.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, "PNG", optimize=True)
