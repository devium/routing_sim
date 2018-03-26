import matplotlib.pyplot as plt
import numpy as np
import sys
from scipy import interpolate


class CurveEditor(object):
    """
    Opens up a pyplot-based 1D curve editor that interpolates specified points with cubic splines.
    Usage:
    * Click anywhere to add new points to the curve.
    * Click near an existing point to remove that point.
    * Click above/below an existing point to move that point.
    * Click outside the specified x/y ranges to add and snap points to min/max.
    """
    POINT_CLICK_RADIUS = 0.05

    def __init__(self, points=None, title='', xmin=0, xmax=1, ymin=0, ymax=1):
        assert not points or isinstance(points, list)
        self.points = points if points else []
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

        fig = plt.figure()
        fig.suptitle(title)
        self.ax = fig.add_subplot(111)
        fig.canvas.mpl_connect('button_press_event', self.onclick)

        self.draw()

    def draw(self):
        self.ax.cla()
        if self.points:
            x, y = np.array(self.points).transpose()
        else:
            x, y = [], []
        x_curve = np.linspace(0, 1, num=500)
        self.ax.plot(x, y, 'rx', x_curve, self._evaluate(x_curve), 'b-')

        self.ax.set_xlim(-0.1, 1.1)
        self.ax.set_ylim(-0.1, 1.1)
        self.ax.grid(True)
        self.ax.set_xticklabels([
            f'{(self.xmax - self.xmin) * tick + self.xmin : .3g}'
            for tick in self.ax.get_xticks()
        ])
        self.ax.set_yticklabels([
            f'{(self.ymax - self.ymin) * tick + self.ymin : .3g}'
            for tick in self.ax.get_yticks()
        ])

        plt.show()

    def _evaluate(self, x_eval):
        if self.points:
            x, y = np.array(self.points).transpose()
        else:
            x, y = [], []

        if 0 not in x:
            x = np.append([0], x)
            y = np.append([0], y)
        if 1 not in x:
            x = np.append(x, [1])
            y = np.append(y, [1])

        curve = interpolate.InterpolatedUnivariateSpline(x, y, k=min(3, len(x) - 1))
        return np.clip(curve(x_eval), 0, 1)

    def evaluate(self, x_eval):
        x = (x_eval - self.xmin) / (self.xmax - self.xmin)
        return (self.ymax - self.ymin) * self._evaluate(x) + self.ymin

    def onclick(self, event):
        cx, cy = event.xdata, event.ydata
        print('Clicked ({}, {}).'.format(cx, cy))
        if not cx or not cy:
            return

        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))

        remove_point = None
        create_new = True
        for x, y in self.points:
            dx = cx - x
            dy = cy - y
            if dx * dx + dy * dy < self.POINT_CLICK_RADIUS * self.POINT_CLICK_RADIUS:
                remove_point = [x, y]
                create_new = False
                break
            if abs(dx) < self.POINT_CLICK_RADIUS:
                remove_point = [x, y]
                break

        if remove_point:
            self.points.remove(remove_point)

        if create_new:
            self.points.append([cx, cy])
            self.points = sorted(self.points)

        self.draw()


if __name__ == '__main__':
    sys.setrecursionlimit(1500)
    editor = CurveEditor(xmin=0, xmax=30, ymin=10, ymax=100)
