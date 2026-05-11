import pygame
import sys
import os

pygame.init()

# Window 
screen   = pygame.display.set_mode((900, 640), pygame.RESIZABLE)
pygame.display.set_caption("River Crossing Puzzle  –  Lion · Goat · Grass")
clock    = pygame.time.Clock()
FPS      = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#  Colors 
SKY      = (110, 185, 235)
BANK_GR  = (55,  150,  55)
BANK_DK  = (35,  105,  35)
RIVER_C  = (25,   90, 185)
RIVER_HL = (45,  120, 210)
WHITE    = (255, 255, 255)
GOLD     = (255, 200,  50)
RED      = (210,  50,  50)
GRAY     = ( 80,  80,  80)
PANEL_BG = ( 15,  15,  45)
BTN_BLUE = ( 30, 110, 200)
BTN_ORG  = (160,  90,  30)
BTN_RED  = (140,  30,  30)

#  Entities 
ALL = ["Lion", "Goat", "Grass"]

#  Image loading & cache 
def _load(filename):
    return pygame.image.load(os.path.join(BASE_DIR, filename)).convert_alpha()

_RAW = {
    "Lion":  _load("LION.png"),
    "Goat":  _load("GOAT.png"),
    "Grass": _load("GRASS.png"),
    "Boat":  _load("BOAT.png"),
}
_CACHE = {}

def get_img(key, size):
    """Return a smoothscaled image, cached by (key, size)."""
    ckey = (key, size)
    if ckey not in _CACHE:
        _CACHE[ckey] = pygame.transform.smoothscale(_RAW[key], size)
    return _CACHE[ckey]

def get_boat_imgs(size):
    """Return (left-facing, right-facing) boat images at given size."""
    lkey = ("boat_L", size)
    rkey = ("boat_R", size)
    if lkey not in _CACHE:
        _CACHE[lkey] = pygame.transform.smoothscale(_RAW["Boat"], size)
        _CACHE[rkey] = pygame.transform.flip(_CACHE[lkey], True, False)
    return _CACHE[lkey], _CACHE[rkey]

#  Fonts 
def _font(name, size, bold=False):
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

FT_LG = _font("Arial", 28, bold=True)
FT_MD = _font("Arial", 21)
FT_SM = _font("Arial", 17)
FT_XS = _font("Arial", 14)

#  Helpers 
def ease(t):
    return t * t * (3 - 2 * t)

def draw_txt(surf, text, font, color, cx, cy):
    s = font.render(text, True, color)
    r = s.get_rect(center=(cx, cy))
    surf.blit(s, r)
    return r

def draw_btn(surf, label, rect, color, disabled=False):
    col   = GRAY if disabled else color
    t_col = (140, 140, 140) if disabled else WHITE
    b_col = (110, 110, 110) if disabled else WHITE
    pygame.draw.rect(surf, col,   rect, border_radius=10)
    pygame.draw.rect(surf, b_col, rect, 2, border_radius=10)
    draw_txt(surf, label, FT_MD, t_col, rect.centerx, rect.centery)

def draw_entity(surf, entity, cx, cy, active, img_size):
    """Draw entity image + label. Returns clickable Rect."""
    iw, ih = img_size
    img = get_img(entity, img_size)
    img_r = img.get_rect(center=(cx, cy))

    if active:
        # Subtle white glow behind image
        glow = pygame.Surface((iw + 16, ih + 16), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 255, 255, 55), glow.get_rect())
        surf.blit(glow, glow.get_rect(center=(cx, cy)))
        surf.blit(img, img_r)
        draw_txt(surf, entity, FT_SM, WHITE, cx, cy + ih // 2 + 11)
    else:
        # Dimmed: draw at reduced alpha
        faded = img.copy()
        faded.set_alpha(70)
        surf.blit(faded, img_r)
        draw_txt(surf, entity, FT_SM, (80, 80, 80), cx, cy + ih // 2 + 11)

    # Clickable rect covers image + label
    return pygame.Rect(cx - iw // 2, cy - ih // 2, iw, ih + 22)

#  Game state 
class G:
    def __init__(self):
        self.reset()

    def reset(self):
        self.left      = set(ALL)
        self.right     = set()
        self.side      = "left"
        self.passenger = None
        self.moves     = 0
        self.animating = False
        self.anim_t    = 0.0
        self.anim_dir  = "left"
        self.msg       = "Click an entity on the LEFT bank to load it, then press CROSS."
        self.msg_col   = WHITE
        self.won       = False
        self.lost      = False
        self.e_rects   = {}
        self.b_rects   = {}

    def bank(self, s=None):
        s = s if s is not None else self.side
        return self.left if s == "left" else self.right

    def load(self, entity):
        if self.animating or self.won or self.lost:
            return
        if self.passenger:
            self.msg     = "Boat is full! Cross first, or click the passenger to unload."
            self.msg_col = (255, 160, 80)
            return
        b = self.bank()
        if entity not in b:
            return
        b.discard(entity)
        self.passenger = entity
        self.msg       = f"{entity} boarded.  Press CROSS (or Space) to go!"
        self.msg_col   = WHITE

    def unload(self):
        if not self.passenger or self.animating:
            return
        self.bank().add(self.passenger)
        p, self.passenger = self.passenger, None
        self.msg       = f"{p} unloaded onto the {self.side} bank."
        self.msg_col   = WHITE
        self._check()

    def cross(self):
        if self.animating or self.won or self.lost:
            return
        self.anim_dir  = self.side
        self.animating = True
        self.anim_t    = 0.0
        self.moves    += 1

    def _arrive(self):
        self.side      = "right" if self.side == "left" else "left"
        self.animating = False
        self.anim_t    = 0.0
        sl = self.side.upper()
        if self.passenger:
            self.msg = (f"Arrived at {sl} bank with {self.passenger}."
                        f"  Click it (or UNLOAD) to drop off.")
        else:
            self.msg = f"Arrived at {sl} bank (empty).  Load an entity or CROSS again."
        self.msg_col = WHITE
        self._check()

    def _check(self):
        for s in ("left", "right"):
            if s == self.side:
                continue
            b = self.left if s == "left" else self.right
            if "Lion" in b and "Goat" in b:
                self.lost    = True
                self.msg     = f"The Lion ate the Goat on the {s} bank!  Press R to restart."
                self.msg_col = RED
                return
            if "Goat" in b and "Grass" in b:
                self.lost    = True
                self.msg     = f"The Goat ate the Grass on the {s} bank!  Press R to restart."
                self.msg_col = RED
                return
        if len(self.right) == 3 and self.side == "right" and not self.passenger:
            self.won     = True
            self.msg     = f"All three safely crossed in {self.moves} moves!  Brilliant!"
            self.msg_col = GOLD

    def update(self, dt):
        if self.animating:
            self.anim_t = min(1.0, self.anim_t + dt * 1.5)
            if self.anim_t >= 1.0:
                self._arrive()

    def boat_frac(self):
        """0.0 = fully left bank, 1.0 = fully right bank."""
        if not self.animating:
            return 1.0 if self.side == "right" else 0.0
        t = ease(self.anim_t)
        return t if self.anim_dir == "left" else 1.0 - t

    def going_right(self):
        """True while the boat is travelling toward the right bank."""
        return self.animating and self.anim_dir == "left"


#  Scene rendering 
def draw(surf, g):
    SW, SH = surf.get_size()

    # Proportional layout
    bw      = max(150, SW // 4)
    gy      = int(SH * 0.72)
    hud_y   = gy + 10
    hud_h   = SH - hud_y
    boat_xl = bw + max(55, SW // 11)
    boat_xr = SW - bw - max(55, SW // 11)
    boat_y  = gy - 30
    rx      = bw
    rw      = SW - 2 * bw

    # Image sizes derived from layout
    ent_sz     = (max(70, bw * 38 // 100), max(70, bw * 38 // 100))  # entity on bank
    ent_sz_sm  = (max(55, bw * 28 // 100), max(55, bw * 28 // 100))  # entity on boat
    boat_sz    = (max(130, rw * 38 // 100), max(80,  rw * 24 // 100))  # boat image

    surf.fill(SKY)

    # River
    pygame.draw.rect(surf, RIVER_C, (rx, 0, rw, gy + 30))
    for wy in range(20, gy + 30, 45):
        pygame.draw.line(surf, RIVER_HL, (rx, wy), (rx + rw, wy), 1)

    # Banks
    for bx_off in (0, SW - bw):
        pygame.draw.rect(surf, BANK_GR, (bx_off, gy, bw, SH - gy))
        pygame.draw.rect(surf, BANK_DK, (bx_off, gy, bw, 12))

    draw_txt(surf, "LEFT BANK",  FT_SM, (170, 255, 170), bw // 2,      gy - 10)
    draw_txt(surf, "RIGHT BANK", FT_SM, (170, 255, 170), SW - bw // 2, gy - 10)
    draw_txt(surf, "River Crossing Puzzle", FT_LG, WHITE, SW // 2, 22)

    e_rects = {}
    spacing = min(130, max(90, (gy - 80) // 3))

    # Left bank entities
    for i, ent in enumerate(sorted(g.left)):
        cx     = bw // 2
        cy     = 75 + i * spacing
        active = g.side == "left" and not g.animating and not g.won and not g.lost
        e_rects[ent] = draw_entity(surf, ent, cx, cy, active, ent_sz)

    # Right bank entities
    for i, ent in enumerate(sorted(g.right)):
        cx     = SW - bw // 2
        cy     = 75 + i * spacing
        active = g.side == "right" and not g.animating and not g.won and not g.lost
        e_rects[ent] = draw_entity(surf, ent, cx, cy, active, ent_sz)

    # Boat
    frac    = g.boat_frac()
    bx      = int(boat_xl + (boat_xr - boat_xl) * frac)
    boat_L, boat_R = get_boat_imgs(boat_sz)
    boat_img = boat_R if g.going_right() else boat_L
    boat_r   = boat_img.get_rect(center=(bx, boat_y))
    surf.blit(boat_img, boat_r)

    # Passenger sitting on the boat (centred on boat, slightly above)
    if g.passenger:
        pass_cy = boat_y - ent_sz_sm[1] // 2 - 8
        img     = get_img(g.passenger, ent_sz_sm)
        img_r   = img.get_rect(center=(bx, pass_cy))
        surf.blit(img, img_r)
        draw_txt(surf, g.passenger, FT_XS, WHITE, bx, pass_cy + ent_sz_sm[1] // 2 + 9)
        # Clickable rect
        e_rects[g.passenger] = pygame.Rect(
            bx - ent_sz_sm[0] // 2, pass_cy - ent_sz_sm[1] // 2,
            ent_sz_sm[0], ent_sz_sm[1] + 18,
        )

    g.e_rects = e_rects

    #  HUD panel 
    pygame.draw.rect(surf, PANEL_BG, (0, hud_y, SW, hud_h))
    pygame.draw.line(surf, (55, 55, 100), (0, hud_y), (SW, hud_y), 2)

    # Buttons
    btn_y = hud_y + 14
    bh    = 40
    btn_cross  = pygame.Rect(SW // 2 - 170, btn_y, 120, bh)
    btn_unload = pygame.Rect(SW // 2 -  38, btn_y, 120, bh)
    btn_reset  = pygame.Rect(SW // 2 +  94, btn_y, 110, bh)

    busy = g.won or g.lost or g.animating
    draw_btn(surf, "CROSS",  btn_cross,  BTN_BLUE, disabled=busy)
    draw_btn(surf, "UNLOAD", btn_unload, BTN_ORG,
             disabled=(not g.passenger or g.animating or g.won or g.lost))
    draw_btn(surf, "RESET",  btn_reset,  BTN_RED)

    g.b_rects = {"cross": btn_cross, "unload": btn_unload, "reset": btn_reset}

    draw_txt(surf, f"Moves: {g.moves}", FT_MD, (160, 210, 255), 60, btn_y + bh // 2)

    # Message (below buttons)
    msg_y = btn_y + bh + 16
    ms    = FT_MD.render(g.msg, True, g.msg_col)
    mr    = ms.get_rect(center=(SW // 2, msg_y))
    mbs   = pygame.Surface((mr.width + 22, mr.height + 8), pygame.SRCALPHA)
    mbs.fill((0, 0, 0, 130))
    surf.blit(mbs, mbs.get_rect(center=mr.center))
    surf.blit(ms, mr)

    # Controls reminder
    draw_txt(surf, "Space = Cross  |  R = Reset",
             FT_XS, (90, 90, 130), SW // 2, SH - 10)

    # Win / Lose overlay
    if g.won or g.lost:
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surf.blit(ov, (0, 0))
        title = "YOU WIN!" if g.won else "GAME OVER"
        col   = GOLD if g.won else RED
        draw_txt(surf, title,  FT_LG, col,   SW // 2, SH // 2 - 55)
        draw_txt(surf, g.msg,  FT_MD, WHITE, SW // 2, SH // 2 + 5)
        draw_txt(surf, "Press R or click RESET to play again",
                 FT_SM, (180, 180, 180), SW // 2, SH // 2 + 48)


#  Main loop ─
def main():
    g = G()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        g.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    g.reset()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    g.cross()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if g.b_rects.get("reset") and g.b_rects["reset"].collidepoint(mx, my):
                    g.reset()
                    continue

                if g.animating or g.won or g.lost:
                    continue

                hit = False
                for ent, rect in g.e_rects.items():
                    if rect.collidepoint(mx, my):
                        if ent == g.passenger:
                            g.unload()
                        else:
                            g.load(ent)
                        hit = True
                        break

                if not hit:
                    if g.b_rects.get("cross") and g.b_rects["cross"].collidepoint(mx, my):
                        g.cross()
                    elif g.b_rects.get("unload") and g.b_rects["unload"].collidepoint(mx, my):
                        g.unload()

        draw(screen, g)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
