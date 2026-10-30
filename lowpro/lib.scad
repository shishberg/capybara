// Rigid-transform helpers: 4x4 matrices, as multmatrix takes them.
function rot_x(a) = [[1, 0, 0, 0], [0, cos(a), -sin(a), 0], [0, sin(a), cos(a), 0], [0, 0, 0, 1]];
function rot_y(a) = [[cos(a), 0, sin(a), 0], [0, 1, 0, 0], [-sin(a), 0, cos(a), 0], [0, 0, 0, 1]];
function rot_z(a) = [[cos(a), -sin(a), 0, 0], [sin(a), cos(a), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
function trans(v) = [[1, 0, 0, v[0]], [0, 1, 0, v[1]], [0, 0, 1, v[2]], [0, 0, 0, 1]];
IDENT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
/** The point p in frame m. */
function xform(m, p) = let(q = m * [p[0], p[1], p[2], 1]) [q[0], q[1], q[2]];
/** The direction d in frame m. */
function xdir(m, d) = let(q = m * [d[0], d[1], d[2], 0]) [q[0], q[1], q[2]];
function origin(m) = [m[0][3], m[1][3], m[2][3]];
function axis_x(m) = [m[0][0], m[1][0], m[2][0]];
function axis_y(m) = [m[0][1], m[1][1], m[2][1]];
function axis_z(m) = [m[0][2], m[1][2], m[2][2]];
/** The inverse of a rigid transform. */
function rinv(m) = let(
    R = [[m[0][0], m[1][0], m[2][0]], [m[0][1], m[1][1], m[2][1]], [m[0][2], m[1][2], m[2][2]]],
    t = R * origin(m)
  ) [concat(R[0], [-t[0]]), concat(R[1], [-t[1]]), concat(R[2], [-t[2]]), [0, 0, 0, 1]];
/** A frame from three unit axes and an origin. */
function basis(x, y, z, o) = [[x[0], y[0], z[0], o[0]], [x[1], y[1], z[1], o[1]], [x[2], y[2], z[2], o[2]], [0, 0, 0, 1]];
function unit(v) = v / norm(v);
/** A frame at o whose z is n and whose y is `up` made square to n. */
function frame_at(o, n, up) = let(z = unit(n), y0 = up - (up * z) * z, y = unit(y0), x = cross(y, z)) basis(x, y, z, o);
function sum(v, i = 0) = i >= len(v) ? 0 : v[i] + sum(v, i + 1);
function vmin(v, i = 0) = i >= len(v) - 1 ? v[i] : min(v[i], vmin(v, i + 1));
function vmax(v, i = 0) = i >= len(v) - 1 ? v[i] : max(v[i], vmax(v, i + 1));
function clamp(v, lo, hi) = min(hi, max(lo, v));
function r2(v) = is_list(v) ? [for (x = v) r2(x)] : round(v * 100) / 100;
function xy(p) = [p[0], p[1]];
