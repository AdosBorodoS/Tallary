from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from kivy.graphics import Color, Ellipse
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.widget import Widget


@dataclass(frozen=True)
class DonutSlice:
    fraction: float  # 0..1


class DonutChartWidget(Widget):
    """
    Рисует donut chart.
    - set_slices([...]) принимает доли 0..1
    - если slices пустые, рисует "пустое кольцо"

    Важно:
    Рисуем через self.x/self.y (а не center_x/center_y), чтобы избежать
    смещения на первом layout-проходе.
    """

    ringWidth = NumericProperty(24)  # px
    emptyRingColor = ListProperty([0.20, 0.20, 0.20, 1])

    _defaultColors = [
        (0.16, 0.45, 0.95, 1),  # blue
        (0.10, 0.78, 0.55, 1),  # green
        (0.95, 0.60, 0.15, 1),  # orange
        (0.70, 0.35, 0.95, 1),  # purple
        (0.95, 0.20, 0.50, 1),  # pink
        (0.00, 0.00, 0.00, 1),  # black
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._slices: List[DonutSlice] = []

        # Перерисовка при любом изменении геометрии/параметров
        self.bind(pos=self._redraw, size=self._redraw)
        self.bind(ringWidth=self._redraw, emptyRingColor=self._redraw)

    def set_slices(self, fractions: Sequence[float]) -> None:
        normalized: List[DonutSlice] = []

        for value in fractions:
            try:
                v = float(value)
            except Exception:
                continue
            if v <= 0:
                continue
            normalized.append(DonutSlice(fraction=v))

        total = sum(s.fraction for s in normalized)
        if total > 0:
            normalized = [DonutSlice(fraction=s.fraction / total) for s in normalized]

        self._slices = normalized
        self._redraw()

    def clear(self) -> None:
        self._slices = []
        self._redraw()

    def _redraw(self, *_args) -> None:
        self.canvas.clear()

        # Размер donut — минимальная сторона виджета
        sizeValue = min(float(self.width), float(self.height))
        if sizeValue <= 2:
            return

        # Центрируем donut внутри текущего прямоугольника виджета
        x0 = float(self.x) + (float(self.width) - sizeValue) / 2.0
        y0 = float(self.y) + (float(self.height) - sizeValue) / 2.0

        ringWidth = float(self.ringWidth)
        ringWidth = max(0.0, min(ringWidth, sizeValue / 2.0))

        innerSize = max(0.0, sizeValue - 2.0 * ringWidth)

        # Нет данных — рисуем пустое кольцо
        if len(self._slices) == 0:
            with self.canvas:
                Color(*self.emptyRingColor)
                Ellipse(pos=(x0, y0), size=(sizeValue, sizeValue))

                # центр (фон внутри)
                Color(0.08, 0.08, 0.08, 1)
                Ellipse(
                    pos=(x0 + ringWidth, y0 + ringWidth),
                    size=(innerSize, innerSize),
                )
            return

        angleStart = 90.0
        with self.canvas:
            for idx, s in enumerate(self._slices):
                angleEnd = angleStart + 360.0 * float(s.fraction)
                Color(*self._defaultColors[idx % len(self._defaultColors)])
                Ellipse(
                    pos=(x0, y0),
                    size=(sizeValue, sizeValue),
                    angle_start=angleStart,
                    angle_end=angleEnd,
                )
                angleStart = angleEnd

            # Внутренний круг (дырка)
            Color(0.08, 0.08, 0.08, 1)
            Ellipse(
                pos=(x0 + ringWidth, y0 + ringWidth),
                size=(innerSize, innerSize),
            )
