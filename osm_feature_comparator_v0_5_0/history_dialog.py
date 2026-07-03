# -*- coding: utf-8 -*-
"""Dialog showing a comparison of two consecutive versions of the same OSM element."""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFrame, QAbstractItemView, QGroupBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QBrush

# Colour coding (same logic as two-feature ComparisonDialog)
COLOR_MATCH    = QColor("#A8D5A2")  # green  – unchanged
COLOR_DIFF     = QColor("#FFE082")  # yellow – value changed between versions
COLOR_ADDED    = QColor("#FFCDD2")  # pink   – key added in current version
COLOR_REMOVED  = QColor("#BBDEFB")  # blue   – key removed in current version


def _swatch_label(color_hex, text):
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
    row.addSpacing(12)
    return row


def _version_label(v):
    """Return a compact header string for a version dict."""
    ver  = v.get("version", "?")
    ts   = v.get("timestamp", "")[:10]   # date only (YYYY-MM-DD)
    user = v.get("user", "")
    cs   = v.get("changeset", "")
    parts = [f"v{ver}"]
    if ts:
        parts.append(ts)
    if user:
        parts.append(f"by {user}")
    if cs:
        parts.append(f"cs#{cs}")
    return " · ".join(parts)


class HistoryComparisonDialog(QDialog):
    """Compares the two most recent versions of an OSM element."""

    def __init__(self, current_version, previous_version, parent=None):
        super().__init__(parent)
        self.current  = current_version
        self.previous = previous_version
        self._setup_ui()

    def _setup_ui(self):
        osm_type = self.current.get("type", "element").capitalize()
        osm_id   = self.current.get("id",   "?")

        self.setWindowTitle(f"OSM Version History — {osm_type} #{osm_id}")
        self.setMinimumSize(750, 550)
        self.resize(920, 640)

        layout = QVBoxLayout(self)

        # Info banner
        banner = QLabel(
            f"You selected <b>{osm_type} #{osm_id}</b> which is already in the comparison. "
            "Showing the <b>two most recent versions</b> fetched from the OSM REST API."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background-color:#FFF9C4; padding:8px; border-radius:4px;"
            "border:1px solid #F9A825;"
        )
        layout.addWidget(banner)

        # Version headers
        header_group  = QGroupBox("Compared versions")
        header_layout = QHBoxLayout(header_group)
        curr_lbl = _version_label(self.current)
        prev_lbl = _version_label(self.previous)
        for label, header_text, color in [
            ("Current",  curr_lbl, "#FFCDD2"),
            ("Previous", prev_lbl, "#BBDEFB"),
        ]:
            w = QLabel(f"<b>{label}:</b> {header_text}")
            w.setWordWrap(True)
            w.setStyleSheet(f"background-color:{color}; padding:6px; border-radius:4px;")
            header_layout.addWidget(w)
        layout.addWidget(header_group)

        # Legend
        legend_group  = QGroupBox("Legend")
        legend_layout = QHBoxLayout(legend_group)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        for color, text in [
            ("#A8D5A2", "Unchanged"),
            ("#FFE082", "Value changed"),
            ("#FFCDD2", "Added in current version"),
            ("#BBDEFB", "Removed in current version"),
        ]:
            legend_layout.addLayout(_swatch_label(color, text))
        legend_layout.addStretch()
        layout.addWidget(legend_group)

        # Statistics
        tags_curr = self.current.get("tags",  {}) or {}
        tags_prev = self.previous.get("tags", {}) or {}
        all_keys  = sorted(set(tags_curr) | set(tags_prev))

        n_match   = sum(1 for k in all_keys if k in tags_curr and k in tags_prev and tags_curr[k] == tags_prev[k])
        n_changed = sum(1 for k in all_keys if k in tags_curr and k in tags_prev and tags_curr[k] != tags_prev[k])
        n_added   = sum(1 for k in all_keys if k in tags_curr and k not in tags_prev)
        n_removed = sum(1 for k in all_keys if k not in tags_curr and k in tags_prev)

        stats_lbl = QLabel(
            f"Total keys: <b>{len(all_keys)}</b> &nbsp;|&nbsp; "
            f"<span style='color:#2e7d32;'>Unchanged: <b>{n_match}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#f57f17;'>Changed: <b>{n_changed}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#c62828;'>Added: <b>{n_added}</b></span> &nbsp;|&nbsp; "
            f"<span style='color:#1565c0;'>Removed: <b>{n_removed}</b></span>"
        )
        stats_lbl.setTextFormat(Qt.RichText)
        stats_lbl.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(stats_lbl)

        # Table
        curr_header = f"Current ({_version_label(self.current)})"
        prev_header = f"Previous ({_version_label(self.previous)})"

        self.table = QTableWidget(len(all_keys), 3)
        self.table.setHorizontalHeaderLabels(["Key / Tag", curr_header, prev_header])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)

        key_font = QFont()
        key_font.setBold(True)

        for row, key in enumerate(all_keys):
            val_curr = tags_curr.get(key, "")
            val_prev = tags_prev.get(key, "")

            if key in tags_curr and key in tags_prev:
                color = COLOR_MATCH if val_curr == val_prev else COLOR_DIFF
            elif key in tags_curr:
                color = COLOR_ADDED    # new in current
            else:
                color = COLOR_REMOVED  # existed in previous, now gone

            brush = QBrush(color)

            key_item  = QTableWidgetItem(key)
            key_item.setFont(key_font)
            curr_item = QTableWidgetItem(val_curr)
            prev_item = QTableWidgetItem(val_prev)

            for item in (key_item, curr_item, prev_item):
                item.setBackground(brush)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, curr_item)
            self.table.setItem(row, 2, prev_item)

        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_close  = QPushButton("Close")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
