"""
Kalkulator Luas Segitiga - versi wxPython (wx.App, wx.Frame, wx.PaintDC).

  - Tab 1: Luas dari alas dan tinggi       L = 1/2 x alas x tinggi
  - Tab 2: Luas dari tiga sisi (Heron)     L = sqrt(s(s-a)(s-b)(s-c))
  - Gambar segitiga digambar dengan wx.BufferedPaintDC (varian wx.PaintDC
    tanpa kedip), skalanya mengikuti ukuran jendela.

Instal  : pip install wxPython
Jalankan: python luas_segitiga_wx.py
"""
import math
import wx

FACE = "Segoe UI"
BLUE = wx.Colour(11, 92, 173)
DARK = wx.Colour(11, 61, 117)
RED = wx.Colour(192, 57, 43)


def fmt(x):
    """Format angka gaya Indonesia: maksimal 2 desimal, koma sebagai desimal."""
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def font(size, bold=False):
    info = wx.FontInfo(size).FaceName(FACE)
    return wx.Font(info.Bold() if bold else info)


# ======================================================================
#  Panel gambar segitiga
# ======================================================================
class DrawPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent, style=wx.BORDER_SIMPLE)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.pts = ((0, 0), (8, 0), (2.8, 5))
        self.labels = {"base": "alas", "height": "tinggi"}
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def set_triangle(self, pts, labels):
        self.pts, self.labels = pts, labels
        self.Refresh()

    def on_size(self, event):
        self.Refresh()
        event.Skip()

    @staticmethod
    def _text(dc, x, y, s, colour, anchor="c"):
        dc.SetTextForeground(colour)
        tw, th = dc.GetTextExtent(s)
        if anchor == "c":
            x -= tw // 2
        elif anchor == "r":
            x -= tw
        dc.DrawText(s, int(x), int(y - th // 2))

    def on_paint(self, event):
        dc = wx.BufferedPaintDC(self)
        w, h = self.GetClientSize()
        if w < 100 or h < 100:
            return

        # latar gradasi + grid
        dc.GradientFillLinear(wx.Rect(0, 0, w, h), wx.Colour(206, 228, 252),
                              wx.WHITE, wx.SOUTH)
        dc.SetPen(wx.Pen(wx.Colour(214, 230, 247), 1))
        for gx in range(0, w, 32):
            dc.DrawLine(gx, 0, gx, h)
        for gy in range(0, h, 32):
            dc.DrawLine(0, gy, w, gy)

        (ax, ay), (bx, by), (cx, cy) = self.pts
        minx, maxx = min(ax, bx, cx), max(ax, bx, cx)
        maxy = max(cy, 1e-9)
        s = min((w - 180) / max(maxx - minx, 1e-9), (h - 180) / maxy)
        off_x = (w - (maxx - minx) * s) / 2
        base_y = h - (h - maxy * s) / 2

        def P(px, py):
            return int(off_x + (px - minx) * s), int(base_y - py * s)

        A, B, C, F = P(ax, ay), P(bx, by), P(cx, cy), P(cx, 0)

        # bayangan lalu segitiga
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(wx.Colour(183, 196, 212)))
        dc.DrawPolygon([wx.Point(p[0] + 6, p[1] + 6) for p in (A, B, C)])
        dc.SetPen(wx.Pen(BLUE, 3))
        dc.SetBrush(wx.Brush(wx.Colour(127, 180, 242)))
        dc.DrawPolygon([wx.Point(*A), wx.Point(*B), wx.Point(*C)])

        # garis tinggi putus-putus + tanda siku-siku
        mid = (ax + bx) / 2
        d = 12 if cx < mid else -12
        dc.SetPen(wx.Pen(RED, 2, wx.PENSTYLE_SHORT_DASH))
        dc.DrawLine(*C, *F)
        dc.SetPen(wx.Pen(RED, 1))
        dc.DrawLine(F[0] + d, F[1], F[0] + d, F[1] - 12)
        dc.DrawLine(F[0] + d, F[1] - 12, F[0], F[1] - 12)
        if cx < ax or cx > bx:      # segitiga tumpul: perpanjang garis alas
            dc.SetPen(wx.Pen(BLUE, 3))
            dc.DrawLine(*A, *B)

        # titik sudut
        dc.SetFont(font(13, True))
        for (px, py), name, dx, dy in ((A, "A", -16, 8), (B, "B", 16, 8), (C, "C", 0, -16)):
            dc.SetPen(wx.Pen(BLUE, 2))
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.DrawCircle(px, py, 5)
            self._text(dc, px + dx, py + dy, name, DARK)

        # label ukuran
        dc.SetFont(font(12, True))
        lb = self.labels
        if "base" in lb:
            self._text(dc, (A[0] + B[0]) / 2, A[1] + 30, lb["base"], DARK)
            if cx < mid:
                self._text(dc, F[0] + 30, (C[1] + F[1]) / 2, lb["height"], RED, "l")
            else:
                self._text(dc, F[0] - 30, (C[1] + F[1]) / 2, lb["height"], RED, "r")
        if "ab" in lb:
            self._text(dc, (A[0] + B[0]) / 2, A[1] + 30, lb["ab"], DARK)
            self._text(dc, (B[0] + C[0]) / 2 + 28, (B[1] + C[1]) / 2 - 8, lb["bc"], DARK)
            self._text(dc, (A[0] + C[0]) / 2 - 28, (A[1] + C[1]) / 2 - 8, lb["ca"], DARK)

        dc.SetFont(font(11, True))
        self._text(dc, 14, 18, "Visualisasi Segitiga", DARK, "l")


# ======================================================================
#  Jendela utama
# ======================================================================
class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Kalkulator Luas Segitiga (wxPython)",
                         size=(940, 600))
        self.SetMinSize((820, 540))
        self._build_menu()
        self._build_ui()
        self.CreateStatusBar()
        self.SetStatusText("Siap")
        self.Centre()

    # ------------------------------------------------------------ menu
    def _build_menu(self):
        bar = wx.MenuBar()
        m_file = wx.Menu()
        i_reset = m_file.Append(wx.ID_ANY, "&Reset semua\tCtrl+R")
        m_file.AppendSeparator()
        i_exit = m_file.Append(wx.ID_EXIT, "&Keluar\tAlt+F4")
        m_help = wx.Menu()
        i_rumus = m_help.Append(wx.ID_ANY, "&Rumus")
        i_about = m_help.Append(wx.ID_ABOUT, "&Tentang")
        bar.Append(m_file, "&File")
        bar.Append(m_help, "&Bantuan")
        self.SetMenuBar(bar)
        self.Bind(wx.EVT_MENU, lambda e: self.reset_all(), i_reset)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), i_exit)
        self.Bind(wx.EVT_MENU, self.on_rumus, i_rumus)
        self.Bind(wx.EVT_MENU, self.on_about, i_about)

    # -------------------------------------------------------------- UI
    def _build_ui(self):
        base = wx.Panel(self)
        left = wx.Panel(base)
        self.draw_panel = DrawPanel(base)

        root = wx.BoxSizer(wx.HORIZONTAL)
        root.Add(left, 0, wx.EXPAND | wx.ALL, 12)
        root.Add(self.draw_panel, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 12)
        base.SetSizer(root)

        lv = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(left, label="Luas Segitiga")
        title.SetFont(font(14, True))
        lv.Add(title, 0, wx.BOTTOM, 2)
        hint = wx.StaticText(left, label="Pilih metode, isi ukuran, lalu klik Hitung.")
        hint.SetForegroundColour(wx.Colour(85, 85, 85))
        lv.Add(hint, 0, wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(left, label="Satuan:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.unit = wx.Choice(left, choices=["mm", "cm", "m", "km"])
        self.unit.SetSelection(1)
        row.Add(self.unit, 0)
        lv.Add(row, 0, wx.BOTTOM, 8)

        nb = wx.Notebook(left)
        p1, p2 = wx.Panel(nb), wx.Panel(nb)
        nb.AddPage(p1, "Alas && Tinggi")
        nb.AddPage(p2, "Tiga Sisi (Heron)")
        self.e1 = self._make_tab(p1, ["Alas", "Tinggi"], self.hitung_alas_tinggi)
        self.e2 = self._make_tab(p2, ["Sisi a", "Sisi b", "Sisi c"], self.hitung_heron)
        lv.Add(nb, 0, wx.EXPAND)

        box = wx.StaticBoxSizer(wx.VERTICAL, left, "Hasil")
        sb = box.GetStaticBox()
        self.lbl_hasil = wx.StaticText(sb, label="-")
        self.lbl_hasil.SetFont(font(20, True))
        self.lbl_hasil.SetForegroundColour(BLUE)
        self.lbl_detail = wx.StaticText(sb, label="Belum ada perhitungan.", size=(310, -1))
        box.Add(self.lbl_hasil, 0, wx.ALL, 6)
        box.Add(self.lbl_detail, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        lv.Add(box, 0, wx.EXPAND | wx.TOP, 12)

        btn_exit = wx.Button(left, wx.ID_EXIT, "Keluar")
        btn_exit.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        lv.Add(btn_exit, 0, wx.ALIGN_RIGHT | wx.TOP, 12)
        left.SetSizer(lv)

    def _make_tab(self, page, fields, command):
        grid = wx.FlexGridSizer(cols=2, vgap=10, hgap=8)
        grid.AddGrowableCol(1)
        ctrls = []
        for txt in fields:
            grid.Add(wx.StaticText(page, label=txt), 0, wx.ALIGN_CENTER_VERTICAL)
            tc = wx.TextCtrl(page, style=wx.TE_PROCESS_ENTER, size=(130, -1))
            tc.Bind(wx.EVT_TEXT_ENTER, lambda e: command())
            grid.Add(tc, 1, wx.EXPAND)
            ctrls.append(tc)

        b_hit = wx.Button(page, label="Hitung")
        b_rst = wx.Button(page, label="Reset")
        b_hit.Bind(wx.EVT_BUTTON, lambda e: command())
        b_rst.Bind(wx.EVT_BUTTON, lambda e: self.reset_entries(ctrls))
        btns = wx.BoxSizer(wx.HORIZONTAL)
        btns.Add(b_hit, 0, wx.RIGHT, 8)
        btns.Add(b_rst, 0)

        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(grid, 0, wx.EXPAND | wx.ALL, 14)
        sz.Add(btns, 0, wx.ALIGN_CENTER | wx.BOTTOM, 14)
        page.SetSizer(sz)
        return ctrls

    # ------------------------------------------------------ perhitungan
    @staticmethod
    def _num(ctrl, nama):
        s = ctrl.GetValue().strip().replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            raise ValueError(f"{nama} harus berupa angka.")
        if v <= 0:
            raise ValueError(f"{nama} harus lebih besar dari 0.")
        return v

    def _show(self, luas, detail, pts, labels):
        u = self.unit.GetStringSelection()
        self.lbl_hasil.SetLabel(f"{fmt(luas)} {u}²")
        self.lbl_detail.SetLabel(detail.replace("{u}", u))
        self.lbl_detail.GetParent().Layout()
        self.draw_panel.set_triangle(pts, labels)
        self.SetStatusText(f"Luas = {fmt(luas)} {u}²")

    def hitung_alas_tinggi(self):
        try:
            a = self._num(self.e1[0], "Alas")
            t = self._num(self.e1[1], "Tinggi")
        except ValueError as err:
            return self.error(str(err))
        u = self.unit.GetStringSelection()
        luas = 0.5 * a * t
        detail = (f"L = ½ × alas × tinggi\n  = ½ × {fmt(a)} × {fmt(t)}\n"
                  f"  = {fmt(luas)} {{u}}²")
        self._show(luas, detail, ((0, 0), (a, 0), (a * 0.35, t)),
                   {"base": f"alas = {fmt(a)} {u}", "height": f"t = {fmt(t)} {u}"})

    def hitung_heron(self):
        try:
            a = self._num(self.e2[0], "Sisi a")
            b = self._num(self.e2[1], "Sisi b")
            c = self._num(self.e2[2], "Sisi c")
        except ValueError as err:
            return self.error(str(err))
        if a + b <= c or a + c <= b or b + c <= a:
            return self.error("Ketiga sisi tidak membentuk segitiga.\n"
                              "Jumlah dua sisi harus lebih besar dari sisi ketiga.")
        s = (a + b + c) / 2
        luas = math.sqrt(s * (s - a) * (s - b) * (s - c))
        x = (b * b + c * c - a * a) / (2 * c)
        y = math.sqrt(max(b * b - x * x, 0))
        detail = (f"s = (a + b + c) / 2 = {fmt(s)}\nL = √[s(s−a)(s−b)(s−c)]\n"
                  f"  = √[{fmt(s)} × {fmt(s-a)} × {fmt(s-b)} × {fmt(s-c)}]\n"
                  f"  = {fmt(luas)} {{u}}²")
        self._show(luas, detail, ((0, 0), (c, 0), (x, y)),
                   {"ab": f"c = {fmt(c)}", "bc": f"a = {fmt(a)}", "ca": f"b = {fmt(b)}"})

    # --------------------------------------------------------- utilitas
    def error(self, msg):
        wx.MessageBox(msg, "Input tidak valid", wx.OK | wx.ICON_WARNING, self)
        self.SetStatusText("Input tidak valid")

    def reset_entries(self, ctrls):
        for c in ctrls:
            c.Clear()
        ctrls[0].SetFocus()
        self.lbl_hasil.SetLabel("-")
        self.lbl_detail.SetLabel("Belum ada perhitungan.")
        self.draw_panel.set_triangle(((0, 0), (8, 0), (2.8, 5)),
                                     {"base": "alas", "height": "tinggi"})
        self.SetStatusText("Siap")

    def reset_all(self):
        self.reset_entries(self.e2)
        self.reset_entries(self.e1)

    def on_rumus(self, event):
        wx.MessageBox("1. Alas & tinggi\n    L = ½ × alas × tinggi\n\n"
                      "2. Tiga sisi (rumus Heron)\n    s = (a + b + c) / 2\n"
                      "    L = √[s(s−a)(s−b)(s−c)]",
                      "Rumus Luas Segitiga", wx.OK | wx.ICON_INFORMATION, self)

    def on_about(self, event):
        wx.MessageBox("Kalkulator Luas Segitiga\nPython + wxPython",
                      "Tentang", wx.OK | wx.ICON_INFORMATION, self)


# ======================================================================
#  Aplikasi
# ======================================================================
class TriangleApp(wx.App):
    def OnInit(self):
        self.SetAppName("Kalkulator Luas Segitiga")
        self.frame = MainFrame()
        self.frame.Show()
        return True


if __name__ == "__main__":
    app = TriangleApp(False)      # False = pesan error tetap tampil di terminal
    app.MainLoop()

