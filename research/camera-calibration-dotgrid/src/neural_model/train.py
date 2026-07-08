import os
import argparse
import copy
import json
import torch
import torch.optim as optim
from dataset import load_data
from model import (
    MLPCompensation,
    AdaptiveLoss,
    collinearity_loss,
    compute_compensated_diameters,
    edge_balance_loss,
    grid_spacing_loss,
    smoothness_loss,
)
from phantom import CENTER_MARKER_MODES, detect_center_marker


def train_model(
    coords_path,
    diams_path,
    output_dir,
    epochs=5000,
    lr=1e-3,
    target_loss=5.0,
    hidden_dim=64,
    seed=42,
    smoothness_weight=1e-3,
    edge_balance_weight=0.3,
    center_marker_mode="auto",
    center_marker_min_ratio=1.5,
):
    os.makedirs(output_dir, exist_ok=True)

    torch.manual_seed(seed)

    # Load data
    coords, diams = load_data(coords_path, diams_path)
    metal_ball_mask_np, marker_metadata = detect_center_marker(
        diams,
        mode=center_marker_mode,
        min_ratio=center_marker_min_ratio,
    )
    metal_ball_mask = torch.as_tensor(metal_ball_mask_np, dtype=torch.bool)
    if marker_metadata["detected_marker_count"]:
        row, col = marker_metadata["marker_index_1based"]
        print(
            "Center marker detected at "
            f"row {row}, col {col}; excluding it from diameter loss."
        )
    else:
        print("No center marker excluded from diameter loss.")

    # Normalize with the same scale used by evaluation and image warping.
    norm_scale = torch.max(coords)

    model = MLPCompensation(hidden_dim=hidden_dim)
    adaptive_loss = AdaptiveLoss(num_losses=3)

    optimizer = optim.Adam(
        list(model.parameters()) + list(adaptive_loss.parameters()), lr=lr
    )

    best_score = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    best_losses = {}
    epoch_ran = 0

    for epoch in range(epochs):
        epoch_ran = epoch + 1
        optimizer.zero_grad()

        # 1. Forward pass for coords
        coords_norm = coords / norm_scale
        offsets = model(coords_norm)
        coords_comp = coords + offsets * norm_scale

        # 2. Grid geometry losses
        l_col = collinearity_loss(coords_comp)
        l_spacing = grid_spacing_loss(coords_comp)
        l_edge = edge_balance_loss(coords_comp) * edge_balance_weight

        # 3. Deformation loss
        diams_comp = compute_compensated_diameters(model, coords, diams, norm_scale)
        metal_diams_comp = diams_comp[metal_ball_mask]
        metal_diams = diams[metal_ball_mask]
        # Only same-size metal balls should be driven toward diameter consistency.
        l_def_var = torch.var(metal_diams_comp)
        l_def_mean = (torch.mean(metal_diams_comp) - torch.mean(metal_diams)) ** 2
        l_def = l_def_var + l_def_mean

        # Add regularization to prevent drifting or high-frequency warps.
        l_reg = torch.mean(offsets**2) * 1e-4
        l_smooth = smoothness_loss(offsets) * smoothness_weight

        # Adaptive weighting
        total_loss = (
            adaptive_loss([l_col, l_spacing, l_def]) + l_edge + l_reg + l_smooth
        )

        total_loss.backward()
        optimizer.step()

        score = (l_col + l_spacing + l_def + l_edge).item()
        if score < best_score:
            best_score = score
            best_state = copy.deepcopy(model.state_dict())
            best_losses = {
                "total_loss": float(total_loss.item()),
                "score": float(score),
                "collinearity": float(l_col.item()),
                "spacing": float(l_spacing.item()),
                "edge_balance": float(l_edge.item()),
                "diameter_variance": float(l_def_var.item()),
                "diameter_mean": float(l_def_mean.item()),
            }

        if epoch % 100 == 0:
            print(
                f"Epoch {epoch}: Total Loss: {total_loss.item():.6f}, "
                f"Col: {l_col.item():.2f}, Spacing: {l_spacing.item():.2f}, "
                f"Edge: {l_edge.item():.2f}, "
                f"Def Var: {l_def_var.item():.4f}, "
                f"Weights: {torch.exp(-adaptive_loss.log_vars).detach().numpy()}"
            )

        # Check termination condition
        if (
            l_col.item() < target_loss
            and l_spacing.item() < target_loss
            and l_def_var.item() < target_loss
        ):
            print(f"Converged at epoch {epoch}!")
            break

    model.load_state_dict(best_state)
    torch.save(model.state_dict(), os.path.join(output_dir, "compensation_model.pth"))

    metadata = {
        "coords_path": coords_path,
        "diams_path": diams_path,
        "grid_shape": list(coords.shape),
        "norm_scale": float(norm_scale.item()),
        "hidden_dim": hidden_dim,
        "seed": seed,
        "epochs_requested": epochs,
        "epochs_ran": epoch_ran,
        "learning_rate": lr,
        "target_loss": target_loss,
        "smoothness_weight": smoothness_weight,
        "edge_balance_weight": edge_balance_weight,
        "center_marker": marker_metadata,
        "best_losses": best_losses,
    }
    with open(os.path.join(output_dir, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print("Training complete. Model and metadata saved.")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train neural grid compensation model."
    )
    parser.add_argument("--coords", default="output/grid_coordinates.csv")
    parser.add_argument("--diams", default="output/grid_diameters.csv")
    parser.add_argument("--out-dir", default="output/neural_model")
    parser.add_argument("--epochs", type=int, default=5000)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--target-loss", type=float, default=5.0)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoothness-weight", type=float, default=1e-3)
    parser.add_argument("--edge-balance-weight", type=float, default=0.3)
    parser.add_argument(
        "--center-marker-mode", choices=CENTER_MARKER_MODES, default="auto"
    )
    parser.add_argument("--center-marker-min-ratio", type=float, default=1.5)
    args = parser.parse_args()

    train_model(
        args.coords,
        args.diams,
        args.out_dir,
        epochs=args.epochs,
        lr=args.lr,
        target_loss=args.target_loss,
        hidden_dim=args.hidden_dim,
        seed=args.seed,
        smoothness_weight=args.smoothness_weight,
        edge_balance_weight=args.edge_balance_weight,
        center_marker_mode=args.center_marker_mode,
        center_marker_min_ratio=args.center_marker_min_ratio,
    )
