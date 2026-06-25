# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFrame, QSizePolicy, QAbstractItemView,
    QGroupBox, QDialogButtonBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush

from .overpass_client import get_feature_display_name

# Kolory dla stanów porównania
COLOR_MATCH = QColor("#A8D5A2")       # zielony  – identyczna wartość
COLOR_DIFF = QColor("#FFE082")        # żółty    – klucz w obu, różne wartości
COLOR_ONLY1 = QColor("#FFCDD2")       # różowy   – klucz tylko w Obiekcie 1
COLOR_ONLY2 = QColor("#BBDEFB")       # niebieski– klucz tylko w Obiekcie 2


def _make_label(color_hex, text):
    """Zwraca widget legend (kolorowy kwadrat + opis)."""
    layout = QHBoxLayout()
    layout.setSpacing(4)
    swatch = QFrame()
    swatch.setFixedSize(18, 18)
    swatch.setStyleSheet(
        f"background-color: {color_hex}; border: 1px solid #999; border-radius: 2px;"
    )
    layout.addWidget(swatch)
    lbl = QLabel(text)
    lbl.setFont(QFont("Arial", 9))
    layout.addWidget(lbl)
    layout.addSpacing(12)
    return layout


class ComparisonDialog(QDialog):
    """Dialog wyświetlający porównanie tagów dwóch obiektów OSM."""

    compare_again = pyqtSignal()

    def __init__(self, feature1, feature2, parent=None):
        super().__init__(parent)
        self.feature1 = feature1
        self.feature2 = feature2
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("OSM Feature Comparator — Porównanie obiektów")
        self.setMinimumSize(750, 550)
        self.resize(900, 620)

        layout = QVBoxLayout(self)

        # ── Nagłówki obiektów ────────────────────────────────────────────────
        header_group = QGroupBox("Porównywane obiekty")
        header_layout = QHBoxLayout(header_group)

        f1_name = get_feature_display_name(self.feature1)
        f2_name = get_feature_display_name(self.feature2)

        for num, name, color in [("1", f1_name, "#FFCDD2"), ("2", f2_name, "#BBDEFB")]:
            lbl = QLabel(f"<b>Obiekt {num}:</b> {name}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"background-color: {color}; padding: 6px; border-radius: 4px;"
            )
            header_layout.addWidget(lbl)

        layout.addWidget(header_group)

        # ── Legenda ──────────────────────────────────────────────────────────
        legend_group = QGroupBox("Legenda")
        legend_layout = QHBoxLayout(legend_group)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        for color, text in [
            ("#A8D5A2", "Identyczna wartość"),
            ("#FFE082", "Różne wartości"),
            ("#FFCDD2", "Unikalne dla Obiektu 1"),
            ("#BBDEFB", "Unikalne dla Obiektu 2"),
        ]:
            legend_layout.addLayout(_make_label(color, text))
        legend_layout.addStretch()
        layout.addWidget(legend_group)

        # ── Statystyki ───────────────────────────────────────────────────────
        tags1 = self.feature1.get("tags", {})
        tags2 = self.feature2.get("tags", {})
        all_keys = sorted(set(tags1) | set(tags2))

        n_match = sum(
            1 for k in all_keys if k in tags1 and k in tags2 and tags1[k] == tags2[k]
        )
        n_diff = sum(
            1 for k in all_keys if k in tags1 and k in tags2 and tags1[k] != tags2[k]
        )
        n_only1 = sum(1 for k in all_keys if k in tags1 and k not in tags2)
        n_only2 = sum(1 for k in all_keys if k not in tags1 and k in tags2)

        stats_lbl = QLabel(
            f"Łącznie kluczy: <b>{len(all_keys)}</b> &nbsp;|&nbsp; "
            f"<span style='color:#2e7d32;'>Identyczne: <b>{n_match}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#f57f17;'>Różne wartości: <b>{n_diff}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#c62828;'>Tylko w Obiekcie 1: <b>{n_only1}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#1565c0;'>Tylko w Obiekcie 2: <b>{n_only2}</b></span>"
        )
        stats_lbl.setTextFormat(Qt.RichText)
        stats_lbl.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(stats_lbl)

        # ── Tabela ───────────────────────────────────────────────────────────
        self.table = QTableWidget(len(all_keys), 3)
        self.table.setHorizontalHeaderLabels(
            ["Klucz / Tag", f"Obiekt 1\n{f1_name}", f"Obiekt 2\n{f2_name}"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        # WAŻNE: sortowanie włączamy DOPIERO po wstawieniu wszystkich wierszy,
        # bo Qt przesuwa wiersze podczas setItem gdy sorting jest aktywne.
        self.table.setSortingEnabled(False)

        key_font = QFont()
        key_font.setBold(True)

        for row, key in enumerate(all_keys):
            val1 = tags1.get(key, "")
            val2 = tags2.get(key, "")

            if key in tags1 and key in tags2:
                color = COLOR_MATCH if val1 == val2 else COLOR_DIFF
            elif key in tags1:
                color = COLOR_ONLY1
            else:
                color = COLOR_ONLY2

            key_item = QTableWidgetItem(key)
            key_item.setFont(key_font)
            val1_item = QTableWidgetItem(val1)
            val2_item = QTableWidgetItem(val2)

            brush = QBrush(color)
            for item in (key_item, val1_item, val2_item):
                item.setBackground(brush)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, val1_item)
            self.table.setItem(row, 2, val2_item)

        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)  # domyślnie A→Z po kluczu
        layout.addWidget(self.table)

        # ── Przyciski ────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        btn_again = QPushButton("🔄  Nowe porównanie")
        btn_again.setToolTip("Zamknij i rozpocznij wybór dwóch nowych obiektów")
        btn_again.clicked.connect(self._on_compare_again)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.reject)
        btn_close.setDefault(True)

        btn_layout.addWidget(btn_again)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _on_compare_again(self):
        self.compare_again.emit()
        self.accept()
