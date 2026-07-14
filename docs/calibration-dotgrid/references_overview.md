# Comprehensive Overview of Camera Calibration References

The `artifacts/camera-calibration-dotgrid/references/` directory contains a curated selection of seminal and state-of-the-art research papers on camera calibration. These documents trace the evolution of camera calibration techniques from traditional parametric models to modern neural network-based compensation methods.

Below is a detailed, easy-to-understand breakdown of each reference, organized by their technological era.

---

## 1. Traditional Parametric Camera Models

### [2006] A Generic Camera Model and Calibration Method
**File:** `2006-Juho Kannala-A Generic Camera Model and Calibration Method for Conventional.pdf`

*   **Summary:** This is a classic, foundational paper in computer vision. It introduces a generic camera model (often referred to as the Kannala-Brandt model) capable of accurately calibrating conventional, wide-angle, and fish-eye lenses.
*   **Key Takeaway:** Unlike standard pinhole models that fail with extreme distortion (like fish-eye lenses), this model uses a polynomial expansion of the projection angle. It remains a standard in the industry for robust distortion modeling.

### [2015] An Enhanced Unified Camera Model
**File:** `2015-Bogdan Khomutenko-An Enhanced Unified Camera Mode.pdf`

*   **Summary:** This paper proposes the Enhanced Unified Camera Model (EUCM). It builds upon previous unified models to seamlessly support systems ranging from standard perspective lenses to catadioptric (mirror-based) and fish-eye cameras.
*   **Key Takeaway:** EUCM simplifies the projection equations, making it mathematically elegant and computationally efficient for real-time robotic applications and visual odometry without sacrificing accuracy.

---

## 2. Early Neural Network Applications

### [2009] Implicit Camera Calibration Using MultiLayer Perceptron Type Neural Network
**File:** `2009-Dong-Min Woo-Implicit Camera Calibration Using MultiLayer Perceptron Type Neural Network.pdf`

*   **Summary:** This early work explores treating camera calibration as an implicit problem. Instead of estimating specific physical parameters (like focal length or distortion coefficients), the authors use a MultiLayer Perceptron (MLP) neural network to directly map 2D image coordinates to 3D world coordinates.
*   **Key Takeaway:** It demonstrates that neural networks can learn the complex, non-linear mapping of lens distortion without requiring explicit mathematical modeling.

---

## 3. Modern State-of-the-Art Neural Compensation

### [2025] Neural Compensation of Residual Distortion in Camera Calibration
**File:** `2025-Kelei Wang-Neural compensation of residual distortion in camera calibration.pdf`

*   **Summary:** Modern high-precision tasks reveal that traditional parametric models (like Kannala-Brandt or EUCM) cannot capture *all* distortions due to manufacturing imperfections. This paper introduces a hybrid approach: using a neural network to learn and compensate for the highly complex **residual distortion** that parametric models leave behind.
*   **Key Takeaway:** By combining the stability of traditional math models with the expressive power of neural networks, this method pushes calibration accuracy to unprecedented levels.

### [2026] End-to-End Neural Compensation for Target Deformation and Lens Distortion
**File:** `2026-Kelei Wang-End-to-end neural compensation for target deformation and lens distortion.pdf`

*   **Summary:** This is the most cutting-edge reference in the repository. It addresses a critical real-world problem: calibration targets (like checkerboards or dot grids) are never perfectly flat. This paper proposes an end-to-end neural architecture that simultaneously estimates and compensates for **both** the residual lens distortion **and** the physical deformation of the calibration target itself.
*   **Key Takeaway:** This eliminates a major source of systemic error in camera calibration, allowing for extreme precision even with imperfect physical calibration boards.
