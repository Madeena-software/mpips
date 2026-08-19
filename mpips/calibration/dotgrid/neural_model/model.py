# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import torch
import torch.nn as nn


class MLPCompensation(nn.Module):
    def __init__(self, hidden_dim=64):
        super().__init__()
        # Input: normalized (x, y)
        self.net = nn.Sequential(
            nn.Linear(2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2),
        )
        # Initialize final layer to output near zero offsets
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x):
        # x is (..., 2)
        return self.net(x)


def apply_compensation(model, coords, norm_scale):
    coords_norm = coords / norm_scale
    offsets = model(coords_norm)
    return coords + offsets * norm_scale


def invert_compensation_points(model, dst_points, norm_scale, iterations=8):
    """Find source points whose compensated coordinates land on dst_points."""
    src_points = dst_points.clone()
    for _ in range(iterations):
        offsets = model(src_points / norm_scale) * norm_scale
        src_points = dst_points - offsets
    return src_points


class AdaptiveLoss(nn.Module):
    def __init__(self, num_losses=2):
        super().__init__()
        # log_vars will learn the uncertainty for each loss
        self.log_vars = nn.Parameter(torch.zeros(num_losses))

    def forward(self, losses):
        """
        losses: list or tuple of scalar tensors
        Returns the combined loss.
        """
        total_loss = 0
        for i, loss in enumerate(losses):
            precision = torch.exp(-self.log_vars[i])
            total_loss += precision * loss + self.log_vars[i]
        return total_loss


def collinearity_loss(coords):
    """
    coords: (rows, cols, 2) tensor of compensated coordinates
    Penalizes row bowing and column bowing in the compensated grid.
    """
    # Enforce horizontal rows (constant Y)
    row_y = coords[..., 1]  # shape (rows, cols)
    loss_row = torch.mean(torch.var(row_y, dim=1))

    # Enforce vertical columns (constant X)
    col_x = coords[..., 0]  # shape (rows, cols)
    loss_col = torch.mean(torch.var(col_x, dim=0))

    return loss_row + loss_col


def grid_spacing_loss(coords):
    """
    Keeps the rectified grid close to a uniformly spaced lattice.
    """
    row_dx = coords[:, 1:, 0] - coords[:, :-1, 0]
    col_dy = coords[1:, :, 1] - coords[:-1, :, 1]

    loss_x = torch.mean((row_dx - torch.mean(row_dx)) ** 2)
    loss_y = torch.mean((col_dy - torch.mean(col_dy)) ** 2)
    return loss_x + loss_y


def edge_balance_loss(coords):
    """
    Keeps the outer grid span close to the center span in both axes.
    This directly targets SMIA-style barrel/pincushion imbalance.
    """
    rows, cols = coords.shape[:2]
    mid_col = cols // 2
    mid_row = rows // 2

    center_height = coords[-1, mid_col, 1] - coords[0, mid_col, 1]
    edge_height = (
        (coords[-1, 0, 1] - coords[0, 0, 1]) + (coords[-1, -1, 1] - coords[0, -1, 1])
    ) / 2.0

    center_width = coords[mid_row, -1, 0] - coords[mid_row, 0, 0]
    edge_width = (
        (coords[0, -1, 0] - coords[0, 0, 0]) + (coords[-1, -1, 0] - coords[-1, 0, 0])
    ) / 2.0

    return (
        (edge_height - center_height) ** 2 + (edge_width - center_width) ** 2
    ) * 0.01


def smoothness_loss(offsets):
    dx = offsets[:, 1:, :] - offsets[:, :-1, :]
    dy = offsets[1:, :, :] - offsets[:-1, :, :]
    return torch.mean(dx**2) + torch.mean(dy**2)


def compute_compensated_diameters(model, coords, diams, norm_scale):
    """
    coords: (rows, cols, 2)
    diams: (rows, cols)
    norm_scale: scalar to normalize inputs to [-1, 1]
    """
    # Create boundary points
    d = diams.unsqueeze(-1) / 2.0
    p_left = coords.clone()
    p_left[..., 0] -= d[..., 0]
    p_right = coords.clone()
    p_right[..., 0] += d[..., 0]

    p_top = coords.clone()
    p_top[..., 1] -= d[..., 0]
    p_bottom = coords.clone()
    p_bottom[..., 1] += d[..., 0]

    # Pass through network
    def get_comp(p):
        p_norm = p / norm_scale
        offset = model(p_norm)
        # offset is in normalized space, scale it back
        return p + offset * norm_scale

    c_left = get_comp(p_left)
    c_right = get_comp(p_right)
    c_top = get_comp(p_top)
    c_bottom = get_comp(p_bottom)

    diam_x = torch.norm(c_right - c_left, dim=-1)
    diam_y = torch.norm(c_bottom - c_top, dim=-1)

    return (diam_x + diam_y) / 2.0
