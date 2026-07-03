# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QLabel, QListWidgetItem, QDialogButtonBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .overpass_client import get_feature_display_name
from .highlight import make_rubber_bands, clear_rubber_bands


class FeatureSelectorDialog(QDialog):
    """Dialog that lets the user pick one feature from multiple OSM results.

    When *canvas* and *color* are provided, a live rubber-band preview is drawn
    on the canvas as the user moves through the list, so they can visually
    identify each feature before confirming their choice.
    """

    def __init__(self, features, click_number=1, parent=None,
                 canvas=None, color=None):
        super().__init__(parent)
        self.features         = features
        self.selected_feature = None
        self._canvas          = canvas
        self._color           = color
        self._preview_rbs     = []   # temporary rubber bands shown while browsing
        self._setup_ui(click_number)
        # Draw initial preview for the first row
        if self._canvas and self._color is not None:
            self._preview_feature(0)

    def _setup_ui(self, click_number):
        self.setWindowTitle("Select OSM Feature")
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            f"Found <b>{len(self.features)}</b> features for <b>Feature {click_number}</b>.<br>"
            "Select one from the list (double-click or OK):"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        font = QFont()
        font.setPointSize(10)
        self.list_widget.setFont(font)

        for i, feature in enumerate(self.features):
            item = QListWidgetItem(get_feature_display_name(feature))
            item.setData(Qt.UserRole, i)
            tags    = feature.get("tags", {})
            tooltip = "\n".join(f"{k}: {v}" for k, v in list(tags.items())[:10])
            if len(tags) > 10:
                tooltip += f"\n... (+{len(tags) - 10} more)"
            item.setToolTip(tooltip)
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self._preview_feature)
        self.list_widget.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Canvas preview ────────────────────────────────────────────────────────

    def _preview_feature(self, row):
        """Redraw the canvas rubber-band preview for the feature at *row*."""
        if self._canvas is None or self._color is None:
            return
        clear_rubber_bands(self._canvas, self._preview_rbs)
        if 0 <= row < len(self.features):
            self._preview_rbs = make_rubber_bands(
                self._canvas, self.features[row], self._color
            )

    def _clear_preview(self):
        if self._canvas is not None:
            clear_rubber_bands(self._canvas, self._preview_rbs)

    # ── Accept / reject ───────────────────────────────────────────────────────

    def _accept_selection(self):
        current = self.list_widget.currentItem()
        if current is not None:
            idx                   = current.data(Qt.UserRole)
            self.selected_feature = self.features[idx]
            self._clear_preview()   # plugin will draw the persistent highlight
            self.accept()

    def reject(self):
        self._clear_preview()
        super().reject()

