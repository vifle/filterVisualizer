# Filter Visualizer

A desktop GUI tool for loading signals and interactively visualizing the effect of different digital filters. Built with Python, Tkinter, Matplotlib, and SciPy.

## Requirements

- Python 3.10+
- `numpy`, `scipy`, `matplotlib`

Install dependencies:

```bash
pip install numpy scipy matplotlib
```

## Running

```bash
python main.py
```

---

## Layout

The window is split into two panels:

- **Left panel** — plots area with a Matplotlib toolbar for zooming and panning.
- **Right panel** — controls for loading signals and configuring filters.

### Plots

| Plot | Shown when |
|---|---|
| Raw Signal | Always (after a signal is loaded) |
| Filtered Signal | After "Apply Filter" is clicked |
| Impulse Response | Only for Frequency filters |

Zooming or panning the **Raw Signal** plot automatically adjusts the **Filtered Signal** plot to the same time range, and vice versa. Use the toolbar buttons (magnifier icon for zoom, hand icon for pan) or scroll to zoom.

---

## Workflow

1. Click **Load Signal (CSV)** to load the signal you want to filter.
2. Select a **Filter Type** from the dropdown.
3. Fill in the filter parameters (see below).
4. Click **Apply Filter**.

---

## Signal Files (CSV format)

All signal files (raw signal and reference signals) must be plain CSV files with numeric values only — no headers.

Two formats are accepted:

**Single-column** — signal amplitudes only. Time is automatically generated as integer sample indices starting at 0.

```
0.12
-0.45
0.87
...
```

**Two-column** — time in the first column, amplitude in the second.

```
0.000, 0.12
0.001, -0.45
0.002, 0.87
...
```

The delimiter must be a comma. Rows containing non-numeric or missing values are silently skipped.

---

## Filter Types and Parameters

### Frequency Filter

A classical IIR filter designed with SciPy. An additional **Impulse Response** plot is shown below the filtered signal.

| Parameter | Type | Description |
|---|---|---|
| Number of Taps | Integer ≥ 2 | Filter order = taps − 1. Higher values give a sharper roll-off but more phase distortion and potential instability. |
| Sample Rate (Hz) | Positive float | The sampling frequency of your signal in Hz. Used to convert cutoff frequencies from Hz to normalized units internally. Must match the actual sample rate of the loaded signal. |
| Filter Shape | Dropdown | `lowpass` — passes frequencies below cutoff. `highpass` — passes frequencies above cutoff. `bandpass` — passes frequencies between low and high cutoff. `bandstop` — rejects frequencies between low and high cutoff. |
| Filter Family | Dropdown | See table below. |
| Cutoff Freq (Hz) | Positive float | For lowpass/highpass: the −3 dB cutoff frequency in Hz. Must be strictly between 0 and Sample Rate / 2 (Nyquist). |
| Low / High Cutoff (Hz) | Positive floats | For bandpass/bandstop: lower and upper edge frequencies in Hz. Both must be between 0 and Nyquist; low cutoff must be less than high cutoff. |
| Passband Ripple (dB) | Positive float | Maximum allowed ripple in the passband. Only shown for **cheby1** and **ellip**. Typical values: 0.1–3 dB. |
| Stopband Atten (dB) | Positive float | Minimum attenuation in the stopband. Only shown for **cheby2** and **ellip**. Typical values: 20–80 dB. |

#### Filter Families

| Name | Description |
|---|---|
| `butter` | Butterworth — maximally flat magnitude in passband, no ripple. Good general-purpose choice. |
| `cheby1` | Chebyshev Type I — equiripple in passband, monotone in stopband. Sharper roll-off than Butterworth at same order. Requires passband ripple (dB). |
| `cheby2` | Chebyshev Type II — monotone in passband, equiripple in stopband. Requires stopband attenuation (dB). |
| `ellip` | Elliptic (Cauer) — equiripple in both bands. Sharpest possible roll-off for a given order. Requires both passband ripple and stopband attenuation. |
| `bessel` | Bessel — maximally linear phase response (constant group delay). Gentle roll-off; best for preserving waveform shape. |

---

### LMS Adaptive Filter

Least Mean Squares adaptive filter. The filter adapts its coefficients to minimize the mean square error between its output and a desired (reference) signal. The **filtered output is the error signal** — the component of the input that could not be predicted from the reference.

| Parameter | Type | Description |
|---|---|---|
| Number of Taps | Integer ≥ 1 | Length of the adaptive FIR filter. More taps allow modelling of longer correlations but slow convergence. |
| Learning Rate (μ) | Float, typically 0.0001–0.1 | Step size for weight updates. Too large → unstable/diverging. Too small → slow convergence. Rule of thumb: start at 0.01 and adjust. |
| Reference Signal | CSV file | The desired signal. Must contain at least as many samples as the raw signal. If it is longer it will be truncated; if shorter it will be zero-padded. Same CSV format as the raw signal (single- or two-column). |

---

### RLS Adaptive Filter

Recursive Least Squares adaptive filter. Converges faster than LMS but is more computationally expensive. Like LMS, the **filtered output is the error signal**.

| Parameter | Type | Description |
|---|---|---|
| Number of Taps | Integer ≥ 1 | Length of the adaptive FIR filter. |
| Forgetting Factor (λ) | Float in (0, 1] | Controls how quickly old samples are forgotten. Values close to 1 (e.g. 0.99) give a long memory (suitable for stationary signals). Smaller values (e.g. 0.95) track non-stationary signals faster but are noisier. |
| P(0) Initialization | Positive float | Initial value for the inverse covariance matrix diagonal. Large values (e.g. 100–1000) make the filter adapt quickly at the start. Equivalent to assuming low confidence in the initial weights. |
| Reference Signal | CSV file | Same role and format as in LMS. |

---

## Toolbar Controls

The Matplotlib toolbar at the bottom of the plot area provides:

| Button | Function |
|---|---|
| Home | Reset view to the full signal range |
| Back / Forward | Undo / redo zoom/pan steps |
| Pan (hand) | Click and drag to pan; right-click drag to zoom asymmetrically |
| Zoom (magnifier) | Draw a rectangle to zoom into that region |
| Save | Export the current figure as an image file |

When using Zoom or Pan on either the Raw Signal or Filtered Signal plot, both plots update together because they share the same time axis.
