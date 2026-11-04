/** A number in [0, 1) that depends only on its inputs, so a replay behaves the same way. */
export function unit(id: number, salt: number): number {
  const value = Math.sin(id * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}
