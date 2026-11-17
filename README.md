# FaceCursor

**FaceCursor** is a hands-free, multimodal desktop mouse controller powered by computer vision. Designed for accessibility and touchless human-computer interaction (HCI), it decouples **cursor positioning** (head/nose tracking) from **click & command execution** (asymmetric eye blendshapes) to eliminate cursor drift during clicks and deliver high spatial precision using a standard webcam.

---

## Key Features

* **Scale-Invariant Nose Pointer:** Tracks the tip of the nose relative to the user's facial bounding box (forehead, chin, and cheekbones), keeping cursor mapping consistent regardless of distance from the camera.
* **Adaptive Velocity Smoothing & Deadzone:** Dynamically scales damping between fast cross-screen head movements and micro-adjustments near small UI targets, while filtering out stationary sensor jitter.
* **Two-Step Precision Anchor Locking:** Closing one eye freezes the cursor in place, preventing head or facial muscle movements from shifting the pointer before a click is confirmed.
* **Asymmetric Blendshape Gesture Engine:** Uses neural network facial blendshape scores (`eyeBlinkLeft`, `eyeBlinkRight`) with asymmetry margins to distinguish intentional single-eye winks from natural bilateral blinks and head pitch changes.
* **4-Corner Personal Calibration:** Interactive fullscreen calibration routine that maps the user's comfortable head-movement range onto 90% (`5%`–`95%`) of the active display resolution.
* **Real-Time Debug HUD:** Toggleable landmark overlay and live blendshape telemetry for tuning and demonstration.

---

## System Architecture

FaceCursor follows a modular, object-oriented pipeline that separates computer vision extraction, state-machine gesture logic, and OS-level cursor actuation:

```text
┌─────────────────────┐
│   Webcam Stream     │  (OpenCV - Mirrored BGR -> RGB Frame)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ MediaPipe Tasks API │  (FaceLandmarker: 478 3D Landmarks + 52 Face Blendshapes)
└──────────┬──────────┘
           │
           ├──────────────────────────────────┐
           ▼                                  ▼
┌─────────────────────┐            ┌─────────────────────┐
│   calibration.py    │            │   calibration.py    │
│ get_nose_position() │            │ get_blink_scores()  │
└──────────┬──────────┘            └──────────┬──────────┘
           │ (rel_x, rel_y)                   │ (blink_l, blink_r)
           │                                  ▼
           │                       ┌─────────────────────┐
           │                       │   eye_gestures.py   │
           │                       │ EyeGestureController│
           │                       │ - Anchor Lock       │
           │                       │ - Double-Wink Click │
           │                       │ - 3x/5x Commands    │
           │                       └──────────┬──────────┘
           │                                  │ can_move_cursor() / Commands
           ▼                                  ▼
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

### Module Breakdown (`src/`)

| File | Responsibility |
| :--- | :--- |
| **`src/model_loader.py`** | Automatically checks for, downloads, and caches Google's official `face_landmarker.task` binary model if not present locally. |
| **`src/calibration.py`** | Extracts scale-normalized nose offsets (`landmark 4` vs. face bounds `10, 152, 234, 454`), maps mirrored `eyeBlink` blendshapes, renders debug landmarks, and executes the 4-corner fullscreen calibration UI. |
| **`src/eye_gestures.py`** | Implements `EyeGestureController`, a deterministic state machine with hysteresis and asymmetry checks to manage cursor anchor locks, anchored double-wink clicks, and multi-blink system commands. |
| **`src/cursor_controller.py`** | Implements `NoseCursorController`, converting normalized nose coordinates into screen coordinates using a deadzone filter (`DEADZONE_PX`) and speed-adaptive exponential smoothing. |
| **`src/mouse_tracker.py`** | Main application entry point. Manages the webcam capture loop, MediaPipe `VIDEO` mode inference, on-screen HUD telemetry, and keyboard shortcuts. |

---

## Libraries & Models Used

* **[MediaPipe Tasks Vision (`mediapipe`)](https://google.com):** Uses the **`FaceLandmarker`** model (`face_landmarker.task`, float16) running in `VIDEO` mode with `output_face_blendshapes=True`.
  * **3D Face Mesh (478 landmarks):** Used for head-pose-normalized nose tracking (`index 4`) and face bounding geometry (`indices 10, 152, 234, 454`).
  * **Face Blendshapes (52 expression coefficients):** Uses `eyeBlinkLeft` and `eyeBlinkRight` (`0.0` open to `1.0` closed) instead of raw geometric Eye Aspect Ratio (EAR), providing strong invariance to downward head pitch and lighting changes.
* **[OpenCV (`opencv-python`)](https://opencv.org):** Handles webcam video capture, horizontal mirror flipping, fullscreen calibration canvas rendering, and real-time HUD overlays.
* **[PyAutoGUI (`pyautogui`)](https://readthedocs.io):** Dispatches cross-platform OS mouse movement (`moveTo`), left clicks (`leftClick`), and right clicks (`rightClick`).
* **[NumPy (`numpy`)](https://numpy.org):** Generates calibration canvases and supports coordinate array operations.

---

## Installation & Setup

### 1. Prerequisites
* Python **3.10+**
* A working webcam positioned near eye/screen level

### 2. Install Dependencies
```bash
pip install opencv-python mediapipe pyautogui numpy
```

### 3. Run FaceCursor
Navigate to the `src/` directory and launch the main tracker:
```bash
cd src
python mouse_tracker.py
```
*(On first run, `model_loader.py` will automatically download `face_landmarker.task` into the project directory).*

---

## How to Use

### Step 1: 4-Corner Calibration
Upon launch, a fullscreen calibration window appears with a red target dot at each corner of your screen (`TOP-LEFT`, `TOP-RIGHT`, `BOTTOM-RIGHT`, `BOTTOM-LEFT`):
1. Keep your torso relaxed and point your **nose** subtly toward the active red dot.
2. Press **`SPACE`** to record 15 frames of your steady head position (the dot turns green while sampling).
3. Repeat for all 4 corners. Once complete, live cursor tracking begins immediately.

### Step 2: Gesture Controls

| Action | Gesture | How It Works |
| :--- | :--- | :--- |
| **Move Cursor** | **Point with Nose** (Both eyes open) | Subtle head yaw and pitch smoothly steer the cursor across the calibrated screen area. |
| **Anchor / Freeze Cursor** | **Hold Left or Right Eye Closed** (`> 0.20s`) | Locks the cursor at its current `(x, y)` coordinates so you can click tiny targets without drift. Opening the eye releases the anchor. |
| **Right Click** | **Hold Left Eye Closed** + **Double-Wink Right Eye** | Locks the cursor with your left eye, then perform two quick winks with your right eye to trigger `rightClick`. |
| **Left Click** | **Hold Right Eye Closed** + **Double-Wink Left Eye** | Locks the cursor with your right eye, then perform two quick winks with your left eye to trigger `leftClick`. |
| **Recalibrate** | **3 Bilateral Blinks** (Both eyes together) | Blink both eyes simultaneously 3 times and pause briefly (`0.7s`) to relaunch the 4-corner calibration screen. |
| **Exit Program** | **5 Bilateral Blinks** (Both eyes together) | Blink both eyes simultaneously 5 times and pause briefly (`0.7s`) to safely release the webcam and close the app. |

### Step 3: Keyboard Shortcuts (Backup Controls)

| Key | Function |
| :--- | :--- |
| **`SPACE`** | Record calibration point during the 4-corner calibration screen. |
| **`C`** | Trigger 4-corner recalibration at any time during live tracking. |
| **`D`** | Toggle the colored MediaPipe landmark debug overlay on/off. |
| **`ESC`** | Cancel calibration (falls back to default bounds) or exit the application. |

---

## Tuning Parameters

If you want to customize responsiveness or blink sensitivity for your webcam setup:
* **Cursor Speed & Jitter (`src/cursor_controller.py`):** Adjust `DEADZONE_PX` (default `4.0`), `MIN_SMOOTHING` (default `2.0`), and `MAX_SMOOTHING` (default `8.0`).
* **Wink & Anchor Sensitivity (`src/eye_gestures.py`):** Adjust `ANCHOR_CLOSE_SCORE` (`0.55`), `WINK_CLOSE_SCORE` (`0.45`), and `ASYMMETRY_MARGIN` (`0.25`) while observing your live `Blink L` and `Blink R` scores on the HUD.
