"""Desktop testbed: pick an image, pick an OCR method, run it, see segments + boxes.

    python gui.py [image.png]
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGraphicsPolygonItem,
    QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

import methods
from ocr import OcrResult, ocr_image

ROOT = Path(__file__).resolve().parents[2]
BOX_PEN = QPen(QColor("#e5484d"), 2)
BOX_SELECTED_PEN = QPen(QColor("#ffd60a"), 4)
BOX_PEN.setCosmetic(True)  # constant on-screen width whatever the zoom
BOX_SELECTED_PEN.setCosmetic(True)


class Worker(QThread):
    done = Signal(object)

    def __init__(self, method: str, image: Path, settings: dict[str, str]):
        super().__init__()
        self.method, self.image, self.settings = method, image, settings

    def run(self) -> None:
        self.done.emit(ocr_image(self.method, self.image, self.settings))


class ImageView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.pixmap_item = None
        self.zoomed = False  # once the user zooms, stop auto-fitting on resize
        self.boxes: list[QGraphicsPolygonItem | None] = []

    def load(self, path: Path) -> bool:
        pix = QPixmap(str(path))
        if pix.isNull():
            return False
        self.clear_boxes()
        self.scene().clear()
        self.pixmap_item = self.scene().addPixmap(pix)
        self.scene().setSceneRect(self.pixmap_item.boundingRect())
        self.fit()
        return True

    def fit(self) -> None:
        self.zoomed = False
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def clear_boxes(self) -> None:
        for item in self.boxes:
            if item:
                self.scene().removeItem(item)
        self.boxes = []

    def set_boxes(self, polygons: list[list[tuple[float, float]] | None], visible: bool) -> None:
        self.clear_boxes()
        for poly in polygons:
            if poly is None:
                self.boxes.append(None)
                continue
            item = self.scene().addPolygon(QPolygonF([QPointF(x, y) for x, y in poly]), BOX_PEN)
            item.setVisible(visible)
            self.boxes.append(item)

    def show_boxes(self, visible: bool) -> None:
        for item in self.boxes:
            if item:
                item.setVisible(visible)

    def highlight(self, index: int) -> None:
        for i, item in enumerate(self.boxes):
            if item:
                item.setPen(BOX_SELECTED_PEN if i == index else BOX_PEN)
                item.setBrush(QBrush(QColor(255, 214, 10, 60)) if i == index else QBrush())
                item.setZValue(1 if i == index else 0)

    def wheelEvent(self, event) -> None:  # noqa: N802
        self.zoomed = True
        factor = 1.15 ** (event.angleDelta().y() / 120)
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self.zoomed and self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)


class MainWindow(QMainWindow):
    def __init__(self, image: Path | None) -> None:
        super().__init__()
        self.setWindowTitle("OCR testbed")
        self.resize(1400, 850)
        self.setAcceptDrops(True)
        self.image: Path | None = None
        self.worker: Worker | None = None
        self.setting_inputs: dict[str, QLineEdit | QComboBox] = {}

        # Left: image + toolbar
        self.view = ImageView()
        open_btn = QPushButton("Open image…")
        open_btn.clicked.connect(self.pick_image)
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.view.fit)
        self.show_boxes = QCheckBox("Show boxes")
        self.show_boxes.setChecked(True)
        self.show_boxes.toggled.connect(self.view.show_boxes)
        self.image_label = QLabel("Drop a PNG here or open one")
        toolbar = QHBoxLayout()
        for w in (open_btn, fit_btn, self.show_boxes):
            toolbar.addWidget(w)
        toolbar.addWidget(self.image_label, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(toolbar)
        left_layout.addWidget(self.view, 1)

        # Right: settings, run, separator, segments
        self.method = QComboBox()
        self.method.addItems(list(methods.METHODS))
        self.method.currentTextChanged.connect(self.build_settings)
        self.settings_form = QFormLayout()
        box = QGroupBox("Settings")
        box_layout = QVBoxLayout(box)
        method_form = QFormLayout()
        method_form.addRow("Method", self.method)
        box_layout.addLayout(method_form)
        box_layout.addLayout(self.settings_form)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self.run)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        self.segments = QListWidget()
        self.segments.setWordWrap(True)
        self.segments.setAlternatingRowColors(True)
        self.segments.currentRowChanged.connect(self.view.highlight)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(box)
        right_layout.addWidget(self.run_btn)
        right_layout.addWidget(sep)
        right_layout.addWidget(QLabel("Segments"))
        right_layout.addWidget(self.segments, 1)
        right_layout.addWidget(self.status)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([900, 500])
        self.setCentralWidget(split)

        self.build_settings(self.method.currentText())
        if image:
            self.open_image(image)

    # --- settings ---
    def build_settings(self, method: str) -> None:
        while self.settings_form.rowCount():
            self.settings_form.removeRow(0)
        self.setting_inputs = {}
        for s in methods.METHODS[method]:
            if s.choices:
                w = QComboBox()
                w.addItems(s.choices)
                w.setCurrentText(s.default)
            else:
                w = QLineEdit(s.default)
            self.setting_inputs[s.name] = w
            self.settings_form.addRow(s.label, w)

    def current_settings(self) -> dict[str, str]:
        return {
            name: (w.currentText() if isinstance(w, QComboBox) else w.text())
            for name, w in self.setting_inputs.items()
        }

    # --- image ---
    def pick_image(self) -> None:
        start = str(ROOT / "fixtures" / "photos")
        path, _ = QFileDialog.getOpenFileName(self, "Open image", start, "Images (*.png *.jpg *.jpeg *.heic)")
        if path:
            self.open_image(Path(path))

    def open_image(self, path: Path) -> None:
        self.segments.clear()
        self.view.clear_boxes()
        if self.view.load(path):
            self.image = path
            self.image_label.setText(f"{path.name}  ({self.view.pixmap_item.pixmap().width()}×"
                                     f"{self.view.pixmap_item.pixmap().height()})")
        else:
            # Still runnable: ocr_image reports the format error the API would give.
            self.image = path
            self.image_label.setText(f"{path.name}  (cannot preview)")
        self.status.setText("")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        self.open_image(Path(event.mimeData().urls()[0].toLocalFile()))

    # --- run ---
    def run(self) -> None:
        if not self.image:
            self.status.setText("Open an image first.")
            return
        self.run_btn.setEnabled(False)
        self.status.setText(f"Running {self.method.currentText()}…")
        self.worker = Worker(self.method.currentText(), self.image, self.current_settings())
        self.worker.done.connect(self.show_result)
        self.worker.start()

    def show_result(self, r: OcrResult) -> None:
        self.run_btn.setEnabled(True)
        self.segments.clear()
        for seg in r.segments:
            label = seg.text if seg.confidence is None else f"{seg.text}\n   conf {seg.confidence:.2f}"
            self.segments.addItem(QListWidgetItem(label))
        self.view.set_boxes([s.box for s in r.segments], self.show_boxes.isChecked())
        n_boxes = sum(1 for s in r.segments if s.box)
        self.status.setText(
            f"ERROR {r.error}" if r.error
            else f"{r.method}: {len(r.segments)} segments, {n_boxes} boxes, {r.elapsed_s}s"
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    app = QApplication(sys.argv)
    win = MainWindow(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
