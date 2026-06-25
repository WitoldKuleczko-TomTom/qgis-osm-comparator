# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QLabel, QListWidgetItem, QDialogButtonBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .overpass_client import get_feature_display_name


class FeatureSelectorDialog(QDialog):
    """Dialog pozwalający użytkownikowi wybrać jeden spośród kilku obiektów OSM."""

    def __init__(self, features, click_number=1, parent=None):
        super().__init__(parent)
        self.features = features
        self.selected_feature = None
        self._setup_ui(click_number)

    def _setup_ui(self, click_number):
        self.setWindowTitle("Wybór obiektu OSM")
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            f"Znaleziono <b>{len(self.features)}</b> obiektów dla <b>Obiektu {click_number}</b>.<br>"
            "Wybierz jeden z listy (dwuklik lub OK):"
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
            # Dodaj tooltip z pełnymi tagami
            tags = feature.get("tags", {})
            tooltip = "\n".join(f"{k}: {v}" for k, v in list(tags.items())[:10])
            if len(tags) > 10:
                tooltip += f"\n... (+{len(tags)-10} więcej)"
            item.setToolTip(tooltip)
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)
        self.list_widget.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_selection(self):
        current = self.list_widget.currentItem()
        if current is not None:
            idx = current.data(Qt.UserRole)
            self.selected_feature = self.features[idx]
            self.accept()
