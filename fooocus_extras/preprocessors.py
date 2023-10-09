import cv2
import numpy as np


def centered_canny(x: np.ndarray, center: float):
    assert isinstance(x, np.ndarray)
    assert x.ndim == 2 and x.dtype == np.uint8

    sigma = 0.4
    center = float(center)

    lower = int(max(0, (1.0 - sigma) * center))
    upper = int(min(255, (1.0 + sigma) * center))

    y = cv2.Canny(x, lower, upper)
    y = y.astype(np.float32) / 255.0
    return y


def centered_canny_color(x: np.ndarray, centers: list):
    assert isinstance(x, np.ndarray) and isinstance(centers, list)
    assert x.ndim == 3 and x.shape[2] == 3
    assert len(centers) == 3

    result = [centered_canny(x[..., i], c) for i, c in enumerate(centers)]
    result = np.stack(result, axis=2)
    return result


def pyramid_canny_color(x: np.ndarray):
    assert isinstance(x, np.ndarray)
    assert x.ndim == 3 and x.shape[2] == 3

    centers = np.median(x, axis=[0, 1]).tolist()
    H, W, C = x.shape
    acc_edge = None

    for k in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        Hs, Ws = int(H * k), int(W * k)
        small = cv2.resize(x, (Ws, Hs), interpolation=cv2.INTER_AREA)
        edge = centered_canny_color(small, centers)
        if acc_edge is None:
            acc_edge = edge
        else:
            acc_edge = cv2.resize(acc_edge, (edge.shape[1], edge.shape[0]), interpolation=cv2.INTER_LINEAR)
            acc_edge = acc_edge * 0.75 + edge * 0.25

    return acc_edge


def norm255(x):
    assert isinstance(x, np.ndarray)
    assert x.ndim == 2 and x.dtype == np.float32

    v_min = np.percentile(x, 4)
    v_max = np.percentile(x, 96)

    x -= v_min
    x /= v_max - v_min

    return x * 255.0


def canny_pyramid(x):
    # For some reasons, SAI's Control-lora Canny seems to be trained on canny maps with non-standard resolutions.
    # Then we use pyramid to use all resolutions to avoid missing any structure in specific resolutions.

    color_canny = pyramid_canny_color(x)
    result = np.sum(color_canny, axis=2)

    return norm255(result).clip(0, 255).astype(np.uint8)


def cpds(x):
    # cv2.decolor is not "decolor", it is Cewu Lu's method
    # See http://www.cse.cuhk.edu.hk/leojia/projects/color2gray/index.html
    # See https://docs.opencv.org/3.0-beta/modules/photo/doc/decolor.html

    raw = cv2.GaussianBlur(x, (0, 0), 0.8)
    density, boost = cv2.decolor(raw)

    raw = raw.astype(np.float32)
    density = density.astype(np.float32)
    boost = boost.astype(np.float32)

    offset = np.sum((raw - boost) ** 2.0, axis=2) ** 0.5
    result = density + offset

    return norm255(result).clip(0, 255).astype(np.uint8)
