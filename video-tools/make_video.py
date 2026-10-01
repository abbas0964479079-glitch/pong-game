"""Builds the "رحلة التغيير" video from narration clips + background images.

Usage: python make_video.py <work_dir> <output.mp4>
work_dir must contain audio/s1..s6.mp3, bg/b1..b6.jpg and a Arabic-capable font
(falls back to DejaVu Sans).
"""
import math, re, struct, subprocess, sys, wave, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

WORK, OUT = sys.argv[1], sys.argv[2]
FF = open(os.path.join(WORK, "ff.txt")).read().strip()
W, H, FPS = 1280, 720, 24
SR = 44100
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
GOLD, CYAN, PINK, WHITE = (255, 215, 0), (0, 212, 255), (255, 0, 110), (245, 245, 250)

def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, size)

_reshaper = arabic_reshaper.ArabicReshaper()
def shape(t):
    return get_display(_reshaper.reshape(t))

def text_w(t, f):
    return f.getlength(shape(t))

def wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if text_w(trial, f) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def draw_rtl(d, text, f, right, y, fill, shadow=True):
    s = shape(text)
    x = right - f.getlength(s)
    if shadow:
        d.text((x + 2, y + 2), s, font=f, fill=(0, 0, 0, 200))
    d.text((x, y), s, font=f, fill=fill)

def draw_center(d, text, f, cy, fill, shadow=True):
    s = shape(text)
    x = (W - f.getlength(s)) / 2
    if shadow:
        d.text((x + 3, cy + 3), s, font=f, fill=(0, 0, 0, 220))
    d.text((x, cy), s, font=f, fill=fill)

def dur(path):
    r = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])

# ---------------- content ----------------
SCENES = [
 dict(title="المقدمة", key="تطوير الذات", sub="عملية مستمرة لحياة أكثر إشباعاً", color=GOLD,
      text="هل شعرت يوماً أنك تمتلك قدرات أكبر مما تستخدمه الآن؟ هل سألت نفسك لماذا يصل البعض إلى أهدافهم بسرعة، بينما يظل الآخرون في مكانهم لسنوات؟ السر ليس في الحظ، بل في كلمة واحدة: تطوير الذات. تطوير الذات ليس مجرد تريند أو كلمات تحفيزية، بل هو عملية مستمرة لتحسين مهاراتك، وطريقة تفكيرك، وسلوكك، لتعيش حياة أكثر إشباعاً.",
      key_at="تطوير الذات."),
 dict(title="الثقة والصحة النفسية", key="الثقة تأتي من الإنجازات الصغيرة", sub=None, color=CYAN,
      text="أول ثمرة تحصدها من تطوير ذاتك هي التصالح مع نفسك. عندما تتعلم كيف تدير مشاعرك، وكيف تضع حدوداً صحية في علاقاتك، تزداد ثقتك بنفسك. الثقة لا تأتي من فراغ، بل تأتي من الإنجازات الصغيرة. كل كتاب تقرؤه، وكل مهارة تتعلمها، تخبر عقلك الباطن بأنك شخص قادر على التغيير، وهذا يقلل من التوتر والقلق تجاه المستقبل.",
      key_at="الثقة لا تأتي"),
 dict(title="النجاح المهني والمادي", key="التعلم المستمر", sub="العملة الوحيدة المضمونة", color=GOLD,
      text="في سوق عمل يتغير كل ثانية بفضل الذكاء الاصطناعي والتكنولوجيا، أصبح التعلم المستمر هو العملة الوحيدة المضمونة. الشخص الذي يتوقف عن تطوير نفسه هو في الحقيقة يتراجع للخلف. تطوير مهاراتك، سواء كانت تقنية أو مهارات ناعمة كالتواصل والقيادة، يجعلك قيمة مضافة في أي مكان تتواجد فيه، وهذا ينعكس مباشرة على دخلك المادي وفرصك في الترقي.",
      key_at="أصبح التعلم"),
 dict(title="خارطة الطريق: كيف تبدأ؟", key=None, sub=None, color=CYAN,
      text="لكي لا تشعر بالتشتت، إليك هذه الخطة البسيطة. أولاً، الوعي الذاتي: حدد نقاط قوتك ونقاط ضعفك بصدق. ثانياً، القراءة الواعية: لا تقرأ لمجرد القراءة، بل اقرأ لتعالج مشكلة تواجهها. ثالثاً، تعلم لغة أو مهارة جديدة: خصص ثلاثين دقيقة يومياً فقط. رابعاً، مرافقة الناجحين: أنت متوسط أكثر خمسة أشخاص تقضي وقتك معهم، فاخترهم بعناية.",
      items=[("أولاً،", "الوعي الذاتي", "حدد نقاط قوتك وضعفك بصدق"),
             ("ثانياً،", "القراءة الواعية", "اقرأ لتعالج مشكلة تواجهها"),
             ("ثالثاً،", "مهارة جديدة", "30 دقيقة يومياً فقط"),
             ("رابعاً،", "مرافقة الناجحين", "اختر من حولك بعناية")]),
 dict(title="تحطيم القيود", key="ابدأ وأنت خائف", sub="التسويف مقبرة الأحلام", color=PINK,
      text="أكبر عدو لتطوير الذات هو منطقة الراحة. ستسمع صوتاً داخلك يقول: لست مستعداً بعد، أو: الوقت فات. الحقيقة هي أنك لن تشعر أبداً بأنك مستعد بنسبة مئة بالمئة. السر هو أن تبدأ وأنت خائف، أن تبدأ وأنت غير مكتمل. التسويف هو مقبرة الأحلام، والخطوة الأولى هي دائماً الأصعب، ولكنها الأهم.",
      key_at="السر هو"),
 dict(title="الخاتمة", key="أنت المشروع الأهم في حياتك", sub=None, color=GOLD,
      text="في النهاية، تذكر أن أعظم استثمار يمكنك القيام به في حياتك ليس في الأسهم أو العقارات، بل هو الاستثمار في عقلك وشخصيتك. أنت المشروع الأهم في حياتك، فلا تهمله. أخبروني في التعليقات: ما هي المهارة التي ستبدأون بتعلمها من اليوم؟",
      key_at="أنت المشروع"),
]
INTRO, GAP, OUTRO = 4.5, 0.6, 7.0

def chunks(text, maxc=62):
    parts = re.findall(r"[^.؟،:]+[.؟،:]?", text)
    out, cur = [], ""
    for p in parts:
        p = p.strip()
        if cur and len(cur) + len(p) > maxc:
            out.append(cur); cur = p
        else:
            cur = (cur + " " + p).strip()
        if cur.endswith((".", "؟")):
            out.append(cur); cur = ""
    if cur: out.append(cur)
    return out

# ---------------- timeline ----------------
t = INTRO
for i, s in enumerate(SCENES):
    s["audio"] = f"{WORK}/audio/s{i+1}.mp3"
    s["bg"] = Image.open(f"{WORK}/bg/b{i+1}.jpg").convert("RGB")
    s["dur"] = dur(s["audio"])
    s["start"] = t
    n = len(s["text"])
    pos, subs = 0, []
    for c in chunks(s["text"]):
        idx = s["text"].find(c, pos)
        subs.append((s["start"] + 0.05 + s["dur"] * idx / n,
                     s["start"] + 0.05 + s["dur"] * (idx + len(c)) / n, c))
        pos = idx + len(c)
    s["subs"] = subs
    if s.get("key_at"):
        s["key_t"] = s["start"] + s["dur"] * s["text"].find(s["key_at"]) / n
    if s.get("items"):
        s["item_t"] = [s["start"] + s["dur"] * s["text"].find(it[0]) / n for it in s["items"]]
    t += s["dur"] + GAP
END_SCENES = t
TOTAL = t + OUTRO - GAP
print("total", TOTAL)

# ---------------- overlays ----------------
def rgba():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def vignette():
    v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(v)
    for y in range(H):
        a = int(90 + 125 * (y / H) ** 3)
        d.line([(0, y), (W, y)], fill=(8, 10, 28, min(a, 215)))
    return v
VIG = vignette()

def sub_layer(text):
    L = rgba(); d = ImageDraw.Draw(L)
    f = font(36)
    lines = wrap(text, f, W - 220)
    h = len(lines) * 56 + 30
    y0 = H - 50 - h
    d.rounded_rectangle((90, y0, W - 90, y0 + h), 18, fill=(5, 8, 25, 170))
    for i, ln in enumerate(lines):
        draw_center(d, ln, f, y0 + 15 + i * 56, WHITE, shadow=False)
    return L

def header_layer(sc, idx):
    L = rgba(); d = ImageDraw.Draw(L)
    col = sc["color"]
    d.rounded_rectangle((W - 70, 42, W - 58, 118), 6, fill=col)
    draw_rtl(d, f"الجزء {idx+1} من {len(SCENES)}", font(24, False), W - 90, 40, (200, 205, 225))
    draw_rtl(d, sc["title"], font(44), W - 90, 68, WHITE)
    # progress dots
    for k in range(len(SCENES)):
        d.ellipse((60 + k * 28, 52, 74 + k * 28, 66), fill=col if k <= idx else (255, 255, 255, 70))
    return L

def key_layer(sc):
    L = rgba(); d = ImageDraw.Draw(L)
    f = font(78 if len(sc["key"]) < 20 else 62)
    lines = wrap(sc["key"], f, W - 160)
    y = 250 - (len(lines) - 1) * 50 - (30 if sc["sub"] else 0)
    for ln in lines:
        draw_center(d, ln, f, y, sc["color"]); y += 100
    if sc["sub"]:
        draw_center(d, sc["sub"], font(40, False), y + 5, WHITE)
    return L

def item_layer(sc, k):
    L = rgba(); d = ImageDraw.Draw(L)
    num, head, sub = sc["items"][k]
    y = 135 + k * 98
    d.rounded_rectangle((200, y, W - 200, y + 84), 20, fill=(8, 12, 36, 205), outline=sc["color"], width=3)
    d.ellipse((W - 200 - 72, y + 8, W - 200 - 8, y + 72), fill=sc["color"])
    n = str(k + 1)
    d.text((W - 200 - 40 - font(40).getlength(n) / 2, y + 16), n, font=font(40), fill=(10, 12, 30))
    draw_rtl(d, head, font(34), W - 300, y + 4, WHITE, shadow=False)
    draw_rtl(d, sub, font(25, False), W - 300, y + 47, (190, 200, 225), shadow=False)
    return L

def card_layer(title, lines, col):
    L = rgba(); d = ImageDraw.Draw(L)
    return L

INTRO_L = rgba(); d = ImageDraw.Draw(INTRO_L)
draw_center(d, "رحلة التغيير", font(110), 160, GOLD)
draw_center(d, "لماذا يجب أن تستثمر في نفسك؟", font(54), 320, WHITE)
d.rounded_rectangle((W / 2 - 80, 430, W / 2 + 80, 436), 3, fill=CYAN)
draw_center(d, "تطوير الذات", font(34, False), 470, (200, 210, 235))

OUTRO_L = rgba(); d = ImageDraw.Draw(OUTRO_L)
draw_center(d, "شاركنا في التعليقات", font(48, False), 170, CYAN)
draw_center(d, "ما هي المهارة التي ستبدأ", font(70), 270, GOLD)
draw_center(d, "بتعلمها من اليوم؟", font(70), 365, GOLD)
d.rounded_rectangle((W / 2 - 80, 490, W / 2 + 80, 496), 3, fill=PINK)
draw_center(d, "اشترك وفعّل التنبيهات لمزيد من الفيديوهات", font(32, False), 530, WHITE)

cache = {}
def cached(key, fn):
    if key not in cache: cache[key] = fn()
    return cache[key]

# ---------------- frame render ----------------
def alpha_mul(layer, a):
    if a >= 0.999: return layer
    l = layer.copy(); l.putalpha(l.getchannel("A").point(lambda v: int(v * a)))
    return l

def ease(x): return x * x * (3 - 2 * x)
def fadein(t, t0, d=0.5): return max(0.0, min(1.0, (t - t0) / d))

def bg_frame(img, p, mode):
    # slow ken-burns zoom
    z = 1.0 + 0.10 * p if mode == 0 else 1.10 - 0.10 * p
    iw, ih = img.size
    cw, ch = iw / z, ih / z
    cx = iw / 2 + (p - 0.5) * 40 * (1 if mode == 0 else -1)
    x0 = min(max(cx - cw / 2, 0), iw - cw)
    y0 = (ih - ch) / 2
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

def frame(t):
    # which scene
    if t < INTRO:
        base = bg_frame(SCENES[0]["bg"], t / INTRO, 0)
        base = Image.alpha_composite(base, Image.new("RGBA", (W, H), (5, 8, 25, 130)))
        base = Image.alpha_composite(base, alpha_mul(INTRO_L, ease(fadein(t, 0.3, 1.0))))
        return base, min(1, t / 0.6)
    if t >= END_SCENES - GAP + 0.01:
        p = (t - (END_SCENES - GAP)) / OUTRO
        base = bg_frame(SCENES[-1]["bg"], p, 1)
        base = Image.alpha_composite(base, Image.new("RGBA", (W, H), (5, 8, 25, 150)))
        base = Image.alpha_composite(base, alpha_mul(OUTRO_L, ease(fadein(t, END_SCENES - GAP, 0.8))))
        return base, min(1, (TOTAL - t) / 1.2)
    idx = max(i for i, s in enumerate(SCENES) if s["start"] <= t)
    s = SCENES[idx]
    p = min(1, max(0, (t - s["start"]) / (s["dur"] + GAP)))
    base = bg_frame(s["bg"], p, idx % 2)
    base = Image.alpha_composite(base, VIG)
    base = Image.alpha_composite(base, cached(("h", idx), lambda: header_layer(s, idx)))
    if s.get("key") and t >= s["key_t"]:
        base = Image.alpha_composite(base, alpha_mul(cached(("k", idx), lambda: key_layer(s)), ease(fadein(t, s["key_t"], 0.6))))
    for k, it in enumerate(s.get("item_t", [])):
        if t >= it:
            base = Image.alpha_composite(base, alpha_mul(cached(("i", idx, k), lambda: item_layer(s, k)), ease(fadein(t, it, 0.45))))
    for a, b, c in s["subs"]:
        if a <= t < b + 0.0:
            base = Image.alpha_composite(base, cached(("s", c), lambda: sub_layer(c)))
            break
    # fades at scene edges
    f = min(1, (t - s["start"]) / 0.5 + 0.0) if t - s["start"] < 0.5 else 1
    end = s["start"] + s["dur"] + GAP
    if end - t < 0.5 and idx < len(SCENES) - 1: f = (end - t) / 0.5
    return base, f

# ---------------- audio ----------------
def to_wav(src, dst):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(SR), dst], check=True)

def silence(sec): return b"\x00\x00" * int(SR * sec)
buf = silence(INTRO)
for i, s in enumerate(SCENES):
    wp = f"{WORK}/n{i}.wav"; to_wav(s["audio"], wp)
    with wave.open(wp) as w: data = w.readframes(w.getnframes())
    # pad/trim so each scene occupies exactly dur+GAP
    want = int(SR * (s["dur"] + GAP)) * 2
    data = (data + silence(GAP + 1))[:want]
    buf += data
buf += silence(OUTRO)
with wave.open(f"{WORK}/narration.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(buf)

# soft ambient pad (Am - F - C - G), very quiet
def pad(total):
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    seg = 8.0
    out = bytearray()
    n = int(total * SR)
    for i in range(n):
        tt = i / SR
        c = chords[int(tt // seg) % 4]
        ph = (tt % seg) / seg
        env = math.sin(math.pi * ph) ** 0.6
        v = sum(math.sin(2 * math.pi * f * tt) + 0.3 * math.sin(4 * math.pi * f * tt) for f in c) / 3.9
        v += 0.5 * math.sin(2 * math.pi * (c[0] / 2) * tt)
        v *= env * (0.75 + 0.25 * math.sin(2 * math.pi * 0.2 * tt))
        out += struct.pack("<h", int(v * 9000))
    return bytes(out)
with wave.open(f"{WORK}/music.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pad(TOTAL + 1))
subprocess.run([FF, "-y", "-loglevel", "error", "-i", f"{WORK}/narration.wav", "-i", f"{WORK}/music.wav",
    "-filter_complex", f"[1:a]volume=0.55,lowpass=f=1200,afade=t=in:d=2,afade=t=out:st={TOTAL-3}:d=3[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
    "-map", "[a]", f"{WORK}/mix.wav"], check=True)

# ---------------- video ----------------
proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
    "-i", "-", "-i", f"{WORK}/mix.wav", "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "160k", "-t", f"{TOTAL:.2f}", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
black = Image.new("RGB", (W, H), (0, 0, 0))
nf = int(TOTAL * FPS)
for n in range(nf):
    img, f = frame(n / FPS)
    img = img.convert("RGB")
    if f < 0.999: img = Image.blend(black, img, max(0.0, f))
    proc.stdin.write(img.tobytes())
proc.stdin.close(); proc.wait()
print("done", OUT)
