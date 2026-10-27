"""Bounding box and geometric utilities for detection and tracking."""

import numpy as np
from typing import Tuple

def calculate_centroid(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Calculate centroid of a bounding box.

    Args:
        bbox: Bounding box as (x1, y1, x2, y2)

    Returns:
        Tuple of (cx, cy) centroid coordinates
    """
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return cx, cy

def calculate_euclidean_distance(point1: Tuple[float, float],
                                  point2: Tuple[float, float]) -> float:
    """
    Calculate Euclidean distance between two points.

    Args:
        point1: First point as (x, y)
        point2: Second point as (x, y)

    Returns:
        Euclidean distance
    """
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def extract_bbox_corners(bbox: Tuple[float, float, float, float]) -> list:
    """
    Extract four corners from bounding box.

    Args:
        bbox: Bounding box as (x1, y1, x2, y2)

    Returns:
        List of 4 corner points: [(x1,y1), (x2,y1), (x1,y2), (x2,y2)]
    """
    x1, y1, x2, y2 = bbox
    return [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]

def calculate_bbox_displacement(bbox_old: Tuple[float, float, float, float],
                                 bbox_new: Tuple[float, float, float, float]) -> float:
    """
    Calculate displacement between two bounding boxes using centroids.

    Args:
        bbox_old: Old bounding box as (x1, y1, x2, y2)
        bbox_new: New bounding box as (x1, y1, x2, y2)

    Returns:
        Euclidean distance between centroids
    """
    centroid_old = calculate_centroid(bbox_old)
    centroid_new = calculate_centroid(bbox_new)
    return calculate_euclidean_distance(centroid_old, centroid_new)
