# OpenCV Calibration Comparison

This report compares the raw dot-grid extraction, an OpenCV Brown-Conrady calibration baseline, and the existing neural compensation result.

## Calibration Setup

- Image size: 4096 x 3000 px
- Grid shape: 19 rows x 26 columns
- Object spacing used for OpenCV: 30.0000
- OpenCV RMS reprojection error: 2.547602 px
- OpenCV flags: CALIB_USE_INTRINSIC_GUESS, CALIB_FIX_PRINCIPAL_POINT
- OpenCV undistorted image invalid pixel fraction: 0.000000
- Center marker excluded from diameter metrics: row 10, col 13 (raw diameter 68.45 px)

## Metric Comparison

| Metric | Raw | OpenCV | Neural | OpenCV change vs raw | Neural change vs raw |
| --- | ---: | ---: | ---: | ---: | ---: |
| Homography reprojection RMSE (px) | 23.9444 | 2.7912 | 2.2589 | 88.34% | 90.57% |
| Orthogonal straightness RMSE (px) | 13.7757 | 9.0741 | 1.2281 | 34.13% | 91.08% |
| SMIA vertical distortion (%) | -1.9521 | 0.1931 | 0.3578 | 90.11% | 81.67% |
| SMIA horizontal distortion (%) | 0.2687 | 0.1996 | 0.2046 | 25.73% | 23.85% |
| Horizontal spacing StdDev (px) | 6.4361 | 1.8824 | 1.7401 | 70.75% | 72.96% |
| Vertical spacing StdDev (px) | 5.3181 | 1.8058 | 1.3863 | 66.04% | 73.93% |
| Metal-ball Diameter StdDev (px) | 1.5121 | 1.3542 | 1.2038 | 10.45% | 20.39% |

## OpenCV Parameters

Camera matrix:

```text
[[4.01275695e+04 0.00000000e+00 2.04800000e+03]
 [0.00000000e+00 3.98681586e+04 1.50000000e+03]
 [0.00000000e+00 0.00000000e+00 1.00000000e+00]]
```

Distortion coefficients:

```text
k1=-4.33366205e+01, k2=6.82012148e+03, p1=3.74497707e-03, p2=3.16735879e-03, k3=-1.20156015e+05
```

## Interpretation Notes

- OpenCV is used here as a single-view parametric Brown-Conrady baseline.
- With only one calibration view, OpenCV intrinsics and distortion coefficients can be under-constrained; use them as baseline diagnostics, not as final production camera parameters.
- The neural result uses the repository's existing learned compensation field and can model residual target/lens deformation beyond the OpenCV polynomial fit.
- Diameter StdDev is computed from same-size metal balls only; the oversized center nut marker is excluded when detected.
- Lower values are better for every table metric. SMIA changes are computed from absolute distortion magnitude.
