export type Point = readonly [number, number];

export type Bounds = { minX: number; minY: number; maxX: number; maxY: number };

export function distanceToSegment(point: Point, start: Point, end: Point): number {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const lengthSquared = dx * dx + dy * dy;
  const along = lengthSquared === 0 ? 0 : ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / lengthSquared;
  const t = Math.max(0, Math.min(1, along));
  return Math.hypot(point[0] - (start[0] + t * dx), point[1] - (start[1] + t * dy));
}

/** Shortest distance from `point` to a polyline. A one-point stroke is a dot. */
export function distanceToPolyline(point: Point, points: readonly Point[]): number {
  if (points.length === 1) {
    return Math.hypot(point[0] - points[0][0], point[1] - points[0][1]);
  }
  let nearest = Infinity;
  for (let index = 1; index < points.length; index += 1) {
    nearest = Math.min(nearest, distanceToSegment(point, points[index - 1], points[index]));
  }
  return nearest;
}

export function boundsOf(polylines: readonly (readonly Point[])[]): Bounds | null {
  let bounds: Bounds | null = null;
  for (const points of polylines) {
    for (const [x, y] of points) {
      bounds = bounds
        ? {
            minX: Math.min(bounds.minX, x),
            minY: Math.min(bounds.minY, y),
            maxX: Math.max(bounds.maxX, x),
            maxY: Math.max(bounds.maxY, y),
          }
        : { minX: x, minY: y, maxX: x, maxY: y };
    }
  }
  return bounds;
}
