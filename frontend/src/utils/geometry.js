/**
 * Geometry utility functions
 */

/**
 * Calculate the intersection point of two line segments
 * @param {Object} p1 - First point of line 1
 * @param {Object} p2 - Second point of line 1
 * @param {Object} p3 - First point of line 2
 * @param {Object} p4 - Second point of line 2
 * @returns {Object|null} Intersection point {x, y} or null if no intersection
 */
export function lineIntersection(p1, p2, p3, p4) {
  const x1 = p1.x, y1 = p1.y
  const x2 = p2.x, y2 = p2.y
  const x3 = p3.x, y3 = p3.y
  const x4 = p4.x, y4 = p4.y

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

  if (denom === 0) {
    return null // Lines are parallel
  }

  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
  const u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return {
      x: x1 + t * (x2 - x1),
      y: y1 + t * (y2 - y1)
    }
  }

  return null // No intersection
}

/**
 * Calculate the area of a polygon using the shoelace formula
 * @param {Array} points - Array of {x, y} points
 * @returns {number} Area in square units
 */
export function polygonArea(points) {
  if (points.length < 3) return 0

  let area = 0
  for (let i = 0; i < points.length; i++) {
    const j = (i + 1) % points.length
    area += points[i].x * points[j].y
    area -= points[j].x * points[i].y
  }

  return Math.abs(area / 2)
}

/**
 * Calculate the centroid of a polygon
 * @param {Array} points - Array of {x, y} points
 * @returns {Object} Centroid {x, y}
 */
export function polygonCentroid(points) {
  if (points.length === 0) return { x: 0, y: 0 }

  let sumX = 0
  let sumY = 0

  points.forEach(point => {
    sumX += point.x
    sumY += point.y
  })

  return {
    x: sumX / points.length,
    y: sumY / points.length
  }
}

/**
 * Calculate distance between two points
 * @param {Object} p1 - First point {x, y}
 * @param {Object} p2 - Second point {x, y}
 * @returns {number} Distance
 */
export function distance(p1, p2) {
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * Check if a point is close to another point within a threshold
 * @param {Object} p1 - First point {x, y}
 * @param {Object} p2 - Second point {x, y}
 * @param {number} threshold - Maximum distance
 * @returns {boolean}
 */
export function isPointNear(p1, p2, threshold = 10) {
  return distance(p1, p2) < threshold
}

/**
 * Clamp a value between min and max
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

/**
 * Calculate the angle between two points in radians
 * @param {Object} p1 - First point {x, y}
 * @param {Object} p2 - Second point {x, y}
 * @returns {number} Angle in radians
 */
export function angle(p1, p2) {
  return Math.atan2(p2.y - p1.y, p2.x - p1.x)
}

/**
 * Rotate a point around a center by an angle
 * @param {Object} point - Point to rotate {x, y}
 * @param {Object} center - Center of rotation {x, y}
 * @param {number} angleRad - Angle in radians
 * @returns {Object} Rotated point {x, y}
 */
export function rotatePoint(point, center, angleRad) {
  const cos = Math.cos(angleRad)
  const sin = Math.sin(angleRad)
  const dx = point.x - center.x
  const dy = point.y - center.y

  return {
    x: center.x + dx * cos - dy * sin,
    y: center.y + dx * sin + dy * cos
  }
}
