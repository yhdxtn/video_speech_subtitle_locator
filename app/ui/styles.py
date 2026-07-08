APP_STYLE = r"""
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
    color: #162033;
}
QMainWindow {
    background: #f4f7fb;
}
QLabel#titleLabel {
    font-size: 25px;
    font-weight: 700;
    color: #10203a;
}
QLabel#subtitleLabel, QLabel#mutedLabel {
    color: #6b7890;
}
QLabel#metricValue {
    font-size: 19px;
    font-weight: 700;
    color: #0f1d33;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 34px;
    border: 1px solid #ccd6e5;
    border-radius: 7px;
    background: white;
    padding: 0 9px;
}
QGroupBox {
    border: 1px solid #d8e0ec;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    background: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    min-height: 36px;
    border: 1px solid #cbd5e3;
    border-radius: 7px;
    background: white;
    padding: 0 14px;
}
QPushButton:hover {
    background: #eef4ff;
}
QPushButton#primaryButton {
    background: #2868e8;
    border-color: #2868e8;
    color: white;
    font-weight: 700;
}
QPushButton#primaryButton:hover {
    background: #1f59cc;
}
QPushButton#dangerButton {
    color: #d13c35;
    border-color: #efb8b3;
}
QProgressBar {
    min-height: 26px;
    border: 1px solid #ccd6e5;
    border-radius: 6px;
    background: white;
    text-align: center;
}
QProgressBar::chunk {
    background: #2868e8;
    border-radius: 5px;
}
QLabel#videoPreview {
    background: #0e1728;
    color: #9eabc0;
    border-radius: 9px;
}
QTableWidget {
    background: white;
    alternate-background-color: #f8fbff;
    border: 1px solid #d8e0ec;
    gridline-color: #e3e9f2;
    selection-background-color: #dce9ff;
    selection-color: #162033;
}
QHeaderView::section {
    background: #edf3fb;
    border: none;
    border-right: 1px solid #d8e0ec;
    border-bottom: 1px solid #d8e0ec;
    padding: 8px;
    font-weight: 700;
}
"""
