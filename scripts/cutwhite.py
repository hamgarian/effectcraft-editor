"""Cut a subject off a plain white background: flood-fill near-white from the borders (so white INSIDE the subject,
like eyes or a speech bubble's fill, stays), then feather the edge. Generate art on plain white to use this.
Usage: python cutwhite.py IN.png [IN2.png ...] [--thresh 232]  -> IN_cut.png (RGBA)
"""
import sys

import cv2
import numpy as np

args = sys.argv[1:]
thresh = 232
if "--thresh" in args:
    i = args.index("--thresh"); thresh = int(args[i + 1]); args = args[:i] + args[i + 2:]
for path in args:
    img = cv2.imread(path)
    h, w = img.shape[:2]
    flood = (img.min(axis=2) > thresh).astype(np.uint8)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if flood[y, x] == 1:
            cv2.floodFill(flood, mask, (x, y), 2)
    alpha = np.where(flood == 2, 0, 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(cv2.erode(alpha, np.ones((3, 3), np.uint8)), (3, 3), 0)
    if alpha.min() != 0 or alpha.max() != 255:
        sys.exit(f"{path}: nothing (or everything) was cut - is the background plain white?")
    out = path.rsplit(".", 1)[0] + "_cut.png"
    cv2.imwrite(out, np.dstack([img, alpha]))
    print(out)
