import sys
import os
import glob
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QFileDialog, 
                             QSplitter, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QLabel, QMessageBox, QFrame, QSlider)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QWheelEvent, QPainter, QFont, QColor, QDesktopServices

# --- 自定义图像查看器 (无需修改) ---
class ImageViewer(QGraphicsView):
    file_dropped_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene_obj.addItem(self.pixmap_item)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QColor("#f3f3f3"))
        self.setAcceptDrops(True)

    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.pixmap_item.setPixmap(pixmap)
            self.scene_obj.setSceneRect(QRectF(pixmap.rect()))
            self.fitInView(self.scene_obj.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.pixmap_item.setPixmap(QPixmap())

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            self.file_dropped_signal.emit(file_path)

# --- 主窗口 ---
class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("小邵的打标机")
        self.resize(1200, 750)
        
        # 核心数据
        self.image_files = []
        self.current_index = -1
        self.current_txt_path = ""
        self.base_font_size = 14 

        # UI 初始化
        self.setup_ui()
        self.apply_win11_style()

    def setup_ui(self):
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 顶部工具栏
        top_bar = QHBoxLayout()
        self.lbl_info = QLabel("请加载文件夹或将图片拖入左侧区域")
        self.lbl_info.setStyleSheet("color: #666; font-size: 15px;") 
        btn_load = QPushButton("📂 打开文件夹")
        btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_load.clicked.connect(self.open_folder)
        top_bar.addWidget(self.lbl_info)
        top_bar.addStretch()
        top_bar.addWidget(btn_load)

        # 中间分割区域
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # 左侧：图片区域 (恢复简洁布局)
        self.image_viewer = ImageViewer()
        self.image_viewer.file_dropped_signal.connect(self.handle_file_drop)
        
        # 右侧：文本区域容器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10) 

        # 字体缩放工具栏
        font_tool_layout = QHBoxLayout()
        font_tool_layout.setContentsMargins(5, 5, 5, 5)
        
        lbl_zoom_icon = QLabel("🔍 缩放预览:")
        lbl_zoom_icon.setStyleSheet("color: #444; font-weight: bold; font-size: 16px;")
        
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(50, 250) 
        self.font_slider.setValue(100)
        self.font_slider.setFixedWidth(250) 
        self.font_slider.setFixedHeight(40)
        self.font_slider.valueChanged.connect(self.update_font_zoom)
        
        self.lbl_zoom_val = QLabel("100%")
        self.lbl_zoom_val.setFixedWidth(50)
        self.lbl_zoom_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_zoom_val.setStyleSheet("color: #444; font-size: 16px; font-weight: 500;")

        # 字数统计显示标签
        self.lbl_char_count = QLabel("字数: 0")
        self.lbl_char_count.setStyleSheet("""
            color: #00FF7F; 
            font-size: 15px; 
            font-weight: bold; 
            padding-left: 10px;
        """)
        self.lbl_char_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        font_tool_layout.addWidget(lbl_zoom_icon)
        font_tool_layout.addSpacing(10)
        font_tool_layout.addWidget(self.font_slider)
        font_tool_layout.addWidget(self.lbl_zoom_val)
        font_tool_layout.addStretch() 
        font_tool_layout.addWidget(self.lbl_char_count) 

        # 文本编辑框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("此处显示对应的 txt 内容...")
        self.text_edit.textChanged.connect(self.update_char_count)
        
        initial_font = QFont("Consolas", self.base_font_size)
        self.text_edit.setFont(initial_font)
        
        right_layout.addLayout(font_tool_layout)
        right_layout.addWidget(self.text_edit)

        # 添加到分割器
        splitter.addWidget(self.image_viewer)
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 1) 
        splitter.setStretchFactor(1, 1) 
        splitter.setSizes([600, 600])

        # --- 底部控制栏 ---
        bottom_bar = QHBoxLayout()
        self.btn_prev = QPushButton("A 上一张")
        self.btn_prev.setShortcut("a") 
        
        # [新增] 两个功能按钮
        self.btn_sys_open = QPushButton("🖥️ 系统打开")
        self.btn_copy_img = QPushButton("📋 复制图像")
        self.btn_sys_open.clicked.connect(self.open_image_in_system)
        self.btn_copy_img.clicked.connect(self.copy_image_to_clipboard)

        self.btn_save = QPushButton("Ctrl+S 保存文本")
        self.btn_save.setShortcut("Ctrl+S")
        
        self.btn_next = QPushButton("D 下一张")
        self.btn_next.setShortcut("d") 

        self.btn_prev.clicked.connect(lambda: self.navigate(-1))
        self.btn_next.clicked.connect(lambda: self.navigate(1))
        self.btn_save.clicked.connect(self.save_current_text)

        self.toggle_buttons(False)

        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_prev)
        # [修改] 插入到上一张右边
        bottom_bar.addWidget(self.btn_sys_open)
        bottom_bar.addWidget(self.btn_copy_img)
        
        bottom_bar.addWidget(self.btn_save)
        bottom_bar.addWidget(self.btn_next)
        bottom_bar.addStretch()

        main_layout.addLayout(top_bar)
        main_layout.addWidget(splitter)
        main_layout.addLayout(bottom_bar)

    def apply_win11_style(self):
        style_sheet = """
        QMainWindow {
            background-color: #f0f3f9;
        }
        QWidget {
            font-family: "Segoe UI", "Microsoft YaHei";
        }
        QTextEdit {
            background-color: #ffffff;
            border: 1px solid #d1d1d1;
            border-radius: 8px;
            padding: 10px;
            color: #333;
        }
        QTextEdit:focus {
            border: 2px solid #0067c0;
        }
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #d1d1d1;
            border-radius: 6px;
            padding: 8px 20px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #e5e5e5;
        }
        QPushButton:pressed {
            background-color: #cce4f7;
            border-color: #0067c0;
        }
        QGraphicsView {
            background-color: #e3e7ed;
            border-radius: 8px;
            border: 1px solid #d1d1d1;
        }
        
        QSlider::groove:horizontal {
            border: 0px solid #bbb;
            background: transparent;
            height: 16px;
            border-radius: 0px;
        }
        QSlider::sub-page:horizontal {
            background: #28a745; 
            border-radius: 3px;
        }
        QSlider::add-page:horizontal {
            background: #e9ecef; 
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #ffffff;
            border: 1px solid #c0c0c0;
            width: 26px;
            margin: -6px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal:hover {
            background: #f8f9fa;
            border-color: #28a745;
        }
        """
        self.setStyleSheet(style_sheet)

    # --- 逻辑处理 ---
    
    # 系统查看器打开
    def open_image_in_system(self):
        if self.image_files and 0 <= self.current_index < len(self.image_files):
            file_path = self.image_files[self.current_index]
            abs_path = os.path.abspath(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
    
    # 复制图像到剪切板
    def copy_image_to_clipboard(self):
        pixmap = self.image_viewer.pixmap_item.pixmap()
        if not pixmap.isNull():
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            # 视觉反馈
            original_title = self.windowTitle()
            self.setWindowTitle(original_title + " [已复制图像!]")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.setWindowTitle(original_title))
        else:
            QMessageBox.warning(self, "提示", "当前没有加载有效的图片，无法复制。")

    def update_font_zoom(self, value):
        self.lbl_zoom_val.setText(f"{value}%")
        new_size = self.base_font_size * (value / 100.0)
        
        font = self.text_edit.font()
        font.setPointSizeF(new_size)
        self.text_edit.setFont(font)

    # 实时更新字数并改变颜色
    def update_char_count(self):
        text = self.text_edit.toPlainText()
        count = len(text)
        self.lbl_char_count.setText(f"字数: {count}")

        # 颜色判断逻辑
        if count <= 160:
            color_hex = "#00FF7F" 
        elif 161 <= count <= 180:
            color_hex = "#FFA500" 
        else:
            color_hex = "#FF0000" 

        self.lbl_char_count.setStyleSheet(f"""
            color: {color_hex}; 
            font-size: 15px; 
            font-weight: bold; 
            padding-left: 10px;
        """)

    def handle_file_drop(self, file_path):
        target = file_path
        if os.path.isdir(target):
            self.load_folder_images(target)
        elif os.path.isfile(target):
            folder = os.path.dirname(target)
            self.load_folder_images(folder)
            filename = os.path.basename(target)
            for i, path in enumerate(self.image_files):
                if filename in path:
                    self.current_index = i
                    self.load_pair(i)
                    break

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择图片所在文件夹")
        if folder:
            self.load_folder_images(folder)

    def load_folder_images(self, folder_path):
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp']
        self.image_files = []
        for ext in extensions:
            self.image_files.extend(glob.glob(os.path.join(folder_path, ext)))
        self.image_files.sort()

        if not self.image_files:
            QMessageBox.warning(self, "提示", "该目录下没有找到图片文件。")
            return

        self.current_index = 0
        self.load_pair(0)
        self.toggle_buttons(True)

    def toggle_buttons(self, enabled):
        self.btn_prev.setEnabled(enabled)
        self.btn_next.setEnabled(enabled)
        self.btn_save.setEnabled(enabled)
        self.btn_sys_open.setEnabled(enabled)
        self.btn_copy_img.setEnabled(enabled)

    def navigate(self, step):
        if not self.image_files:
            return
        self.save_current_text()
        new_index = self.current_index + step
        if 0 <= new_index < len(self.image_files):
            self.current_index = new_index
            self.load_pair(new_index)
        else:
            msg = "已经是第一张了" if step < 0 else "已经是最后一张了"
            print(msg)

    def load_pair(self, index):
        if index < 0 or index >= len(self.image_files):
            return

        img_path = self.image_files[index]
        self.image_viewer.load_image(img_path)
        
        base_name = os.path.splitext(img_path)[0]
        self.current_txt_path = base_name + ".txt"

        content = ""
        if os.path.exists(self.current_txt_path):
            try:
                with open(self.current_txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"读取错误: {str(e)}"
        else:
            content = ""

        self.text_edit.setPlainText(content)
        
        self.update_char_count()
        
        filename = os.path.basename(img_path)
        self.lbl_info.setText(f"当前文件 [{index+1}/{len(self.image_files)}]: {filename}")
        self.setWindowTitle(f"小邵的打标机 - 正在编辑: {filename}")

    def save_current_text(self):
        if not self.current_txt_path:
            return
        content = self.text_edit.toPlainText()
        try:
            with open(self.current_txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"已保存: {self.current_txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())