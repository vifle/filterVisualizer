import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import scipy.signal as sp
import os


# ── Layout constants ─────────────────────────────────────────────────────────
_PAD = dict(padx=8, pady=3)

# Axis positions [left, bottom, width, height] in figure-fraction units
_POS_2ROW = {
    "raw":      [0.10, 0.56, 0.86, 0.38],
    "filtered": [0.10, 0.08, 0.86, 0.38],
}
_POS_3ROW = {
    "raw":      [0.10, 0.70, 0.86, 0.24],
    "filtered": [0.10, 0.39, 0.86, 0.24],
    "impulse":  [0.10, 0.08, 0.86, 0.24],
}


class FilterVisualizer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Filter Visualizer")
        self.root.geometry("1400x820")

        # ── Data storage ─────────────────────────────────────────────────────
        self.raw_signal:  np.ndarray | None = None
        self.time_points: np.ndarray | None = None
        self.ref_signal:  np.ndarray | None = None

        self._build_ui()
        # Trigger param panel for the default filter type
        self._on_filter_changed(None)

    # =========================================================================
    # UI construction
    # =========================================================================

    def _build_ui(self) -> None:
        pw = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6,
                            sashrelief=tk.RAISED)
        pw.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(pw)
        pw.add(left, minsize=700)

        right = tk.Frame(pw, bd=2, relief=tk.GROOVE)
        pw.add(right, minsize=320)

        self._build_plots(left)
        self._build_controls(right)

        self.root.update_idletasks()
        pw.sash_place(0, 1040, 0)

    # ── Plots ─────────────────────────────────────────────────────────────────

    def _build_plots(self, parent: tk.Frame) -> None:
        self.fig = Figure(figsize=(10, 8))

        self.ax_raw      = self.fig.add_axes(_POS_2ROW["raw"])
        self.ax_filtered = self.fig.add_axes(_POS_2ROW["filtered"], sharex=self.ax_raw)
        self.ax_impulse  = self.fig.add_axes(_POS_3ROW["impulse"])
        self.ax_impulse.set_visible(False)

        for ax, title in [
            (self.ax_raw,      "Raw Signal"),
            (self.ax_filtered, "Filtered Signal"),
            (self.ax_impulse,  "Impulse Response"),
        ]:
            ax.set_title(title)
            ax.set_xlabel("time / a.u.")
            ax.set_ylabel("amplitude / a.u.")

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = tk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        self.canvas.draw()

    def _set_layout_2row(self) -> None:
        self.ax_raw.set_position(_POS_2ROW["raw"])
        self.ax_filtered.set_position(_POS_2ROW["filtered"])
        self.ax_impulse.set_visible(False)
        self.canvas.draw_idle()

    def _set_layout_3row(self) -> None:
        self.ax_raw.set_position(_POS_3ROW["raw"])
        self.ax_filtered.set_position(_POS_3ROW["filtered"])
        self.ax_impulse.set_position(_POS_3ROW["impulse"])
        self.ax_impulse.set_visible(True)
        self.canvas.draw_idle()

    # ── Controls ──────────────────────────────────────────────────────────────

    def _build_controls(self, parent: tk.Frame) -> None:
        # Load signal
        tk.Button(parent, text="Load Signal (CSV)", command=self._load_signal,
                  font=("", 10, "bold"), bg="#2196F3", fg="white") \
            .pack(fill=tk.X, padx=8, pady=(12, 4))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        # Filter type
        tk.Label(parent, text="Filter Type:", font=("", 9, "bold")) \
            .pack(anchor=tk.W, **_PAD)
        self.filter_type = tk.StringVar(value="Frequency")
        cb = ttk.Combobox(parent, textvariable=self.filter_type, state="readonly",
                          values=["LMS Adaptive", "RLS Adaptive", "Frequency"])
        cb.pack(fill=tk.X, **_PAD)
        cb.bind("<<ComboboxSelected>>", self._on_filter_changed)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        tk.Label(parent, text="Filter Parameters:", font=("", 9, "bold")) \
            .pack(anchor=tk.W, **_PAD)

        # Scrollable params area
        params_outer = tk.Frame(parent)
        params_outer.pack(fill=tk.BOTH, expand=True, padx=8)
        self.params_frame = tk.Frame(params_outer)
        self.params_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)

        tk.Button(parent, text="Apply Filter", command=self._apply_filter,
                  font=("", 10, "bold"), bg="#4CAF50", fg="white") \
            .pack(fill=tk.X, padx=8, pady=(4, 12))

    # =========================================================================
    # Parameter panels
    # =========================================================================

    def _clear_params(self) -> None:
        for w in self.params_frame.winfo_children():
            w.destroy()

    def _lbl_entry(self, parent, text, default, row) -> tk.StringVar:
        """Helper: label + entry on a grid row, returns the StringVar."""
        tk.Label(parent, text=text).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar(value=str(default))
        tk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky=tk.EW,
                                                 padx=(6, 0), pady=2)
        parent.columnconfigure(1, weight=1)
        return var

    def _ref_signal_row(self, parent, row) -> tk.Label:
        """Helper: reference signal file-picker row; returns the status label."""
        tk.Label(parent, text="Reference Signal:").grid(row=row, column=0,
                                                         sticky=tk.W, pady=2)
        row_frame = tk.Frame(parent)
        row_frame.grid(row=row + 1, column=0, columnspan=2, sticky=tk.EW, pady=2)
        status = tk.Label(row_frame, text="No file selected",
                          relief=tk.SUNKEN, anchor=tk.W, width=22)
        status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(row_frame, text="Browse…",
                  command=lambda: self._browse_ref(status)).pack(side=tk.RIGHT)
        return status

    # ── LMS ──────────────────────────────────────────────────────────────────

    def _setup_lms_params(self) -> None:
        f = self.params_frame
        self.lms_taps = self._lbl_entry(f, "Number of Taps:", 32, 0)
        self.lms_mu   = self._lbl_entry(f, "Learning Rate (μ):", 0.01, 1)
        self._lms_ref_lbl = self._ref_signal_row(f, 2)

    # ── RLS ──────────────────────────────────────────────────────────────────

    def _setup_rls_params(self) -> None:
        f = self.params_frame
        self.rls_taps      = self._lbl_entry(f, "Number of Taps:", 32, 0)
        self.rls_lambda    = self._lbl_entry(f, "Forgetting Factor (λ):", 0.99, 1)
        self.rls_p0        = self._lbl_entry(f, "P(0) Initialization:", 100, 2)
        self._rls_ref_lbl  = self._ref_signal_row(f, 3)

    # ── Frequency ────────────────────────────────────────────────────────────

    def _setup_freq_params(self) -> None:
        f = self.params_frame

        self.freq_taps   = self._lbl_entry(f, "Number of Taps:", 51, 0)
        self.freq_fs     = self._lbl_entry(f, "Sample Rate (Hz):", 1000, 1)

        # Filter shape
        tk.Label(f, text="Filter Shape:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.freq_shape = tk.StringVar(value="lowpass")
        cb_shape = ttk.Combobox(f, textvariable=self.freq_shape, state="readonly",
                                values=["lowpass", "highpass", "bandpass", "bandstop"])
        cb_shape.grid(row=2, column=1, sticky=tk.EW, padx=(6, 0))
        cb_shape.bind("<<ComboboxSelected>>", lambda e: self._update_cutoff_vis())

        # Filter family
        tk.Label(f, text="Filter Family:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.freq_family = tk.StringVar(value="butter")
        cb_fam = ttk.Combobox(f, textvariable=self.freq_family, state="readonly",
                              values=["butter", "cheby1", "cheby2", "ellip", "bessel"])
        cb_fam.grid(row=3, column=1, sticky=tk.EW, padx=(6, 0))
        cb_fam.bind("<<ComboboxSelected>>", lambda e: self._update_ripple_vis())

        # Cutoff 1
        self._co1_lbl = tk.Label(f, text="Cutoff Freq (Hz):")
        self._co1_lbl.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.freq_cutoff1 = tk.StringVar(value="100")
        tk.Entry(f, textvariable=self.freq_cutoff1).grid(row=4, column=1, sticky=tk.EW,
                                                          padx=(6, 0))

        # Cutoff 2 (band filters)
        self._co2_lbl = tk.Label(f, text="High Cutoff (Hz):")
        self._co2_lbl.grid(row=5, column=0, sticky=tk.W, pady=2)
        self.freq_cutoff2 = tk.StringVar(value="300")
        self._co2_entry = tk.Entry(f, textvariable=self.freq_cutoff2)
        self._co2_entry.grid(row=5, column=1, sticky=tk.EW, padx=(6, 0))

        # Passband ripple (cheby1, ellip)
        self._rp_lbl = tk.Label(f, text="Passband Ripple (dB):")
        self._rp_lbl.grid(row=6, column=0, sticky=tk.W, pady=2)
        self.freq_rp = tk.StringVar(value="1.0")
        self._rp_entry = tk.Entry(f, textvariable=self.freq_rp)
        self._rp_entry.grid(row=6, column=1, sticky=tk.EW, padx=(6, 0))

        # Stopband attenuation (cheby2, ellip)
        self._rs_lbl = tk.Label(f, text="Stopband Atten (dB):")
        self._rs_lbl.grid(row=7, column=0, sticky=tk.W, pady=2)
        self.freq_rs = tk.StringVar(value="40.0")
        self._rs_entry = tk.Entry(f, textvariable=self.freq_rs)
        self._rs_entry.grid(row=7, column=1, sticky=tk.EW, padx=(6, 0))

        f.columnconfigure(1, weight=1)

        # Set initial visibility
        self._update_cutoff_vis()
        self._update_ripple_vis()

    def _update_cutoff_vis(self) -> None:
        band = self.freq_shape.get() in ("bandpass", "bandstop")
        if band:
            self._co1_lbl.config(text="Low Cutoff (Hz):")
            self._co2_lbl.grid()
            self._co2_entry.grid()
        else:
            self._co1_lbl.config(text="Cutoff Freq (Hz):")
            self._co2_lbl.grid_remove()
            self._co2_entry.grid_remove()

    def _update_ripple_vis(self) -> None:
        fam = self.freq_family.get()
        need_rp = fam in ("cheby1", "ellip")
        need_rs = fam in ("cheby2", "ellip")
        if need_rp:
            self._rp_lbl.grid()
            self._rp_entry.grid()
        else:
            self._rp_lbl.grid_remove()
            self._rp_entry.grid_remove()
        if need_rs:
            self._rs_lbl.grid()
            self._rs_entry.grid()
        else:
            self._rs_lbl.grid_remove()
            self._rs_entry.grid_remove()

    # =========================================================================
    # Event callbacks
    # =========================================================================

    def _on_filter_changed(self, _event) -> None:
        self._clear_params()
        self._discard_filter_output()
        ft = self.filter_type.get()
        if ft == "LMS Adaptive":
            self._setup_lms_params()
            self._set_layout_2row()
        elif ft == "RLS Adaptive":
            self._setup_rls_params()
            self._set_layout_2row()
        else:
            self._setup_freq_params()
            self._set_layout_3row()

    def _browse_ref(self, label_widget: tk.Label) -> None:
        path = filedialog.askopenfilename(
            title="Load Reference Signal",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.ref_signal = self._read_csv_signal(path)
            label_widget.config(text=os.path.basename(path))
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def _load_signal(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Signal",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            sig, t = self._read_csv_with_time(path)
            self.raw_signal  = sig
            self.time_points = t
            self._discard_filter_output()
            self._plot_raw()
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def _apply_filter(self) -> None:
        if self.raw_signal is None:
            messagebox.showwarning("No Signal", "Please load a signal first.")
            return
        ft = self.filter_type.get()
        try:
            if ft == "LMS Adaptive":
                filtered = self._run_lms()
                self._plot_filtered(filtered)
            elif ft == "RLS Adaptive":
                filtered = self._run_rls()
                self._plot_filtered(filtered)
            else:
                filtered, imp = self._run_freq()
                self._plot_filtered(filtered)
                self._plot_impulse(imp)
        except Exception as exc:
            messagebox.showerror("Filter Error", str(exc))

    # =========================================================================
    # CSV helpers
    # =========================================================================

    def _read_csv_signal(self, path: str) -> np.ndarray:
        """Read a CSV and return the signal column (1-D array)."""
        data = np.genfromtxt(path, delimiter=",", invalid_raise=False)
        data = data[~np.isnan(data).any(axis=data.ndim - 1)]  # drop nan rows
        if data.ndim == 1:
            return data
        return data[:, 1] if data.shape[1] >= 2 else data[:, 0]

    def _read_csv_with_time(self, path: str):
        """Return (signal, time) arrays from a CSV."""
        data = np.genfromtxt(path, delimiter=",", invalid_raise=False)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        # Remove rows that are entirely NaN
        mask = ~np.isnan(data).all(axis=1)
        data = data[mask]
        if data.shape[1] >= 2:
            return data[:, 1], data[:, 0]
        sig = data[:, 0]
        return sig, np.arange(len(sig), dtype=float)

    # =========================================================================
    # Filter implementations
    # =========================================================================

    def _prep_ref(self, n: int) -> np.ndarray:
        if self.ref_signal is None:
            raise ValueError("No reference signal loaded.")
        r = self.ref_signal
        if len(r) >= n:
            return r[:n]
        return np.pad(r, (0, n - len(r)))

    def _run_lms(self) -> np.ndarray:
        M  = int(self.lms_taps.get())
        mu = float(self.lms_mu.get())
        x  = self.raw_signal
        d  = self._prep_ref(len(x))
        n  = len(x)
        w  = np.zeros(M)
        e  = np.zeros(n)
        for i in range(M, n):
            xv   = x[i - M + 1 : i + 1][::-1]
            y    = w @ xv
            e[i] = d[i] - y
            w   += 2.0 * mu * e[i] * xv
        return e

    def _run_rls(self) -> np.ndarray:
        M   = int(self.rls_taps.get())
        lam = float(self.rls_lambda.get())
        p0  = float(self.rls_p0.get())
        x   = self.raw_signal
        d   = self._prep_ref(len(x))
        n   = len(x)
        w   = np.zeros(M)
        P   = p0 * np.eye(M)
        e   = np.zeros(n)
        for i in range(M, n):
            xv    = x[i - M + 1 : i + 1][::-1].reshape(-1, 1)
            pi    = P @ xv
            denom = lam + float(xv.T @ pi)
            k     = pi / denom
            y     = float(w @ xv.flatten())
            e[i]  = d[i] - y
            w    += k.flatten() * e[i]
            P     = (P - k @ xv.T @ P) / lam
        return e

    def _run_freq(self):
        M      = int(self.freq_taps.get())
        shape  = self.freq_shape.get()
        family = self.freq_family.get()
        fs     = float(self.freq_fs.get())
        order  = max(1, M - 1)

        cutoff: float | list[float]
        if shape in ("bandpass", "bandstop"):
            cutoff = [float(self.freq_cutoff1.get()),
                      float(self.freq_cutoff2.get())]
        else:
            cutoff = float(self.freq_cutoff1.get())

        # Design IIR filter (cutoff in Hz, fs supplied)
        if family == "butter":
            b, a = sp.butter(order, cutoff, btype=shape, fs=fs)
        elif family == "cheby1":
            rp = float(self.freq_rp.get())
            b, a = sp.cheby1(order, rp, cutoff, btype=shape, fs=fs)
        elif family == "cheby2":
            rs = float(self.freq_rs.get())
            b, a = sp.cheby2(order, rs, cutoff, btype=shape, fs=fs)
        elif family == "ellip":
            rp = float(self.freq_rp.get())
            rs = float(self.freq_rs.get())
            b, a = sp.ellip(order, rp, rs, cutoff, btype=shape, fs=fs)
        elif family == "bessel":
            b, a = sp.bessel(order, cutoff, btype=shape, norm="phase", fs=fs)
        else:
            raise ValueError(f"Unknown family: {family}")

        filtered = sp.filtfilt(b, a, self.raw_signal)

        # Impulse response
        imp_len  = max(3 * M, 128)
        impulse  = np.zeros(imp_len)
        impulse[0] = 1.0
        imp_resp = sp.lfilter(b, a, impulse)

        return filtered, imp_resp

    # =========================================================================
    # Plotting helpers
    # =========================================================================

    def _discard_filter_output(self) -> None:
        """Remove all plotted filter results without resetting axis limits or sharex."""
        for ax in (self.ax_filtered, self.ax_impulse):
            for line in list(ax.lines):
                line.remove()
        self.canvas.draw_idle()

    def _plot_raw(self) -> None:
        ax = self.ax_raw
        ax.clear()
        ax.plot(self.time_points, self.raw_signal, color="#1565C0", linewidth=0.9)
        ax.set_title("Raw Signal")
        ax.set_xlabel("time / a.u.")
        ax.set_ylabel("amplitude / a.u.")
        self.canvas.draw()

    def _plot_filtered(self, data: np.ndarray) -> None:
        ax = self.ax_filtered
        ax.clear()
        ax.plot(self.time_points, data, color="#B71C1C", linewidth=0.9)
        ax.set_title("Filtered Signal")
        ax.set_xlabel("time / a.u.")
        ax.set_ylabel("amplitude / a.u.")
        self.canvas.draw()

    def _plot_impulse(self, data: np.ndarray) -> None:
        ax = self.ax_impulse
        ax.clear()
        ax.plot(data, color="#1B5E20", linewidth=0.9)
        ax.set_title("Impulse Response")
        ax.set_xlabel("time / a.u.")
        ax.set_ylabel("amplitude / a.u.")
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        self.canvas.draw()


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = FilterVisualizer(root)
    root.mainloop()
