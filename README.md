# FaceCursor

**FaceCursor** is a hands-free, multimodal desktop mouse controller powered by computer vision. Designed for accessibility and touchless human-computer interaction (HCI)—particularly for software developers and users managing Repetitive Strain Injury (RSI) or motor impairments—it decouples **continuous cursor positioning** (head/nose tracking) from **discrete action execution** (asymmetric eye blendshapes) to eliminate cursor drift during clicks using a standard RGB webcam.

---

## Key Features

* **Scale-Invariant Nose Pointer:** Tracks the tip of the nose (`landmark 4`) normalized against the user's facial bounding box (forehead, chin, and cheekbones), maintaining consistent cursor mapping regardless of camera distance.
* **Adaptive Velocity Smoothing & Deadzone:** Dynamically scales damping between fast cross-screen head turns and micro-adjustments near small UI targets, while filtering out stationary tremor.
* **Two-Step Precision Anchor Clutch (`0.12s` Lock):** Holding one eye closed rapidly locks the cursor at its exact `(x, y)` coordinates, preventing subtle head or facial movements from shifting the pointer before a click is confirmed.
* **Asymmetric Blendshape Gesture Engine:** Uses neural facial blendshape scores (`eyeBlinkLeft`, `eyeBlinkRight`) with hysteresis, asymmetry prioritization, and symmetry checks (`abs(blink_l - blink_r) < asymmetry_margin`) to cleanly separate single-eye anchor winks from sympathetic squinting and bilateral blinks.
* **Persistent JSON Configuration & Hot-Reload (`R`):** All thresholds, smoothing parameters, and personal 4-corner calibration bounds are stored in `config/config.json` and can be reloaded live without restarting the webcam.
* **Real-Time Debug HUD (`D`):** Toggleable color-coded MediaPipe landmark overlay and live blendshape telemetry.

---

## Project Structure

```text
FaceCursor/
├── main.py                      # Application entry point, webcam loop, HUD & hotkeys
├── config/
│   |── config.json              # Central configuration, thresholds & saved calibration bounds
|   ├── config_loader.py         # Loads, validates, and persists settings to config/config.json
|
├── Helpers/
│   ├── __init__.py
│   ├── model_loader.py          # Downloads and caches MediaPipe face_landmarker.task
│   ├── calibration.py           # Landmark/blendshape extraction, debug overlay & 4-corner UI
│   ├── eye_gestures.py          # State machine for anchor locks, double-wink clicks & 3x/5x blinks
│   └── cursor_controller.py     # Kinematic mapping, deadzone filter & velocity-adaptive smoothing
└── README.md
```

---

## System Architecture

FaceCursor follows a modular pipeline that separates probabilistic computer vision extraction from deterministic state-machine gesture logic and OS-level cursor actuation:

```text
┌─────────────────────┐      ┌──────────────────────────┐
│   Webcam Stream     │      │    config/config.json    │
│  (OpenCV Mirrored)  │      │ (Thresholds & Bounds)    │
└──────────┬──────────┘      └────────────┬─────────────┘
           ▼                              │
┌─────────────────────┐                   │
│ MediaPipe Tasks API │                   │
│  (FaceLandmarker)   │                   │
└──────────┬──────────┘                   │
           │                              │
           ├──────────────────────┐       │
           ▼                      ▼       ▼
┌─────────────────────┐  ┌──────────────────────────┐
│   calibration.py    │  │     eye_gestures.py      │
│ get_nose_position() │  │   EyeGestureController   │
│ get_blink_scores()  │  │ - Asymmetric Anchor Lock │
└──────────┬──────────┘  │ - Double-Wink Clicks     │
           │             │ - Symmetric 3x/5x Blinks │
           │             └────────────┬─────────────┘
           │ (rel_x, rel_y)           │ can_move_cursor() / Commands
           ▼                          ▼
┌────────────────────────────────────────────────────────┐
│                  cursor_controller.py                  │
│                  NoseCursorController                  │
│       (Calibration Mapping -> Deadzone -> Smoothing)   │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│                    PyAutoGUI Engine                    │
│          (OS Cursor Movement & Click Events)           │
└────────────────────────────────────────────────────────┘
```

---

## Libraries & Models Used

* **[MediaPipe Tasks Vision (`mediapipe`)](https://google.com):** Runs Google's **`FaceLandmarker`** model (`face_landmarker.task`, float16) in `VIDEO` mode with `output_face_blendshapes=True`.
  * **3D Face Mesh (478 landmarks):** Tracks nose tip (`index 4`) relative to facial anchor bounds (`indices 10, 152, 234, 454`).
  * **Face Blendshapes (52 expression coefficients):** Uses `eyeBlinkLeft` and `eyeBlinkRight` (`0.0` open to `1.0` closed) for pitch-invariant wink and blink detection.
* **[OpenCV (`opencv-python`)](https://opencv.org):** Captures webcam frames, applies horizontal mirror flipping, renders the fullscreen calibration UI, and draws live HUD telemetry.
* **[PyAutoGUI (`pyautogui`)](https://readthedocs.io):** Dispatches cross-platform OS cursor positioning (`moveTo`) and click events (`leftClick`, `rightClick`).
* **[NumPy (`numpy`)](https://numpy.org):** Supports calibration canvas rendering and coordinate math.

---

## Installation & Setup

### 1. Prerequisites
* Python **3.10+**
* A standard webcam positioned near eye/screen level

### 2. Install Dependencies
```bash
pip install opencv-python mediapipe pyautogui numpy
```

### 3. Run FaceCursor
From the root `FaceCursor/` directory, run:
```bash
python main.py
```
*(On first launch, `Helpers/model_loader.py` automatically downloads `face_landmarker.task` if it is not already cached).*

---

## How to Use

### Step 1: 4-Corner Calibration
If `"is_calibrated": false` in `config/config.json` (or when you trigger recalibration), a fullscreen window opens with a red target dot at each corner (`TOP-LEFT`, `TOP-RIGHT`, `BOTTOM-RIGHT`, `BOTTOM-LEFT`):
1. Keep your posture comfortable and point your **nose** subtly toward the active red dot.
2. Press **`SPACE`** to record 15 steady frames (the dot turns green while sampling).
3. Repeat for all 4 corners. Your personal bounds are automatically saved to `config/config.json` for future sessions.

### Step 2: Hands-Free Gesture Controls

| Action | Gesture | Behavior |
| :--- | :--- | :--- |
| **Move Cursor** | **Point with Nose** (Both eyes open) | Subtle head yaw and pitch steer the cursor smoothly across the calibrated display area. |
| **Anchor / Freeze Cursor** | **Hold Left or Right Eye Closed** (`> 0.12s`) | Locks the cursor at its current `(x, y)` coordinates and displays an orange `ANCHOR` banner so you can click tiny UI icons without drift. Opening the eye releases the anchor. |
| **Right Click** | **Hold Left Eye Closed** + **Double-Wink Right Eye** | Locks the cursor with your left eye, then perform two quick winks with your right eye within `1.40s` to trigger `rightClick`. |
| **Left Click** | **Hold Right Eye Closed** + **Double-Wink Left Eye** | Locks the cursor with your right eye, then perform two quick winks with your left eye within `1.40s` to trigger `leftClick`. |
| **Recalibrate** | **3 Symmetric Bilateral Blinks** (Both eyes together) | Blink both eyes simultaneously 3 times and pause briefly (`0.70s`) to relaunch the 4-corner calibration screen. |
| **Exit Program** | **5 Symmetric Bilateral Blinks** (Both eyes together) | Blink both eyes simultaneously 5 times and pause briefly (`0.70s`) to safely release the webcam and close the app. |

### Step 3: Keyboard Shortcuts

| Key | Function |
| :--- | :--- |
| **`SPACE`** | Capture corner sample during 4-corner calibration. |
| **`C`** | Trigger 4-corner recalibration at any time. |
| **`R`** | Hot-reload changes from `config/config.json` live without restarting. |
| **`D`** | Toggle the colored MediaPipe landmark debug overlay on/off. |
| **`ESC`** | Cancel calibration or exit the application. |

---

## Configuration (`config/config.json`)

You can fine-tune sensitivity and ergonomics directly inside `config/config.json` and press **`R`** in the FaceCursor window to test changes immediately:

* **`cursor`:** Adjusts active screen margins (`min_range`, `max_range`), jitter filter (`deadzone_px`), and adaptive damping (`min_smoothing`, `max_smoothing`, `speed_threshold`).
* **`gestures`:** Adjusts blendshape activation thresholds (`anchor_close_score: 0.42`, `anchor_release_score: 0.25`, `wink_close_score: 0.30`, `asymmetry_margin: 0.15`, `both_blink_score: 0.65`) and timing windows (`anchor_hold_delay: 0.12`, `double_wink_window: 1.40`, `multi_blink_timeout: 0.70`).
* **`calibration`:** Stores `"is_calibrated"` and your saved nose coordinate bounds (`min_x`, `max_x`, `min_y`, `max_y`).
* **`app`:** Sets `"camera_index"` and `"show_debug_on_start"`.

---

## Development Record & Iteration Log

1. **v0.1 — Monocular & Binocular Iris Tracking:** Initial prototype mapping normalized iris landmarks (`468`, `473`) to screen space. Identified quantization jitter and vertical Y-axis inversion caused by upper eyelid droop when looking down.
2. **v0.2 — Scale-Invariant Nose Pointer & Geometric EAR:** Transitioned cursor positioning to head-normalized nose tip (`landmark 4`), improving spatial stability by ~10x, and introduced Eye Aspect Ratio (EAR) blink detection.
3. **v0.3 — Neural Blendshapes & Two-Step Anchor Clutch:** Replaced geometric EAR with MediaPipe eyeBlinkLeft/eyeBlinkRight blendshapes and asymmetry margins to prevent false triggers during downward head pitch and single-eye squinting.
4. **v0.4 — Modular Architecture & Persistent JSON Config:** Refactored logic into Helpers/ (eye_gestures.py, cursor_controller.py, calibration.py, config_loader.py) with persistent config/config.json bounds and live 'R' hot-reload.
5. **v0.5 — Asymmetric Anchor Prioritization & Symmetry Filtering:** Resolved anchor-lock contention by prioritizing asymmetric single-eye holds (0.12s) over bilateral blink detection and requiring inter-eye symmetry (abs(blink_l - blink_r) < asymmetry_margin) for 3x/5x commands.
