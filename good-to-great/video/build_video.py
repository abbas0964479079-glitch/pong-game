#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يَبني فيديو «من الجيد إلى العظيم» (1080p) من:
  - التعليق الصوتي voiceover/full-narration.mp3
  - الصور التوضيحية images/
  - نصوص المشاهد voiceover/scene-*.txt

المخرجات: video/out/good-to-great-1080p.mp4  + صور مصغّرة للثامبنيل
"""
import re, subprocess, sys, time
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

VID = Path(__file__).resolve().parent
ROOT = VID.parent
OUT = VID / "out"
OUT.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1920, 1080, 30
BG_STEP = 4                                # تحديث الخلفية كل 3 إطارات (10Hz) — تقريب Ken Burns بطيء
PAUSE = 0.8
TOTAL_AUDIO = 651.5
OUTRO = 9.0
OUTRO_CACHE = {}
TOTAL = TOTAL_AUDIO + OUTRO

GOLD   = (233, 185, 73)
TEAL   = (46, 196, 182)
INK    = (238, 243, 255)
MUTED  = (150, 162, 190)
RED    = (255, 107, 107)
FONT_PATH = VID / "fonts" / "NotoSansArabic[wdth,wght].ttf"
_FC = {}

# ------------------------------------------------------------------ helpers
def font(size, weight=400):
    k = (size, weight)
    if k not in _FC:
        f = ImageFont.truetype(str(FONT_PATH), size)
        try: f.set_variation_by_axes([weight, 100])     # [Weight, Width]
        except Exception: pass
        _FC[k] = f
    return _FC[k]

def ar(t):
    return get_display(arabic_reshaper.reshape(t))

def wrap(text, f, maxw, draw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(ar(t), font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def rounded(size, radius, fill, border=None, bw=3):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0]-1, size[1]-1], radius=radius, fill=fill,
                        outline=border, width=bw)
    return img

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x):  return 1 - (1 - x) ** 3
def ease_io(x):   return 3*x*x - 2*x*x*x

# ------------------------------------------------------------------ static layers
def build_static_overlay():
    """تعتيم الأطراف + تدرّج أعلى وأسفل — طبقة واحدة تُدمج مع الخلفية"""
    top = Image.new("L", (1, H), 0)
    bot = Image.new("L", (1, H), 0)
    for y in range(H):
        if y < H * 0.30:
            top.putpixel((0, y), int(165 * (1 - y / (H*0.30)) ** 1.5))
        if y > H * 0.55:
            bot.putpixel((0, y), int(205 * ((y - H*0.55) / (H*0.45)) ** 1.7))
    lay = Image.new("RGBA", (W, H), (4, 7, 18, 0))
    a_top = top.resize((W, H))
    a_bot = bot.resize((W, H))
    a = Image.new("L", (W, H))
    a.paste(a_top, (0, 0))
    a = Image.fromarray(__import__("numpy").maximum(
        __import__("numpy").asarray(a), __import__("numpy").asarray(a_bot)).astype("uint8"))
    lay.putalpha(a)
    # تعتيم حواف دائري خفيف
    vig = Image.new("L", (W, H), 0)
    dv = ImageDraw.Draw(vig)
    steps = 220
    for i in range(steps):
        val = int(150 * (1 - i / steps) ** 3)
        dv.rectangle([i*2, i, W-1-i*2, H-1-i], outline=val)
    vig = vig.filter(ImageFilter.GaussianBlur(60))
    base = Image.new("RGBA", (W, H), (4, 7, 18, 255)); base.putalpha(vig)
    return Image.alpha_composite(base, lay)

STATIC = build_static_overlay()

def make_chip(text, size=38, weight=700, tcolor=INK, fill=(10, 15, 32, 208), border=GOLD):
    f = font(size, weight)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    box = tmp.textbbox((0, 0), ar(text), font=f)
    tw, th = box[2]-box[0], box[3]-box[1]
    w, h = tw + 68, th + 44
    img = rounded((w, h), h//2, fill, border + (150,), 3)
    ImageDraw.Draw(img).text((w//2, h//2 - 6), ar(text), font=f, fill=tcolor + (255,), anchor="mm")
    return img

def make_stat(vtxt, label, color=GOLD, sub=None):
    fv, fl, fs = font(112, 900), font(36, 600), font(29, 500)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    vw = tmp.textlength(ar(vtxt), font=fv)
    lw = tmp.textlength(ar(label), font=fl)
    sw = tmp.textlength(ar(sub), font=fs) if sub else 0
    w = int(max(720, vw + 150, lw + 100, sw + 100))
    h = 150 + (48 if sub else 0) + 96
    img = rounded((w, h), 34, (9, 13, 28, 214), (255, 255, 255, 30), 2)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 10, 8, h-10], fill=color + (255,))
    d.text((w - 46, 30), ar(vtxt), font=fv, fill=color + (255,), anchor="ra")
    d.text((w - 46, 150), ar(label), font=fl, fill=INK + (255,), anchor="ra")
    if sub:
        d.text((w - 46, 150 + 52), ar(sub), font=fs, fill=MUTED + (255,), anchor="ra")
    return img

def make_caption(text, maxw=1460):
    for size in (56, 52, 48, 44, 40):
        f = font(size, 700)
        tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        lines = wrap(text, f, maxw, tmp)
        if len(lines) <= 2: break
    lh = size + 28
    h = len(lines) * lh + 42
    img = Image.new("RGBA", (maxw + 80, h), (0, 0, 0, 0))
    img.alpha_composite(rounded((maxw + 80, h), 26, (6, 9, 22, 208)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([maxw + 80 - 15, 20, maxw + 80 - 9, h - 20], radius=3, fill=GOLD + (255,))
    y = 21
    for ln in lines:
        d.text((maxw + 80 - 48, y), ar(ln), font=f, fill=INK + (255,), anchor="ra")
        y += lh
    return img

def make_title_chip(no, title, tc):
    t1, t2 = f"المشهد {no} • {title}", tc
    f1, f2 = font(38, 800), font(30, 600)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    w1, h1 = tmp.textlength(ar(t1), font=f1), 46
    w2 = tmp.textlength(ar(t2), font=f2)
    w, h = int(max(w1, w2)) + 74, 128
    img = rounded((w, h), 26, (9, 13, 28, 205), (233, 185, 73, 120), 3)
    d = ImageDraw.Draw(img)
    d.text((37, 20), ar(t1), font=f1, fill=GOLD + (255,))
    d.text((37, 76), ar(t2), font=f2, fill=MUTED + (255,))
    return img

# ------------------------------------------------------------------ timing
def clip_durations():
    d = {}
    for p in sorted((ROOT / "voiceover").glob("scene-*.mp3")):
        out = subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
        h, mi, s = m.groups()
        d[p.stem] = int(h)*3600 + int(mi)*60 + float(s)
    return d

DUR = clip_durations()
ORDER = list(DUR.keys())
STARTS, _t = [], 0.0
for n in ORDER:
    STARTS.append(_t); _t += DUR[n] + PAUSE

def scene_index(t):
    i = 0
    for k, s in enumerate(STARTS):
        if t >= s - 1e-6: i = k
    return i

SCENE_META = [
    dict(title="الهوك: صيدلية مملة تهزم الجميع", img="01-thumbnail-hook.png"),
    dict(title="تجربة 1435 شركة",                img="02-study-1435.png"),
    dict(title="الأول «مين» ثم «إيه»",           img="05-bus-first-who.png"),
    dict(title="المستوى الخامس",                 img="03-kimberly-clark.png",
         img2="04-level5-window-mirror.png", switch=95.0),
    dict(title="مواجهة الحقائق المرّة",          img="06-stockdale-facts.png"),
    dict(title="مفهوم القنفذ",                   img="07-hedgehog-three-circles.png"),
    dict(title="الانضباط والدولاب",              img="08-flywheel.png"),
    dict(title="الطفرة تبدأ منك",                img="09-the-leap.png"),
]

EVENTS = {
 0: [("chip", 0.6, 5.2, "من الجيد إلى العظيم — جيم كولينز"),
     ("stat", 4.2, 7.0, dict(a="1", b="15", suffix="×", label="تفوّق على السوق الأميركي")),
     ("chip", 13.5, 5.0, "40 سنة… عادية تمامًا"),
     ("stat", 20.5, 6.5, dict(a="0", b="1435", label="شركة خضعت للدراسة")),
     ("chip", 28.5, 5.5, "ونجحت 11 شركة فقط"),
     ("chip", 34.5, 5.5, "القائد العبقري؟ ليس السبب"),
     ("chip", 48.5, 6.0, "السبب: الرضا بالجيد")],
 1: [("stat", 5.0, 6.5, dict(a="0", b="1435", label="شركة… و40 سنة من الأرقام")),
     ("chip", 15.0, 6.0, "شرطان قاسيان للدخول في الدراسة"),
     ("stat", 34.5, 6.0, dict(a="1435", b="11", label="فقط نجحت في الطفرة", value_color=TEAL)),
     ("chip", 42.0, 5.5, "عشر من 11 قائدًا من داخل الشركة"),
     ("chip", 48.5, 4.5, "لا حوافز خارقة… ولا استراتيجية سحرية")],
 2: [("chip", 3.5, 6.0, "1981: خسارة مليون دولار كل يوم"),
     ("stat", 4.0, 6.5, dict(a="1000000", b="0", prefix="−",
                             label="خسارة كل يوم عمل في فاني ماي", value_color=RED)),
     ("chip", 18.5, 7.0, "ديفيد ماكسويل: «مين» قبل «إيه»"),
     ("chip", 30.0, 6.5, "الناس الصح… هم أهم مورد"),
     ("stat", 40.5, 7.0, dict(a="0", b="4000000", prefix="+",
                             label="ربح كل يوم عمل بعد 9 سنوات", value_color=TEAL)),
     ("chip", 50.0, 6.0, "الأول: مين… ثم: إيه")],
 3: [("chip", 2.0, 7.0, "1971: داروين سميث… محامٍ هادئ"),
     ("chip", 15.0, 6.5, "«لم يكن مادة رئيس تنفيذي»"),
     ("chip", 24.0, 7.0, "القرار: يبيع مطاحن الورق كلها"),
     ("chip", 36.0, 6.0, "الصحافة: حماقة… والسهم يهبط"),
     ("stat", 45.0, 7.0, dict(a="0", b="25", suffix=" سنة", label="ثم اشترت سكوت بيبر بالكامل")),
     ("chip", 54.0, 6.0, "هزمت بروكتر آند غامبل في 6 من 8 فئات"),
     ("chip", 63.0, 7.0, "1985: سرطان… سنة واحدة للعيش"),
     ("chip", 72.0, 7.0, "مدير الشغل العادي: عاش 19 سنة أخرى"),
     ("chip", 82.0, 8.0, "«لم أتوقف عن محاولة أن أكون مؤهلًا»"),
     ("chip", 92.0, 6.0, "المستوى الخامس: تواضع + إرادة نار"),
     ("chip", 99.0, 6.5, "انظر من الشباك للفضل… وفي المرآة للحساب")],
 4: [("chip", 2.0, 6.5, "مفارقة ستوكدايل"),
     ("chip", 13.0, 6.5, "7 سنوات أسيرًا… وتعذيب"),
     ("chip", 24.0, 6.5, "السؤال: مَن مات في المعسكر؟"),
     ("chip", 29.0, 8.0, "الجواب: «المتفائلون»"),
     ("chip", 46.0, 7.0, "إيمان ثابت + حقائق قاسية"),
     ("chip", 60.0, 6.0, "الجدال المسموح: نوكور"),
     ("chip", 68.0, 7.0, "الإدارة تحملت أكبر نصيب من الألم"),
     ("chip", 78.0, 7.0, "شجاعة: انظر للواقع… وقل سأكسب")],
 5: [("chip", 3.0, 6.5, "القنفذ: حيلة واحدة بامتياز"),
     ("chip", 22.0, 7.0, "1) ما يمكن أن نكون الأفضل فيه"),
     ("chip", 37.0, 7.0, "2) المحرك الاقتصادي: رقم واحد"),
     ("chip", 51.0, 7.0, "3) شغف حقيقي"),
     ("chip", 60.0, 6.0, "التقاطع… بوصلة القرارات"),
     ("chip", 66.0, 7.0, "وولجرينز: رِبح لكل زيارة عميل"),
     ("chip", 78.0, 7.0, "9 فروع في مربع ميل واحد"),
     ("chip", 87.0, 6.5, "خرجت من الأكل واللوجستيات: ليست دوائرها"),
     ("chip", 93.0, 6.5, "قائمة: «أبطّل أعمل إيه»", "gold")],
 6: [("chip", 2.0, 6.5, "الانضباط… لا التسلّط"),
     ("chip", 20.0, 6.5, "حرية كاملة داخل إطار واضح"),
     ("chip", 32.0, 6.5, "لا ضربة واحدة… ولا حفل إطلاق"),
     ("chip", 60.0, 6.5, "الدولاب الثقيل: دفع… دفع… انطلاق"),
     ("chip", 74.0, 7.0, "دوامة الانهيار: رئيس جديد كل مرة"),
     ("chip", 84.0, 7.0, "التكنولوجيا مُسرّع… لا محرّك")],
 7: [("chip", 1.5, 6.0, "الكتاب ليس عن الشركات… بل عنك"),
     ("chip", 12.0, 6.0, "مين حواليك… قبل إيه اللي تعمله"),
     ("chip", 20.0, 6.0, "تواضع + إرادة نار"),
     ("chip", 28.0, 6.0, "واجه حقائقك… بلا هروب"),
     ("chip", 36.0, 6.0, "اعرف نقطة تقاطع دوائرك"),
     ("chip", 44.0, 6.0, "انضباط طويل النفس"),
     ("chip", 52.0, 5.0, "العجلة تفشل أولًا… وتنجح أخيرًا"),
     ("chip", 57.0, 4.0, "اكتب في التعليقات: أبطّل إيه؟", "gold")],
}

# ------------------------------------------------------------------ assets
SRC = {}
for m in SCENE_META:
    for k in ("img", "img2"):
        if m.get(k) and m[k] not in SRC:
            im = Image.open(ROOT / "images" / m[k]).convert("RGB")
            SRC[m[k]] = im.resize((int(W*1.10), int(H*1.10)), Image.LANCZOS)
SRC_SIZE = {k: v.size for k, v in SRC.items()}
ZOOMED = {}                                   # نسخ للتقريب البطيء (فقط عند الحاجة)

def zoom_src(name):
    """خلفية بحجم 1.10 مسبقًا (تكفي 10% تقريبًا)"""
    return SRC[name]

TITLE_CHIPS = [make_title_chip(i+1, m["title"],
               f"{int(STARTS[i]//60):02d}:{int(STARTS[i]%60):02d}") for i, m in enumerate(SCENE_META)]

CAPS = []
for i, name in enumerate(ORDER):
    num = name.split("-")[1]
    lines = [l.strip() for l in (ROOT / "voiceover" / f"scene-{num}.txt")
             .read_text(encoding="utf-8").split("\n") if l.strip()]
    tot = sum(len(l) for l in lines)
    cur, span = STARTS[i], DUR[name] + PAUSE
    for l in lines:
        d = span * (len(l) / tot)
        CAPS.append(dict(t0=cur, t1=cur + d, layer=make_caption(l), scene=i))
        cur += d

EV = {}
STAT_CACHE = {}
for si, items in EVENTS.items():
    lst = []
    for it in items:
        kind, t0, dur, data = it[0], it[1], it[2], it[3]
        if kind == "chip":
            lst.append(dict(kind="chip", t0=t0, t1=t0 + dur,
                            layer=make_chip(data, tcolor=GOLD if len(it) > 4 and it[4] == "gold" else INK)))
        else:
            dd = dict(data)
            dd["a"], dd["b"] = float(dd["a"]), float(dd["b"])
            lst.append(dict(kind="stat", t0=t0, t1=t0 + dur, d=dd))
    EV[si] = lst

WM = ar("من الجيد إلى العظيم • جيم كولينز")
WM_FONT = font(26, 600)
FADE = {}
def faded(layer, a):
    """نسخة بشفافية مخفّضة (مُخزّنة، بلا أخطاء عند تفريغ الذاكرة)"""
    if a >= 0.995: return layer
    k = (id(layer), int(a * 14), layer.width, layer.height)
    ent = FADE.get(k)
    if ent is not None and ent[0] is layer:
        return ent[1]
    c = layer.copy()
    c.putalpha(c.getchannel("A").point(lambda q: int(q * a)))
    if len(FADE) > 1500: FADE.clear()
    FADE[k] = (layer, c)
    return c

def stat_for(e, t):
    d = e["d"]
    p = clamp((t - e["t0"]) / min(3.0, (e["t1"] - e["t0"]) * 0.6))
    cur = d["a"] + (d["b"] - d["a"]) * ease_out(p)
    if abs(cur) >= 100000:
        vtxt = f"{d.get('prefix','')}{int(round(cur)):,}"
    else:
        vtxt = f"{d.get('prefix','')}{int(round(cur))}{d.get('suffix','')}"
    key = (vtxt, d["label"], d.get("value_color", GOLD))
    if key not in STAT_CACHE:
        STAT_CACHE[key] = make_stat(vtxt, d["label"], d.get("value_color", GOLD), d.get("sub"))
        if len(STAT_CACHE) > 900: STAT_CACHE.clear()
    return STAT_CACHE[key]

BG_CACHE = {}
def background(fi, t):
    """خلفية مُدمجة مع التدرجات — تُحسب كل BG_STEP إطارات"""
    key = fi // BG_STEP
    if key in BG_CACHE: return BG_CACHE[key]
    si = scene_index(t)
    meta = SCENE_META[si]
    name = meta["img"]
    local = t - STARTS[si]
    if meta.get("img2") and local >= meta["switch"]:
        name = meta["img2"]
        prog = clamp((local - meta["switch"]) / max(DUR[ORDER[si]] - meta["switch"], 1))
    else:
        prog = clamp(local / max(DUR[ORDER[si]], 1))
    src = SRC[name]
    sw, sh = SRC_SIZE[name]
    k = 1.0 + 0.05 * (1.0 - prog)        # prog=0 -> أوسع لحظة، prog=1 -> أقرب
    cw, ch = W * k, H * k
    ox = (sw - cw) / 2 + (0.5 - prog) * 60
    oy = (sh - ch) / 2 + (0.5 - prog) * 34
    bg = src.crop((int(ox), int(oy), int(ox + cw), int(oy + ch))).resize((W, H), Image.BILINEAR)
    bg = Image.alpha_composite(bg.convert("RGBA"), STATIC).convert("RGB")
    if len(BG_CACHE) > 6: BG_CACHE.clear()
    BG_CACHE[key] = bg
    return bg

# ------------------------------------------------------------------ frame
def render(t):
    fi = int(round(t * FPS))
    si = scene_index(t)
    local = t - STARTS[si]
    frame = background(fi, t).copy()

    # شريط المشهد (أول 7 ثوان من المشهد)
    if local < 7.2:
        a = clamp(min(local / 0.8, (7.2 - local) / 0.8))
        if a > 0.01:
            lay = faded(TITLE_CHIPS[si], a)
            off = int((1 - ease_out(clamp(local / 0.8))) * 70)
            frame.paste(lay, (W - lay.width - 56 + off, 44), lay)

    # الرسوم المتحركة
    for e in EV.get(si, []):
        if not (e["t0"] <= t <= e["t1"]): continue
        a = clamp(min((t - e["t0"]) / 0.45, (e["t1"] - t) / 0.45))
        if a <= 0.01: continue
        lay = e["layer"] if e["kind"] == "chip" else stat_for(e, t)
        lay = faded(lay, a)
        off = int((1 - ease_out(clamp((t - e["t0"]) / 0.5))) * 56)
        frame.paste(lay, (90 + off, 168), lay)

    # الترجمة
    for c in CAPS:
        if c["scene"] != si: continue
        if c["t0"] - 0.25 <= t <= c["t1"] + 0.25:
            a = clamp(min((t - c["t0"]) / 0.3, (c["t1"] - t) / 0.3))
            if a > 0.01:
                lay = faded(c["layer"], a)
                frame.paste(lay, ((W - lay.width)//2, H - lay.height - 40), lay)
            break

    d = ImageDraw.Draw(frame)
    d.text((56, H - 66), WM, font=WM_FONT, fill=(146, 158, 186))
    pw = int(W * clamp(t / TOTAL))
    d.rectangle([0, H - 5, pw, H], fill=GOLD)

    # كارت الختام
    if t > TOTAL_AUDIO:
        if "chip" not in OUTRO_CACHE:
            OUTRO_CACHE["chip"] = make_chip("اشترك في القناة • واكتب: أبطّل إيه؟", size=46, tcolor=GOLD)
            OUTRO_CACHE["f1"] = font(92, 900); OUTRO_CACHE["f2"] = font(44, 600); OUTRO_CACHE["f3"] = font(34, 600)
            OUTRO_CACHE["t1"] = ar("من الجيد إلى العظيم")
            OUTRO_CACHE["t2"] = ar("جيم كولينز — Good to Great")
            OUTRO_CACHE["t3"] = ar("الحلقة القادمة: تكملة القصة")
        p = clamp((t - TOTAL_AUDIO) / 1.1)
        card = Image.new("RGBA", (W, H), (6, 9, 22, int(220 * p)))
        frame = Image.alpha_composite(frame.convert("RGBA"), card)
        a = int(255 * p)
        cd = ImageDraw.Draw(frame)
        cd.text((W//2, 350), OUTRO_CACHE["t1"], font=OUTRO_CACHE["f1"], fill=GOLD + (a,), anchor="mm")
        cd.text((W//2, 468), OUTRO_CACHE["t2"], font=OUTRO_CACHE["f2"], fill=INK + (a,), anchor="mm")
        chip = faded(OUTRO_CACHE["chip"], p)
        frame.paste(chip, ((W - chip.width)//2, 560), chip)
        cd = ImageDraw.Draw(frame)
        cd.text((W//2, 740), OUTRO_CACHE["t3"], font=OUTRO_CACHE["f3"], fill=MUTED + (a,), anchor="mm")
        return frame.convert("RGB")
    return frame

# ------------------------------------------------------------------ build
def build(sample=None, stills=None):
    if stills:
        for s in stills:
            render(s).save(OUT / f"still_{s:07.1f}.png")
            print("still:", OUT / f"still_{s:07.1f}.png", flush=True)
        return
    nframes = int(TOTAL * FPS) if not sample else sample
    audio = OUT / "audio.m4a"
    if not audio.exists():
        subprocess.run([FF, "-y", "-i", str(ROOT / "voiceover" / "full-narration.mp3"),
                        "-af", "apad", "-t", f"{TOTAL:.2f}", "-c:a", "aac", "-b:a", "192k",
                        str(audio)], capture_output=True)
    dst = OUT / ("good-to-great-1080p.mp4" if not sample else "_sample.mp4")
    cmd = [FF, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(audio), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    for i in range(nframes):
        proc.stdin.write(render(i / FPS).tobytes())
        if i and i % 300 == 0:
            el = time.time() - t0
            print(f"  frame {i}/{nframes} ({100*i/nframes:.1f}%)  {el:.0f}s  "
                  f"ETA {el/i*(nframes-i):.0f}s", flush=True)
    proc.stdin.close(); proc.wait()
    print(f"DONE {time.time()-t0:.0f}s -> {dst} ({dst.stat().st_size/1024/1024:.1f} MB)", flush=True)

THUMBS = [("thumbnail-15x", 6.5), ("thumbnail-1435", 40.0), ("thumbnail-outro", 656.0)]

def thumbnails():
    for name, t in THUMBS:
        render(t).resize((1280, 720), Image.LANCZOS).save(OUT / f"{name}.jpg", quality=92)
        print("thumb:", OUT / f"{name}.jpg", flush=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"
    if cmd == "sample":
        build(sample=int(sys.argv[2]) if len(sys.argv) > 2 else 90)
    elif cmd == "stills":
        build(stills=[float(x) for x in sys.argv[2:]])
    elif cmd == "thumbs":
        thumbnails()
    else:
        build()
        thumbnails()
