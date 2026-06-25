# -*- coding: utf-8 -*-
"""Comparison dialog supporting an arbitrary number of OSM features (N columns)."""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFrame, QAbstractItemView, QGroupBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush

from .overpass_client import get_feature_display_name

# Header background colours for each feature slot (cycles if N > len)
FEATURE_HEADER_COLORS = [
    "#FFCDD2",  # F1 – pink
    "#BBDEFB",  # F2 – blue
    "#C8E6C9",  # F3 – light green
    "#FFF9C4",  # F4 – light yellow
    "#E1BEE7",  # F5 – lavender
    "#FFE0B2",  # F6 – orange
]

# Table cell colours
COLOR_MATCH   = QColor("#A8D5A2")  # green  – identical value in all features
COLOR_DIFF    = QColor("#FFE082")  # yellow – key in ≥2 features, values differ
COLOR_MISSING = QColor("#F0F0F0")  # gray   – this feature does not have the key


def _swatch_label(color_hex, text):
    """Return a legend item: colour swatch + text label."""
    row = QHBoxLayout()
    row.setSpacing(4)
    swatch = QFrame()
    swatch.setFixedSize(18, 18)
    swatch.setStyleSheet(
        f"background-color:{color_hex}; border:1px solid #999; border-radius:2px;"
    )
    lbl = QLabel(text)
    lbl.setFont(QFont("Arial", 9))
    row.addWidget(swatch)
    row.addWidget(lbl)
    row.addSpacing(10)
    return row


class ComparisonDialog(QDialog):
    """Side-by-side tag comparison of N OSM features."""

    compare_again = pyqtSignal()
    add_feature   = pyqtSignal()   # user wants to add a feature column

    def __init__(self, features, parent=None):
        super().__init__(parent)
        self.features = list(features)
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self):
        n = len(self.features)
        self.setWindowTitle(f"OSM Feature Comparator — {n} Feature(s)")
        self.setMinimumSize(750, 550)
        self.resize(min(350 + n * 220, 1600), 660)

        layout = QVBoxLayout(self)

        # Feature headers
        header_group  = QGroupBox("Compared features")
        header_layout = QHBoxLayout(header_group)
        for i, feat in enumerate(self.features):
            name  = get_feature_display_name(feat)
            color = FEATURE_HEADER_COLORS[i % len(FEATURE_HEADER_COLORS)]
            lbl   = QLabel(f"<b>Feature {i + 1}:</b> {name}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"background-color:{color}; padding:6px; border-radius:4px;"
            )
            header_layout.addWidget(lbl)
        layout.addWidget(header_group)

        # Legend
        legend_group  = QGroupBox("Legend")
        legend_layout = QHBoxLayout(legend_group)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        legend_layout.addLayout(_swatch_label("#A8D5A2", "Identical value"))
        legend_layout.addLayout(_swatch_label("#FFE082", "Different values"))
        legend_layout.addLayout(
            _swatch_label(FEATURE_HEADER_COLORS[0], "Unique to one feature (feature colour)")
        )
        legend_layout.addLayout(_swatch_label("#F0F0F0", "Key absent in this feature"))
        legend_layout.addStretch()
        layout.addWidget(legend_group)

        # Statistics
        all_tags_list = [f.get("tags", {}) for f in self.features]
        all_keys      = sorted(set().union(*[set(t) for t in all_tags_list]))
        stats         = self._compute_stats(all_keys, all_tags_list, n)
        layout.addWidget(self._build_stats_label(stats, n))

        # Table
        self.table = QTableWidget(len(all_keys), n + 1)
        headers = ["Key / Tag"] + [
            f"Feature {i + 1}\n{get_feature_display_name(self.features[i])}"
            for i in range(n)
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in range(1, n + 1):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        # NOTE: sorting must be enabled AFTER populating — Qt shifts rows otherwise.
        self.table.setSortingEnabled(False)

        key_font = QFont()
        key_font.setBold(True)

        for row, key in enumerate(all_keys):
            values         = [tags.get(key) for tags in all_tags_list]   # None = absent
            present_values = [v for v in values if v is not None]
            present_count  = len(present_values)
            all_same       = len(set(present_values)) == 1 if present_values else True

            # Key cell colour
            if present_count == 1:
                only_idx  = next(i for i, v in enumerate(values) if v is not None)
                key_color = QColor(FEATURE_HEADER_COLORS[only_idx % len(FEATURE_HEADER_COLORS)])
            elif all_same:
                key_color = COLOR_MATCH
            else:
                key_color = COLOR_DIFF

            key_item = QTableWidgetItem(key)
            key_item.setFont(key_font)
            key_item.setBackground(QBrush(key_color))
            key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, key_item)

            # Value cells
            for col_idx, value in enumerate(values):
                val_item = QTableWidgetItem(value if value is not None else "")
                if value is None:
                    cell_color = COLOR_MISSING
                elif present_count == 1:
                    cell_color = QColor(
                        FEATURE_HEADER_COLORS[col_idx % len(FEATURE_HEADER_COLORS)]
                    )
                elif all_same:
                    cell_color = COLOR_MATCH
                else:
                    cell_color = COLOR_DIFF
                val_item.setBackground(QBrush(cell_color))
                val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col_idx + 1, val_item)

        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕  Add feature")
        btn_add.setToolTip(
            "Click another OSM feature on the map to add it as a new column.\n"
            "Clicking the same element again will show its version history."
        )
        btn_add.clicked.connect(self._on_add_feature)

        btn_again = QPushButton("🔄  New comparison")
        btn_again.setToolTip("Close and start a fresh two-feature comparison")
        btn_again.clicked.connect(self._on_compare_again)

        btn_close = QPushButton("Close")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.reject)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_again)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    # ── Stats helpers ────────────────────────────────────────────────────────

    def _compute_stats(self, all_keys, all_tags_list, n):
        n_match = sum(
            1 for k in all_keys
            if all(k in t for t in all_tags_list)
            and len({t[k] for t in all_tags_list}) == 1
        )
        n_diff = sum(
            1 for k in all_keys
            if all(k in t for t in all_tags_list)
            and len({t[k] for t in all_tags_list}) > 1
        )
        n_partial = sum(
            1 for k in all_keys
            if not all(k in t for t in all_tags_list)
        )
        return {"total": len(all_keys), "match": n_match, "diff": n_diff, "partial": n_partial}

    def _build_stats_label(self, s, n):
        if n == 2:
            html = (
                f"Total keys: <b>{s['total']}</b> &nbsp;|&nbsp; "
                f"<span style='color:#2e7d32;'>Identical: <b>{s['match']}</b></span> &nbsp;|&nbsp; "
                f"<span style='color:#f57f17;'>Different values: <b>{s['diff']}</b></span> &nbsp;|&nbsp; "
                f"<span style='color:#b71c1c;'>Unique to one: <b>{s['partial']}</b></span>"
            )
        else:
            html = (
                f"Total keys: <b>{s['total']}</b> &nbsp;|&nbsp; "
                f"<span style='color:#2e7d32;'>All identical: <b>{s['match']}</b></span> &nbsp;|&nbsp; "
                f"<span style='color:#f57f17;'>Values differ: <b>{s['diff']}</b></span> &nbsp;|&nbsp; "
                f"<span style='color:#b71c1c;'>Not in all features: <b>{s['partial']}</b></span>"
            )
        lbl = QLabel(html)
        lbl.setTextFormat(Qt.RichText)
        lbl.setContentsMargins(4, 2, 4, 2)
        return lbl

    # ── Button handlers ──────────────────────────────────────────────────────

    def _on_add_feature(self):
        self.add_feature.emit()
        self.accept()

    def _on_compare_again(self):
        self.compare_again.emit()
        self.accept()
