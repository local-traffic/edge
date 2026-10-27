/**
 * Canvas utility functions for zone drawing and editing
 */

/**
 * Color constants for perspective calibration edges
 */
export const EDGE_COLORS = {
  top: '#00d4ff',     // Cyan
  left: '#ffaa00',    // Orange
  bottom: '#44ff44'   // Green
}

/**
 * Check if a point is inside a polygon using ray casting algorithm
 * @param {Object} point - {x, y} coordinates
 * @param {Array} polygon - Array of {x, y} points
 * @returns {boolean}
 */
export function pointInPolygon(point, polygon) {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x
    const yi = polygon[i].y
    const xj = polygon[j].x
    const yj = polygon[j].y

    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi

    if (intersect) inside = !inside
  }
  return inside
}

/**
 * Calculate distance from a point to a line segment
 * @param {Object} point - {x, y} coordinates
 * @param {Object} p1 - First point of segment
 * @param {Object} p2 - Second point of segment
 * @returns {number} Distance in pixels
 */
export function distanceToSegment(point, p1, p2) {
  const A = point.x - p1.x
  const B = point.y - p1.y
  const C = p2.x - p1.x
  const D = p2.y - p1.y

  const dot = A * C + B * D
  const lenSq = C * C + D * D
  let param = -1

  if (lenSq !== 0) {
    param = dot / lenSq
  }

  let xx, yy

  if (param < 0) {
    xx = p1.x
    yy = p1.y
  } else if (param > 1) {
    xx = p2.x
    yy = p2.y
  } else {
    xx = p1.x + param * C
    yy = p1.y + param * D
  }

  const dx = point.x - xx
  const dy = point.y - yy
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * Find the nearest handle to a point
 * @param {Object} point - {x, y} coordinates
 * @param {Array} handles - Array of {x, y} handle points
 * @param {number} threshold - Maximum distance to consider (default 10)
 * @returns {number|null} Index of nearest handle or null
 */
export function nearestHandle(point, handles, threshold = 10) {
  let nearestIndex = null
  let minDistance = threshold

  handles.forEach((handle, index) => {
    const dx = point.x - handle.x
    const dy = point.y - handle.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance < minDistance) {
      minDistance = distance
      nearestIndex = index
    }
  })

  return nearestIndex
}

/**
 * Draw a line on canvas
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array} points - Array of {x, y} points
 * @param {string} color - Stroke color
 * @param {number} lineWidth - Line width
 */
export function drawLine(ctx, points, color = '#00d4ff', lineWidth = 2) {
  if (points.length < 2) return

  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = lineWidth
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)

  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y)
  }

  ctx.stroke()
  ctx.restore()
}

/**
 * Draw a polygon on canvas
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array} points - Array of {x, y} points
 * @param {string} strokeColor - Stroke color
 * @param {string} fillColor - Fill color (optional)
 * @param {number} lineWidth - Line width
 */
export function drawPolygon(ctx, points, strokeColor = '#00d4ff', fillColor = null, lineWidth = 2) {
  if (points.length < 3) return

  ctx.save()
  ctx.strokeStyle = strokeColor
  ctx.lineWidth = lineWidth
  ctx.beginPath()
  ctx.moveTo(points[0].x, points[0].y)

  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y)
  }

  ctx.closePath()

  if (fillColor) {
    ctx.fillStyle = fillColor
    ctx.fill()
  }

  ctx.stroke()
  ctx.restore()
}

/**
 * Draw a handle (small circle) on canvas
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {boolean} selected - Whether handle is selected
 * @param {number} radius - Handle radius
 */
export function drawHandle(ctx, x, y, selected = false, radius = 5) {
  ctx.save()
  ctx.fillStyle = selected ? '#ff4444' : '#00d4ff'
  ctx.strokeStyle = '#ffffff'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, 2 * Math.PI)
  ctx.fill()
  ctx.stroke()
  ctx.restore()
}

/**
 * Clear the canvas
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 */
export function clearCanvas(ctx, width, height) {
  ctx.clearRect(0, 0, width, height)
}

/**
 * Linear interpolation between two points
 * @param {Object} p1 - First point {x, y}
 * @param {Object} p2 - Second point {x, y}
 * @param {number} t - Interpolation factor (0-1)
 * @returns {Object} Interpolated point {x, y}
 */
export function lerp(p1, p2, t) {
  return {
    x: p1.x + (p2.x - p1.x) * t,
    y: p1.y + (p2.y - p1.y) * t
  }
}

/**
 * Draw a perspective-distorted grid inside a quadrilateral
 * Uses bilinear interpolation for smooth perspective effect
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array} corners - 4 corner points [topLeft, topRight, bottomRight, bottomLeft]
 * @param {number} gridSize - Number of cells per side (e.g., 5 for 5x5)
 * @param {string} color - Grid line color
 * @param {number} lineWidth - Line width
 * @param {number} extend - Number of cells to extend beyond corners (default 0)
 */
export function drawPerspectiveGrid(ctx, corners, gridSize = 5, color = 'rgba(255, 255, 255, 0.6)', lineWidth = 1, extend = 0) {
  if (corners.length !== 4) return

  const [tl, tr, br, bl] = corners

  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = lineWidth

  // Calculate extended range in normalized coordinates
  const startT = -extend / gridSize
  const endT = 1 + extend / gridSize

  // Draw horizontal lines (vary v, extend u range)
  for (let i = -extend; i <= gridSize + extend; i++) {
    const v = i / gridSize
    // Get left and right edges at this v, then extend along u
    const leftEdgeTop = lerp(tl, bl, v)
    const rightEdgeTop = lerp(tr, br, v)
    // Extend the line beyond the edges
    const left = lerp(leftEdgeTop, rightEdgeTop, startT)
    const right = lerp(leftEdgeTop, rightEdgeTop, endT)

    ctx.beginPath()
    ctx.moveTo(left.x, left.y)
    ctx.lineTo(right.x, right.y)
    ctx.stroke()
  }

  // Draw vertical lines (vary u, extend v range)
  for (let i = -extend; i <= gridSize + extend; i++) {
    const u = i / gridSize
    // Get top and bottom edges at this u, then extend along v
    const topEdgeLeft = lerp(tl, tr, u)
    const bottomEdgeLeft = lerp(bl, br, u)
    // Extend the line beyond the edges
    const top = lerp(topEdgeLeft, bottomEdgeLeft, startT)
    const bottom = lerp(topEdgeLeft, bottomEdgeLeft, endT)

    ctx.beginPath()
    ctx.moveTo(top.x, top.y)
    ctx.lineTo(bottom.x, bottom.y)
    ctx.stroke()
  }

  ctx.restore()
}

/**
 * Draw an edge length label between two points
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} p1 - First point {x, y}
 * @param {Object} p2 - Second point {x, y}
 * @param {string} label - Text to display
 * @param {number} offset - Perpendicular offset from line (default 20)
 * @param {string} color - Text color (default white)
 */
export function drawEdgeLabel(ctx, p1, p2, label, offset = 20, color = '#ffffff') {
  const midX = (p1.x + p2.x) / 2
  const midY = (p1.y + p2.y) / 2

  // Calculate perpendicular offset direction
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  const len = Math.hypot(dx, dy)

  if (len === 0) return

  const nx = -dy / len * offset
  const ny = dx / len * offset

  ctx.save()
  ctx.fillStyle = color
  ctx.font = 'bold 14px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  // Draw text with shadow for better visibility
  ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
  ctx.shadowBlur = 3
  ctx.shadowOffsetX = 1
  ctx.shadowOffsetY = 1

  ctx.fillText(label, midX + nx, midY + ny)
  ctx.restore()
}

/**
 * Draw a corner label
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} point - Point {x, y}
 * @param {string} label - Text to display (e.g., 'TL', 'TR')
 * @param {number} offsetX - X offset from point
 * @param {number} offsetY - Y offset from point
 */
export function drawCornerLabel(ctx, point, label, offsetX = -15, offsetY = -15) {
  ctx.save()
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  // Draw text with shadow
  ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
  ctx.shadowBlur = 3
  ctx.shadowOffsetX = 1
  ctx.shadowOffsetY = 1

  ctx.fillText(label, point.x + offsetX, point.y + offsetY)
  ctx.restore()
}

