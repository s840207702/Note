import sys
import os
import sqlite3
import base64
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit,
    QTextEdit, QSplitter, QToolBar, QAction, QTreeWidget, QTreeWidgetItem,
    QMenu, QMessageBox, QFileDialog, QInputDialog, QHBoxLayout, QStyle, QLabel, QColorDialog, QFrame, QDesktopWidget,
    QTextBrowser, QSizePolicy, QDialog, QPushButton, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QSize, QEvent, QUrl, QBuffer, QIODevice
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QTextCharFormat, QFontDatabase, QPixmap, QTextBlockFormat, \
    QTextListFormat, QColor, QDesktopServices, QCursor

# 导入应用程序相关图标的 Base64 编码
from image_base64 import (
    app_icon_base64, new_note_icon_base64, new_folder_icon_base64,
    collapse_icon_base64, folder_icon_base64, note_icon_base64,
    highlight_icon_base64
)

# 导入文本编辑器相关图标的 Base64 编码
from image_base64 import (
    bold_icon_base64, italic_icon_base64, underline_icon_base64, color_icon_base64,
    separator_icon_base64, ordered_list_icon_base64, unordered_list_icon_base64,
    task_list_icon_base64, link_icon_base64, h1_icon_base64, h2_icon_base64, h3_icon_base64,
    find_material_icon_base64, strikethrough_icon_base64, insert_image_icon_base64,
    shortcut_icon_base64
)


def get_icon_from_base64(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return QIcon(pixmap)

class ShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键提示")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout()

        # 使用 QScrollArea 以支持内容溢出时滚动
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)

        shortcuts = [
            ("加粗", "Ctrl+B"),
            ("斜体", "Ctrl+I"),
            ("下划线", "Ctrl+U"),
            ("撤销", "Ctrl+Z"),
            ("恢复", "Ctrl+Y"),
            ("插入图片", "Ctrl+Shift+I"),
            ("插入超链接", "Ctrl+K"),
            ("插入有序列表", "Ctrl+Shift+O"),
            ("插入无序列表", "Ctrl+Shift+U"),
            ("插入任务列表", "Ctrl+Shift+T"),
            ("插入分割线", "Ctrl+Shift+S"),
            ("插入一级标题", "Ctrl+Alt+1"),
            ("插入二级标题", "Ctrl+Alt+2"),
            ("插入三级标题", "Ctrl+Alt+3"),
            ("高亮模式", "Ctrl+H"),
            ("找素材模式", "Ctrl+F"),
            ("删除线", "Ctrl+Shift+D"),
        ]

        for i, (action, shortcut) in enumerate(shortcuts):
            label_action = QLabel(action)
            label_shortcut = QLabel(shortcut)
            label_action.setStyleSheet("font-size: 14px;")
            label_shortcut.setStyleSheet("font-size: 14px;")
            scroll_layout.addWidget(label_action, i, 0, alignment=Qt.AlignLeft)
            scroll_layout.addWidget(label_shortcut, i, 1, alignment=Qt.AlignLeft)

        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        self.setLayout(layout)

class ElegantNoteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('非丨优雅笔记')
        self.setWindowIcon(get_icon_from_base64(app_icon_base64))
        self.resize(1100, 1500)  # 调整窗口尺寸，增加宽度以显示更多图标

        # 窗口居中
        qt_rectangle = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())

        self.current_note_id = None
        self.highlight_mode = False  # 高亮模式标志

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(5000)  # 每5秒自动保存一次

        # 设置全局字体为微软雅黑
        font = QFont("微软雅黑", 10)
        QApplication.setFont(font)

        self.init_db()
        self.init_ui()

    def init_db(self):
        self.conn = sqlite3.connect('notes.db')
        self.cursor = self.conn.cursor()
        # 确保数据完整性，即使在突然断电的情况下
        self.cursor.execute('PRAGMA synchronous = FULL')
        # 创建文件夹表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY(parent_id) REFERENCES folders(id)
            )
        ''')
        # 创建笔记表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER,
                title TEXT NOT NULL,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY(folder_id) REFERENCES folders(id)
            )
        ''')
        self.conn.commit()

    def init_ui(self):
        # 主窗口的中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()  # 使用水平布局

        # 左侧布局（笔记树和顶部按钮）
        left_layout = QVBoxLayout()

        # 顶部工具栏（左侧）
        left_toolbar = QToolBar()
        left_toolbar.setIconSize(QSize(32, 32))  # 增大按钮尺寸
        left_toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 设置工具栏的大小策略，使其宽度与笔记树一致

        # 折叠全部按钮
        collapse_icon = get_icon_from_base64(collapse_icon_base64)
        collapse_action = QAction(collapse_icon, "折叠全部 (Ctrl+Shift+C)", self)
        collapse_action.triggered.connect(self.collapse_all)
        collapse_action.setShortcut("Ctrl+Shift+C")
        collapse_action.setToolTip("折叠全部 (Ctrl+Shift+C)")
        left_toolbar.addAction(collapse_action)

        # 新建文件夹按钮
        new_folder_icon = get_icon_from_base64(new_folder_icon_base64)
        new_folder_action = QAction(new_folder_icon, "新建文件夹 (Ctrl+Shift+F)", self)
        new_folder_action.triggered.connect(self.new_folder)
        new_folder_action.setShortcut("Ctrl+Shift+F")
        new_folder_action.setToolTip("新建文件夹 (Ctrl+Shift+F)")
        left_toolbar.addAction(new_folder_action)

        # 新建笔记按钮
        new_note_icon = get_icon_from_base64(new_note_icon_base64)
        new_note_action = QAction(new_note_icon, "新建笔记 (Ctrl+Shift+N)", self)
        new_note_action.triggered.connect(self.new_note)
        new_note_action.setShortcut("Ctrl+Shift+N")
        new_note_action.setToolTip("新建笔记 (Ctrl+Shift+N)")
        left_toolbar.addAction(new_note_action)

        # 快捷键提示按钮
        shortcut_icon = get_icon_from_base64(shortcut_icon_base64)  # 假设您已将快捷键提示按钮的 Base64 编码添加到 image_base64.py
        shortcut_action = QAction(shortcut_icon, "快捷键提示 (Ctrl+Shift+H)", self)
        shortcut_action.triggered.connect(self.show_shortcut_dialog)
        shortcut_action.setShortcut("Ctrl+Shift+H")
        shortcut_action.setToolTip("快捷键提示 (Ctrl+Shift+H)")
        left_toolbar.addAction(shortcut_action)

        # 设置按钮均匀分布
        left_toolbar.setMovable(False)  # 防止工具栏被移动
        left_toolbar.setStyleSheet("QToolBar { spacing: 17px; }")  # 设置按钮间距为17px，刚刚好tmd

        # 添加伸缩空间以确保按钮均匀分布
        left_toolbar.addWidget(QWidget())  # 左侧添加一个伸缩空间
        left_toolbar.addAction(collapse_action)
        left_toolbar.addWidget(QWidget())  # Spacer
        left_toolbar.addAction(new_folder_action)
        left_toolbar.addWidget(QWidget())  # Spacer
        left_toolbar.addAction(new_note_action)
        left_toolbar.addWidget(QWidget())  # Spacer
        left_toolbar.addAction(shortcut_action)
        left_toolbar.addWidget(QWidget())  # 右侧添加一个伸缩空间

        left_layout.addWidget(left_toolbar)

        # 笔记树（左侧）
        self.notes_tree = QTreeWidget()
        self.notes_tree.setHeaderHidden(True)
        self.notes_tree.itemClicked.connect(self.load_note)
        self.notes_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.notes_tree.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.notes_tree)

        # 左侧小部件
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # 右侧布局（编辑器工具栏和笔记编辑器）
        right_layout = QVBoxLayout()

        # 文本编辑器工具栏（右侧）
        editor_toolbar = QToolBar()
        editor_toolbar.setIconSize(QSize(24, 24))
        editor_toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 确保工具栏宽度与笔记编辑器一致

        # 插入图片按钮
        insert_image_icon = get_icon_from_base64(insert_image_icon_base64)
        insert_image_action = QAction(insert_image_icon, "插入图片 (Ctrl+Shift+I)", self)
        insert_image_action.setShortcut("Ctrl+Shift+I")
        insert_image_action.triggered.connect(self.insert_image)
        insert_image_action.setToolTip("插入图片 (Ctrl+Shift+I)")
        editor_toolbar.addAction(insert_image_action)

        # 加粗
        bold_icon = get_icon_from_base64(bold_icon_base64)
        bold_action = QAction(bold_icon, "加粗 (Ctrl+B)", self)
        bold_action.setShortcut("Ctrl+B")
        bold_action.triggered.connect(self.set_bold)
        bold_action.setToolTip("加粗 (Ctrl+B)")
        editor_toolbar.addAction(bold_action)

        # 斜体
        italic_icon = get_icon_from_base64(italic_icon_base64)
        italic_action = QAction(italic_icon, "斜体 (Ctrl+I)", self)
        italic_action.setShortcut("Ctrl+I")
        italic_action.triggered.connect(self.set_italic)
        italic_action.setToolTip("斜体 (Ctrl+I)")
        editor_toolbar.addAction(italic_action)

        # 下划线
        underline_icon = get_icon_from_base64(underline_icon_base64)
        underline_action = QAction(underline_icon, "下划线 (Ctrl+U)", self)
        underline_action.setShortcut("Ctrl+U")
        underline_action.triggered.connect(self.set_underline)
        underline_action.setToolTip("下划线 (Ctrl+U)")
        editor_toolbar.addAction(underline_action)

        # 更改文字颜色
        color_icon = get_icon_from_base64(color_icon_base64)
        color_action = QAction(color_icon, "更改文字颜色", self)
        color_action.triggered.connect(self.change_text_color)
        color_action.setToolTip("更改文字颜色")
        editor_toolbar.addAction(color_action)

        # 插入分割线
        separator_icon = get_icon_from_base64(separator_icon_base64)
        separator_action = QAction(separator_icon, "插入分割线 (Ctrl+Shift+S)", self)
        separator_action.setShortcut("Ctrl+Shift+S")
        separator_action.triggered.connect(self.insert_separator)
        separator_action.setToolTip("插入分割线 (Ctrl+Shift+S)")
        editor_toolbar.addAction(separator_action)

        # 插入有序列表
        ordered_list_icon = get_icon_from_base64(ordered_list_icon_base64)
        ordered_list_action = QAction(ordered_list_icon, "插入有序列表 (Ctrl+Shift+O)", self)
        ordered_list_action.setShortcut("Ctrl+Shift+O")
        ordered_list_action.triggered.connect(self.insert_ordered_list)
        ordered_list_action.setToolTip("插入有序列表 (Ctrl+Shift+O)")
        editor_toolbar.addAction(ordered_list_action)

        # 插入无序列表
        unordered_list_icon = get_icon_from_base64(unordered_list_icon_base64)
        unordered_list_action = QAction(unordered_list_icon, "插入无序列表 (Ctrl+Shift+U)", self)
        unordered_list_action.setShortcut("Ctrl+Shift+U")
        unordered_list_action.triggered.connect(self.insert_unordered_list)
        unordered_list_action.setToolTip("插入无序列表 (Ctrl+Shift+U)")
        editor_toolbar.addAction(unordered_list_action)

        # 插入任务列表
        task_list_icon = get_icon_from_base64(task_list_icon_base64)
        task_list_action = QAction(task_list_icon, "插入任务列表 (Ctrl+Shift+T)", self)
        task_list_action.setShortcut("Ctrl+Shift+T")
        task_list_action.triggered.connect(self.insert_task_list)
        task_list_action.setToolTip("插入任务列表 (Ctrl+Shift+T)")
        editor_toolbar.addAction(task_list_action)

        # 插入超链接
        link_icon = get_icon_from_base64(link_icon_base64)
        link_action = QAction(link_icon, "插入超链接 (Ctrl+K)", self)
        link_action.setShortcut("Ctrl+K")
        link_action.triggered.connect(self.insert_link)
        link_action.setToolTip("插入超链接 (Ctrl+K)")
        editor_toolbar.addAction(link_action)

        # 插入一级标题
        h1_icon = get_icon_from_base64(h1_icon_base64)
        h1_action = QAction(h1_icon, "插入一级标题 (Ctrl+Alt+1)", self)
        h1_action.setShortcut("Ctrl+Alt+1")
        h1_action.triggered.connect(lambda: self.set_heading(1))
        h1_action.setToolTip("插入一级标题 (Ctrl+Alt+1)")
        editor_toolbar.addAction(h1_action)

        # 插入二级标题
        h2_icon = get_icon_from_base64(h2_icon_base64)
        h2_action = QAction(h2_icon, "插入二级标题 (Ctrl+Alt+2)", self)
        h2_action.setShortcut("Ctrl+Alt+2")
        h2_action.triggered.connect(lambda: self.set_heading(2))
        h2_action.setToolTip("插入二级标题 (Ctrl+Alt+2)")
        editor_toolbar.addAction(h2_action)

        # 插入三级标题
        h3_icon = get_icon_from_base64(h3_icon_base64)
        h3_action = QAction(h3_icon, "插入三级标题 (Ctrl+Alt+3)", self)
        h3_action.setShortcut("Ctrl+Alt+3")
        h3_action.triggered.connect(lambda: self.set_heading(3))
        h3_action.setToolTip("插入三级标题 (Ctrl+Alt+3)")
        editor_toolbar.addAction(h3_action)

        # 高亮模式
        highlight_icon = get_icon_from_base64(highlight_icon_base64)
        self.highlight_action = QAction(highlight_icon, "高亮模式 (Ctrl+H)", self)
        self.highlight_action.setShortcut("Ctrl+H")
        self.highlight_action.setToolTip("高亮模式 (Ctrl+H)")
        self.highlight_action.setCheckable(True)
        self.highlight_action.triggered.connect(self.toggle_highlight_mode)
        editor_toolbar.addAction(self.highlight_action)

        # 找素材模式
        find_material_icon = get_icon_from_base64(find_material_icon_base64)
        self.find_material_action = QAction(find_material_icon, "找素材模式 (Ctrl+F)", self)
        self.find_material_action.setShortcut("Ctrl+F")
        self.find_material_action.setToolTip("找素材模式 (Ctrl+F)")
        self.find_material_action.setCheckable(True)
        self.find_material_action.triggered.connect(self.toggle_find_material_mode)
        editor_toolbar.addAction(self.find_material_action)

        # 删除线
        strikethrough_icon = get_icon_from_base64(strikethrough_icon_base64)
        strikethrough_action = QAction(strikethrough_icon, "删除线 (Ctrl+Shift+D)", self)
        strikethrough_action.setShortcut("Ctrl+Shift+D")
        strikethrough_action.triggered.connect(self.set_strikethrough)
        strikethrough_action.setToolTip("删除线 (Ctrl+Shift+D)")
        editor_toolbar.addAction(strikethrough_action)

        # 撤销
        undo_action = QAction(QIcon(), "撤销 (Ctrl+Z)", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.note_editor.undo)
        undo_action.setToolTip("撤销 (Ctrl+Z)")
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(undo_action)

        # 恢复
        redo_action = QAction(QIcon(), "恢复 (Ctrl+Y)", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.note_editor.redo)
        redo_action.setToolTip("恢复 (Ctrl+Y)")
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(redo_action)

        # 设置按钮均匀分布
        editor_toolbar.setMovable(False)  # 防止工具栏被移动
        editor_toolbar.setStyleSheet("QToolBar { spacing: 6px; }")  # 设置按钮间距为6px

        # 添加伸缩空间以确保按钮均匀分布
        editor_toolbar.addWidget(QWidget())  # 左侧添加一个伸缩空间

        # 添加编辑工具按钮和中间伸缩空间
        editor_toolbar.addAction(bold_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(italic_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(underline_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(color_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(separator_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(ordered_list_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(unordered_list_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(task_list_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(link_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(h1_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(h2_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(h3_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(self.highlight_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(self.find_material_action)
        editor_toolbar.addWidget(QWidget())  # Spacer
        editor_toolbar.addAction(strikethrough_action)

        # 添加右侧伸缩空间
        editor_toolbar.addWidget(QWidget())  # 右侧添加一个伸缩空间

        right_layout.addWidget(editor_toolbar)

        # 笔记编辑器（右侧）
        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText('在这里开始书写您的笔记...')
        self.note_editor.textChanged.connect(self.update_word_count)  # 当文本改变时更新字数统计
        self.note_editor.textChanged.connect(self.auto_save)  # 实时保存

        # 添加以下两行代码
        self.note_editor.setAcceptDrops(True)
        self.note_editor.viewport().setAcceptDrops(True)

        # 设置链接相关属性
        self.note_editor.setReadOnly(False)
        # self.note_editor.setOpenExternalLinks(True)  # 移除或注释掉
        self.note_editor.setTextInteractionFlags(Qt.TextEditorInteraction | Qt.LinksAccessibleByMouse)

        # 移除或注释掉连接 anchorClicked 信号的代码
        # self.note_editor.anchorClicked.connect(self.handle_link_activated)

        # 将笔记编辑器和字数统计标签叠放在一起
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addWidget(self.note_editor)

        # 字数统计标签
        self.word_count_label = QLabel("字数：0", self.note_editor)
        self.word_count_label.setStyleSheet("padding: 5px; background-color: rgba(255, 255, 255, 0);")
        self.word_count_label.move(
            self.note_editor.viewport().width() - 80,
            self.note_editor.viewport().height() - 20
        )
        self.word_count_label.show()

        # 安装事件过滤器以更新字数标签位置和处理高亮模式
        self.note_editor.viewport().installEventFilter(self)

        editor_layout.addWidget(self.word_count_label)

        right_layout.addWidget(editor_widget)

        # 右侧小部件
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # 使用 QSplitter 分割左右区域
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # 笔记树范围控制
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(0, 7)
        main_layout.addWidget(splitter)

        central_widget.setLayout(main_layout)

        # 应用样式表，提升UI的优雅度
        self.apply_stylesheet()

        # 加载文件夹和笔记
        self.load_folders_and_notes()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTreeWidget {
                background-color: #ffffff;
                padding: 5px;
                font-size: 14px;
            }
            QTreeWidget::item {
                margin-left: -10px; /* 减少左边距 */
                height: 25px;        /* 增加项的高度 */
            }
            QTextEdit {
                border: none;
                background-color: #ffffff;
                padding: 10px;
                font-size: 16px;
                line-height: 1.6; /* 设置行间距 */
                font-family: '微软雅黑';
            }
            QToolBar {
                background: #ffffff;
                border-bottom: 1px solid #ccc;
            }
            QToolButton {
                background: transparent;
                border: none;
                width: 32px;  /* 固定按钮宽度，确保均匀分布 */
                height: 32px;
            }
            QToolButton:hover {
                background: #e6e6e6;
            }
            QLabel {
                font-size: 12px;
                color: #555;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #ccc;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e6e6e6;
            }
        """)

    def load_folders_and_notes(self):
        self.notes_tree.clear()
        # 加载根文件夹（parent_id为NULL）
        self.cursor.execute('SELECT id, name FROM folders WHERE parent_id IS NULL')
        root_folders = self.cursor.fetchall()
        for folder_id, folder_name in root_folders:
            folder_item = QTreeWidgetItem([folder_name])
            folder_item.setData(0, Qt.UserRole, ('folder', folder_id))
            folder_item.setIcon(0, get_icon_from_base64(folder_icon_base64))  # 添加文件夹图标
            self.load_subfolders_and_notes(folder_item, folder_id)
            self.notes_tree.addTopLevelItem(folder_item)

        # 加载未分类的笔记（folder_id为NULL）
        self.cursor.execute('SELECT id, title FROM notes WHERE folder_id IS NULL')
        notes = self.cursor.fetchall()
        for note_id, note_title in notes:
            note_item = QTreeWidgetItem([note_title])
            note_item.setData(0, Qt.UserRole, ('note', note_id))
            note_item.setIcon(0, get_icon_from_base64(note_icon_base64))  # 添加笔记图标
            self.notes_tree.addTopLevelItem(note_item)

        # 展开所有节点
        self.notes_tree.expandAll()

    def load_subfolders_and_notes(self, parent_item, parent_folder_id):
        # 加载子文件夹
        self.cursor.execute('SELECT id, name FROM folders WHERE parent_id = ?', (parent_folder_id,))
        subfolders = self.cursor.fetchall()
        for folder_id, folder_name in subfolders:
            folder_item = QTreeWidgetItem([folder_name])
            folder_item.setData(0, Qt.UserRole, ('folder', folder_id))
            folder_item.setIcon(0, get_icon_from_base64(folder_icon_base64))  # 添加文件夹图标
            self.load_subfolders_and_notes(folder_item, folder_id)
            parent_item.addChild(folder_item)

        # 加载该文件夹下的笔记
        self.cursor.execute('SELECT id, title FROM notes WHERE folder_id = ?', (parent_folder_id,))
        notes = self.cursor.fetchall()
        for note_id, note_title in notes:
            note_item = QTreeWidgetItem([note_title])
            note_item.setData(0, Qt.UserRole, ('note', note_id))
            note_item.setIcon(0, get_icon_from_base64(note_icon_base64))  # 添加笔记图标
            parent_item.addChild(note_item)

    def new_note(self):
        selected_items = self.notes_tree.selectedItems()
        folder_id = None
        if selected_items:
            item_type, item_id = selected_items[0].data(0, Qt.UserRole)
            if item_type == 'folder':
                folder_id = item_id
            elif item_type == 'note':
                parent_item = selected_items[0].parent()
                if parent_item:
                    parent_type, parent_id = parent_item.data(0, Qt.UserRole)
                    if parent_type == 'folder':
                        folder_id = parent_id

        # 使用自定义对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle('新建笔记')
        dialog.setLabelText('请输入笔记标题：')
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.resize(250, 100)  # 增大宽度

        # 移除右上角的问号（QInputDialog默认没有问号，可以忽略）

        if dialog.exec_() == QInputDialog.Accepted:
            title = dialog.textValue()
            if title:
                timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
                self.cursor.execute('INSERT INTO notes (folder_id, title, content, timestamp) VALUES (?, ?, ?, ?)',
                                    (folder_id, title, '', timestamp))
                self.conn.commit()
                self.load_folders_and_notes()
                self.statusBar().showMessage('新建笔记成功', 2000)
            else:
                QMessageBox.warning(self, '错误', '笔记标题不能为空')

    def new_folder(self):
        selected_items = self.notes_tree.selectedItems()
        parent_folder_id = None
        if selected_items:
            item_type, item_id = selected_items[0].data(0, Qt.UserRole)
            if item_type == 'folder':
                parent_folder_id = item_id

        # 使用自定义对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle('新建文件夹')
        dialog.setLabelText('请输入文件夹名称：')
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.resize(250, 100)  # 增大宽度

        # 移除右上角的问号（QInputDialog默认没有问号，可以忽略）

        if dialog.exec_() == QInputDialog.Accepted:
            name = dialog.textValue()
            if name:
                self.cursor.execute('INSERT INTO folders (name, parent_id) VALUES (?, ?)', (name, parent_folder_id))
                self.conn.commit()
                self.load_folders_and_notes()
                self.statusBar().showMessage('新建文件夹成功', 2000)
            else:
                QMessageBox.warning(self, '错误', '文件夹名称不能为空')

    def load_note(self, item, column):
        item_type, item_id = item.data(0, Qt.UserRole)
        if item_type == 'note':
            self.current_note_id = item_id
            self.cursor.execute('SELECT content FROM notes WHERE id = ?', (self.current_note_id,))
            result = self.cursor.fetchone()
            content = result[0] if result else ''
            self.note_editor.setHtml(content)
            self.update_word_count()
        else:
            self.current_note_id = None
            self.note_editor.clear()
            self.update_word_count()

    def show_context_menu(self, position):
        selected_item = self.notes_tree.itemAt(position)
        if selected_item:
            item_type, item_id = selected_item.data(0, Qt.UserRole)
            menu = QMenu()
            if item_type == 'folder':
                rename_action = QAction("重命名文件夹", self)
                rename_action.triggered.connect(lambda: self.rename_folder(selected_item))
                menu.addAction(rename_action)

                delete_action = QAction("删除文件夹", self)
                delete_action.triggered.connect(lambda: self.delete_folder(selected_item))
                menu.addAction(delete_action)
            elif item_type == 'note':
                rename_action = QAction("重命名笔记", self)
                rename_action.triggered.connect(lambda: self.rename_note(selected_item))
                menu.addAction(rename_action)

                delete_action = QAction("删除笔记", self)
                delete_action.triggered.connect(lambda: self.delete_note(selected_item))
                menu.addAction(delete_action)
            menu.exec_(self.notes_tree.viewport().mapToGlobal(position))

    def rename_folder(self, item):
        name, ok = QInputDialog.getText(self, '重命名文件夹', '请输入新的文件夹名称：', text=item.text(0))
        if ok and name:
            item_type, folder_id = item.data(0, Qt.UserRole)
            self.cursor.execute('UPDATE folders SET name = ? WHERE id = ?', (name, folder_id))
            self.conn.commit()
            self.load_folders_and_notes()
            self.statusBar().showMessage('文件夹已重命名', 2000)
        else:
            QMessageBox.warning(self, '错误', '文件夹名称不能为空')

    def delete_folder(self, item):
        reply = QMessageBox.question(self, '删除文件夹', '删除文件夹将同时删除其包含的所有笔记，确定要删除吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            item_type, folder_id = item.data(0, Qt.UserRole)
            self.delete_folder_recursive(folder_id)
            self.conn.commit()
            self.load_folders_and_notes()
            self.statusBar().showMessage('文件夹已删除', 2000)

    def delete_folder_recursive(self, folder_id):
        # 删除子文件夹
        self.cursor.execute('SELECT id FROM folders WHERE parent_id = ?', (folder_id,))
        subfolders = self.cursor.fetchall()
        for subfolder_id, in subfolders:
            self.delete_folder_recursive(subfolder_id)
        # 删除文件夹下的笔记
        self.cursor.execute('DELETE FROM notes WHERE folder_id = ?', (folder_id,))
        # 删除文件夹
        self.cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))

    def rename_note(self, item):
        title, ok = QInputDialog.getText(self, '重命名笔记', '请输入新的笔记标题：', text=item.text(0))
        if ok and title:
            item_type, note_id = item.data(0, Qt.UserRole)
            self.cursor.execute('UPDATE notes SET title = ? WHERE id = ?', (title, note_id))
            self.conn.commit()
            self.load_folders_and_notes()
            self.statusBar().showMessage('笔记已重命名', 2000)
        else:
            QMessageBox.warning(self, '错误', '笔记标题不能为空')

    def delete_note(self, item):
        reply = QMessageBox.question(self, '删除笔记', '确定要删除该笔记吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            item_type, note_id = item.data(0, Qt.UserRole)
            self.cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
            self.conn.commit()
            self.load_folders_and_notes()
            self.note_editor.clear()
            self.update_word_count()
            self.statusBar().showMessage('笔记已删除', 2000)

    def auto_save(self):
        if self.current_note_id is not None:
            content = self.note_editor.toHtml()
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            self.cursor.execute('UPDATE notes SET content = ?, timestamp = ? WHERE id = ?', (content, timestamp, self.current_note_id))
            self.conn.commit()
            self.statusBar().showMessage('笔记已自动保存', 1000)

    # 折叠全部节点
    def collapse_all(self):
        self.notes_tree.collapseAll()

    # 文本编辑器功能实现
    def set_bold(self):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontWeight(QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.mergeCharFormat(fmt)
        else:
            cursor.select(QTextCursor.LineUnderCursor)
            fmt = cursor.charFormat()
            fmt.setFontWeight(QFont.Bold if fmt.fontWeight() != QFont.Bold else QFont.Normal)
            cursor.mergeCharFormat(fmt)

    def set_italic(self):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)
        else:
            cursor.select(QTextCursor.LineUnderCursor)
            fmt = cursor.charFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)

    def set_underline(self):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)
        else:
            cursor.select(QTextCursor.LineUnderCursor)
            fmt = cursor.charFormat()
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)

    def change_text_color(self):
        # 常见颜色列表
        colors = [
            ('黑色', '#000000'),
            ('红色', '#FF0000'),
            ('绿色', '#008000'),
            ('蓝色', '#0000FF'),
            ('黄色', '#FFFF00'),
            ('紫色', '#800080'),
            ('橙色', '#FFA500'),
            ('灰色', '#808080'),
        ]
        menu = QMenu(self)
        for name, color_code in colors:
            action = QAction(name, self)
            action.setData(color_code)
            # 添加颜色图标
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(color_code))
            icon = QIcon(pixmap)
            action.setIcon(icon)
            menu.addAction(action)
        # 显示菜单并获取所选颜色
        action = menu.exec_(QCursor.pos())
        if action:
            color_code = action.data()
            color = QColor(color_code)
            cursor = self.note_editor.textCursor()
            if cursor.hasSelection():
                fmt = cursor.charFormat()
                fmt.setForeground(color)
                cursor.mergeCharFormat(fmt)
            else:
                cursor.select(QTextCursor.LineUnderCursor)
                fmt = cursor.charFormat()
                fmt.setForeground(color)
                cursor.mergeCharFormat(fmt)

    def insert_separator(self):
        cursor = self.note_editor.textCursor()
        cursor.insertHtml("<hr/>")

    def insert_ordered_list(self):
        cursor = self.note_editor.textCursor()
        cursor.insertList(QTextListFormat.ListDecimal)

    def insert_unordered_list(self):
        cursor = self.note_editor.textCursor()
        cursor.insertList(QTextListFormat.ListDisc)

    def insert_task_list(self):
        cursor = self.note_editor.textCursor()
        # 插入一个复选框的HTML
        html = '<input type="checkbox" onclick="toggle_task(this)"> &nbsp;<span>未完成的任务</span><br>'
        cursor.insertHtml(html)

    def insert_link(self):
        url, ok = QInputDialog.getText(self, '插入超链接', '请输入URL：')
        if ok and url:
            text, ok_text = QInputDialog.getText(self, '插入超链接', '显示的文本（可选）：', text=url)
            if ok_text:
                display_text = text if text else url
                html = f'<a href="{url}">{display_text}</a>'
                cursor = self.note_editor.textCursor()
                cursor.insertHtml(html)

    def set_heading(self, level):
        cursor = self.note_editor.textCursor()
        fmt = QTextBlockFormat()
        cursor.select(QTextCursor.LineUnderCursor)
        fmt.setHeadingLevel(level)
        cursor.mergeBlockFormat(fmt)
        char_fmt = QTextCharFormat()
        font_size = 24 - (level * 2)  # 根据标题级别调整字体大小
        font = QFont("微软雅黑", font_size, QFont.Bold)
        char_fmt.setFont(font)
        cursor.mergeCharFormat(char_fmt)

    def update_word_count(self):
        text = self.note_editor.toPlainText()
        word_count = len(text)
        self.word_count_label.setText(f"字数：{word_count}")
        self.update_word_count_position()

    def update_word_count_position(self):
        self.word_count_label.adjustSize()
        self.word_count_label.move(
            self.note_editor.viewport().width() - self.word_count_label.width() - 10,
            self.note_editor.viewport().height() - self.word_count_label.height() - 10
        )

    def toggle_highlight_mode(self, checked):
        if checked:
            self.note_editor.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.note_editor.viewport().setCursor(Qt.IBeamCursor)

    def clear_find_material_highlight(self):
        # 清除所有高亮
        cursor = self.note_editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        fmt = QTextCharFormat()
        fmt.setBackground(Qt.transparent)
        while not cursor.atEnd():
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.mergeCharFormat(fmt)
            cursor.movePosition(QTextCursor.Down)

    def toggle_find_material_mode(self, checked):
        if not checked:
            # 取消模式时，清除高亮
            self.clear_find_material_highlight()
        # 更新鼠标指针样式
        self.note_editor.viewport().setCursor(Qt.PointingHandCursor if checked else Qt.IBeamCursor)

    def set_strikethrough(self):
        cursor = self.note_editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.LineUnderCursor)
        fmt = cursor.charFormat()
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        cursor.mergeCharFormat(fmt)

    def insert_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "Image Files (*.png *.jpg *.bmp *.gif *.ico *.webp);;All Files (*)",
            options=options
        )
        if file_name:
            with open(file_name, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                image_format = os.path.splitext(file_name)[1][1:].lower()  # 获取图片格式，如 'png'
                html_img = f'<img src="data:image/{image_format};base64,{encoded_image}"><br>'
                cursor = self.note_editor.textCursor()
                cursor.insertHtml(html_img)
                self.auto_save()  # 保存更改

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

    # 添加快捷键提示窗口
    def show_shortcut_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键提示")
        dialog.resize(400, 800)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)

        layout = QGridLayout(content)
        layout.setSpacing(10)  # 设置行间距

        shortcuts = [
            {"功能": "加粗", "快捷键": "Ctrl+B"},
            {"功能": "斜体", "快捷键": "Ctrl+I"},
            {"功能": "下划线", "快捷键": "Ctrl+U"},
            {"功能": "插入分割线", "快捷键": "Ctrl+Shift+S"},
            {"功能": "插入有序列表", "快捷键": "Ctrl+Shift+O"},
            {"功能": "插入无序列表", "快捷键": "Ctrl+Shift+U"},
            {"功能": "插入任务列表", "快捷键": "Ctrl+Shift+T"},
            {"功能": "插入超链接", "快捷键": "Ctrl+K"},
            {"功能": "插入一级标题", "快捷键": "Ctrl+Alt+1"},
            {"功能": "插入二级标题", "快捷键": "Ctrl+Alt+2"},
            {"功能": "插入三级标题", "快捷键": "Ctrl+Alt+3"},
            {"功能": "高亮模式", "快捷键": "Ctrl+H"},
            {"功能": "找素材模式", "快捷键": "Ctrl+F"},
            {"功能": "删除线", "快捷键": "Ctrl+Shift+D"},
            {"功能": "撤销", "快捷键": "Ctrl+Z"},
            {"功能": "恢复", "快捷键": "Ctrl+Y"},
        ]

        for i, shortcut in enumerate(shortcuts):
            label_action = QLabel(shortcut["功能"])
            label_shortcut = QLabel(shortcut["快捷键"])
            label_action.setStyleSheet("font-size: 14px;")
            label_shortcut.setStyleSheet("font-size: 14px; font-weight: bold;")
            layout.addWidget(label_action, i, 0, alignment=Qt.AlignLeft)
            layout.addWidget(label_shortcut, i, 1, alignment=Qt.AlignRight)

        scroll_content = QWidget()
        scroll_content.setLayout(layout)
        scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(scroll)

        # 添加关闭按钮
        close_button = QPushButton("关闭", dialog)
        close_button.clicked.connect(dialog.accept)
        main_layout.addWidget(close_button, alignment=Qt.AlignRight)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def eventFilter(self, source, event):
        if source == self.note_editor.viewport():
            if event.type() == QEvent.Resize:
                self.update_word_count_position()
            elif event.type() == QEvent.MouseButtonPress:
                cursor = self.note_editor.cursorForPosition(event.pos())
                block = cursor.block()
                text = block.text()

                # 检测是否点击在任务列表的复选框区域
                # 假设任务列表前缀为 "[ ] " 或 "[x] "
                if text.startswith("[ ] ") or text.startswith("[x] "):
                    # 获取点击位置相对于行的水平位置
                    layout = self.note_editor.document().documentLayout()
                    position = cursor.positionInBlock()
                    # 假设复选框的宽度为 20 像素
                    if position <= 20:
                        # 切换任务完成状态
                        if text.startswith("[ ] "):
                            new_text = "[x] " + text[4:]
                            fmt = QTextCharFormat()
                            fmt.setFontStrikeOut(True)
                        else:
                            new_text = "[ ] " + text[4:]
                            fmt = QTextCharFormat()
                            fmt.setFontStrikeOut(False)

                        cursor.select(QTextCursor.LineUnderCursor)
                        cursor.insertText(new_text, fmt)
                        self.auto_save()  # 保存更改
                        return True  # 事件已处理

                # 处理超链接点击
                anchor = cursor.charFormat().anchorHref()
                if anchor:
                    QDesktopServices.openUrl(QUrl(anchor))
                    return True

                # 处理高亮模式
                if self.highlight_action.isChecked():
                    fmt = QTextCharFormat()
                    fmt.setBackground(QColor('yellow'))
                    cursor.mergeCharFormat(fmt)
                    self.highlight_action.setChecked(False)
                    self.note_editor.viewport().setCursor(Qt.IBeamCursor)
                    return True
                elif self.find_material_action.isChecked():
                    # 找素材模式逻辑
                    # 清除之前的高亮
                    self.clear_find_material_highlight()
                    # 高亮当前行
                    fmt = QTextCharFormat()
                    fmt.setBackground(QColor('yellow'))
                    cursor.mergeCharFormat(fmt)
                    return True
            return False
        return super(ElegantNoteApp, self).eventFilter(source, event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ElegantNoteApp()
    window.show()
    sys.exit(app.exec_())
