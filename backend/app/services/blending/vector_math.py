import math
from typing import Dict, List, Tuple


def circular_mean_degrees(
    angles_deg: List[float],
    weights: List[float],
) -> Tuple[float, float]:
    """
    Computes the weighted circular (vector) average of angles in degrees [0, 360).
    
    Prevents catastrophic naive arithmetic averaging across the 0°/360° North boundary
    (e.g., 350° and 10° average to 0°/360° North, NOT 180° South).
    
    Args:
        angles_deg: List of wind direction angles in degrees [0, 360)
        weights: List of normalized weights summing to 1.0
        
    Returns:
        Tuple[blended_angle_deg, mean_resultant_length_R]
        where R in [0.0, 1.0] measures directional coherence (1.0 = identical, 0.0 = completely dispersed).
    """
    if len(angles_deg) != len(weights):
        raise ValueError("angles_deg and weights must have identical lengths.")
    if not angles_deg:
        return 0.0, 1.0

    # Ensure weights are normalized
    total_w = sum(weights)
    if total_w <= 0:
        norm_weights = [1.0 / len(weights)] * len(weights)
    else:
        norm_weights = [w / total_w for w in weights]

    # Convert degrees to radians and accumulate Cartesian vector components
    sum_x = 0.0
    sum_y = 0.0

    for angle, w in zip(angles_deg, norm_weights):
        rad = math.radians(angle % 360.0)
        sum_x += w * math.cos(rad)
        sum_y += w * math.sin(rad)

    # Mean resultant length R (0.0 to 1.0)
    R = math.sqrt(sum_x * sum_x + sum_y * sum_y)

    if R < 1e-9:
        # Perfectly opposing directions with equal weights; default to first angle
        return round(angles_deg[0] % 360.0, 1), 0.0

    # Compute resultant angle
    mean_rad = math.atan2(sum_y, sum_x)
    mean_deg = math.degrees(mean_rad)

    # Wrap to [0, 360)
    blended_deg = (mean_deg + 360.0) % 360.0

    return round(blended_deg, 1), min(1.0, round(R, 4))


def circular_dispersion_and_confidence(R: float) -> Tuple[float, float]:
    """
    Computes circular angular dispersion in degrees (Yamartino formulation)
    and normalized confidence index (0.0 to 1.0).
    
    Args:
        R: Mean resultant length from circular_mean_degrees (0.0 to 1.0)
        
    Returns:
        Tuple[circular_dispersion_deg, confidence_index]
    """
    R_clamped = max(1e-6, min(1.0, R))

    # Yamartino standard deviation approximation for circular data
    # sigma = sqrt(-2 * ln(R)) in radians, converted to degrees
    sigma_rad = math.sqrt(-2.0 * math.log(R_clamped))
    sigma_deg = round(math.degrees(sigma_rad), 1)

    # Confidence index: directly proportional to vector coherence R
    confidence_index = round(max(0.10, min(0.98, R)), 2)

    return sigma_deg, confidence_index
