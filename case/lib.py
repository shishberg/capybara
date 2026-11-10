"""Rigid-transform helpers: 4x4 frames as numpy arrays, and a few small utilities."""
import math

import numpy as np


def rot_x(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], float)


def rot_y(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], float)


def rot_z(a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)


def trans(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


IDENT = np.eye(4)


def xform(m, p):
    """The point p in frame m."""
    return m[:3, :3] @ np.asarray(p, float) + m[:3, 3]


def xdir(m, d):
    """The direction d in frame m."""
    return m[:3, :3] @ np.asarray(d, float)


def origin(m):
    return m[:3, 3].copy()


def axis_x(m):
    return m[:3, 0].copy()


def axis_y(m):
    return m[:3, 1].copy()


def axis_z(m):
    return m[:3, 2].copy()


def rinv(m):
    """The inverse of a rigid transform."""
    r = m[:3, :3].T
    out = np.eye(4)
    out[:3, :3] = r
    out[:3, 3] = -r @ m[:3, 3]
    return out


def basis(x, y, z, o):
    """A frame from three unit axes and an origin."""
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, o
    return m


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame_at(o, n, up):
    """A frame at o whose z is n and whose y is `up` made square to n."""
    z = unit(n)
    up = np.asarray(up, float)
    y = unit(up - (up @ z) * z)
    return basis(np.cross(y, z), y, z, o)


def clamp(v, lo, hi):
    return min(hi, max(lo, v))


def r2(v):
    if isinstance(v, (list, tuple, np.ndarray)):
        return [r2(x) for x in v]
    return round(float(v) * 100) / 100


def xy(p):
    return (float(p[0]), float(p[1]))


def sind(a):
    return math.sin(math.radians(a))


def cosd(a):
    return math.cos(math.radians(a))
