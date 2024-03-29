import sys
import os
import time
from PIL import Image
from threading import Thread
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar, QLabel,
    QListWidget, QMessageBox, QCheckBox, QLineEdit
)
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
import qtmodern.styles
import qtmodern.windows
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import QtGui

# Initialize with empty list
folders_to_search = []

button_style = "QPushButton { min-width: 200px; min-height: 40px; }"

class ResizeThread(QThread):
    progress = pyqtSignal(int)
    remaining_time = pyqtSignal(str)

    def __init__(self, target_size, total_images):
        QThread.__init__(self)
        self.target_size = target_size
        self.total_images = total_images
        self.start_time = time.time()
        self.has_low_resolution_images = False

    def run(self):
        images_processed = 0
        try:
            for folder in folders_to_search:
                for dirpath, dirnames, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png"):
                            image_path = os.path.join(dirpath, filename)
                            try:
                                image = Image.open(image_path)
                                width, height = image.size
                                if width < self.target_size[0] or height < self.target_size[1]:
                                    self.has_low_resolution_images = True
                                    image.close()
                                    os.remove(image_path)
                                    continue
                                left = (width - self.target_size[0]) / 2
                                top = (height - self.target_size[1]) / 2
                                right = (width + self.target_size[0]) / 2
                                bottom = (height + self.target_size[1]) / 2
                                image = image.crop((left, top, right, bottom))
                                image.save(image_path)
                                images_processed += 1
                                self.progress.emit(images_processed)
                                self.update_remaining_time(images_processed)
                                image.close()
                            except Exception as e:
                                print(e)
                                image.close()
                                os.remove(image_path)
                                continue
        except Exception as e:
            print(e)

    def update_remaining_time(self, images_processed):
        elapsed_time = time.time() - self.start_time
        remaining_time = elapsed_time * (self.total_images - images_processed) / images_processed
        hours, rem = divmod(remaining_time, 3600)
        minutes, seconds = divmod(rem, 60)
        self.remaining_time.emit(f"預估剩餘時間: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

class Application(QWidget):
    def __init__(self):
        super().__init__()

        self.TARGET_SIZE = [500, 500]
        self.base_dir_enabled = True

        self.setWindowTitle('Trim')
        app.setWindowIcon(QtGui.QIcon('crop.ico'))

        self.folder_entry = QLineEdit()
        self.add_folder_button = QPushButton("新增需裁減的資料夾名稱")
        self.add_folder_button.setStyleSheet(button_style)
        self.add_folder_button.clicked.connect(self.add_folder)

        self.remove_folder_button = QPushButton("刪除資料夾名稱")
        self.remove_folder_button.setStyleSheet(button_style)
        self.remove_folder_button.clicked.connect(self.remove_folder)

        self.folders = QListWidget()
        for folder in folders_to_search:
            self.folders.addItem(folder)

        self.start_button = QPushButton("開始執行")
        self.start_button.setStyleSheet(button_style)
        self.start_button.clicked.connect(self.start_resizing)

        self.progress = QProgressBar()

        self.remaining_time_label = QLabel()

        self.width_entry = QLineEdit("500")
        self.height_entry = QLineEdit("500")

        self.width_label = QLabel("指定裁減寬度(X軸)")
        self.height_label = QLabel("指定裁減高度(Y軸)")

        self.update_size_button = QPushButton("更新尺寸 (如有更新尺寸需點擊)")
        self.update_size_button.setStyleSheet(button_style)
        self.update_size_button.clicked.connect(self.update_size)

        layout = QVBoxLayout()
        layout.addWidget(self.add_folder_button)
        layout.addWidget(self.remove_folder_button)
        layout.addWidget(self.folders)
        layout.addWidget(self.start_button)
        layout.addWidget(self.progress)
        layout.addWidget(self.remaining_time_label)
        layout.addWidget(self.width_label)
        layout.addWidget(self.width_entry)
        layout.addWidget(self.height_label)
        layout.addWidget(self.height_entry)
        layout.addWidget(self.update_size_button)
        self.setLayout(layout)

    @pyqtSlot()
    def start_resizing(self):
        self.start_button.setEnabled(False)
        self.width_entry.setEnabled(False)  # Disable width entry
        self.height_entry.setEnabled(False)  # Disable height entry
        self.total_images = self.count_images()  # added this line
        self.progress.setMaximum(self.total_images)  # added this line
        self.thread = ResizeThread(self.TARGET_SIZE, self.total_images)  # modified this line
        self.thread.progress.connect(self.update_progress)
        self.thread.remaining_time.connect(self.update_remaining_time)
        self.thread.finished.connect(self.show_completion_message)
        self.thread.start()

    @pyqtSlot()
    def show_completion_message(self):
        if self.thread.has_low_resolution_images:
            QMessageBox.information(self, "  ", "程式已成功執行完畢，但照片內含有低於裁切標準的照片，已自動刪除")
        else:
            QMessageBox.information(self, "  ", "程式已成功執行完畢")

    @pyqtSlot(int)
    def update_progress(self, val):
        self.progress.setValue(val)
        if val == self.total_images:  # Check if progress reaches 100%
            self.progress.setFormat("100%")  # Update the progress bar format

    @pyqtSlot(str)
    def update_remaining_time(self, val):
        self.remaining_time_label.setText(val)

    @pyqtSlot()
    def add_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if folder_path:  # Ensure that a directory is actually selected by the user
            if folder_path not in folders_to_search:
                folders_to_search.append(folder_path)
                self.folders.clear()
                for folder in folders_to_search:
                    self.folders.addItem(folder)

    @pyqtSlot()
    def remove_folder(self):
        folder_name = self.folders.currentItem().text()
        if folder_name in folders_to_search:
            folders_to_search.remove(folder_name)
            listItems = self.folders.findItems(folder_name, Qt.MatchExactly)
            if not listItems:
                return
            for item in listItems:
                self.folders.takeItem(self.folders.row(item))

    def count_images(self):
        count = 0
        for folder in folders_to_search:
            for dirpath, dirnames, filenames in os.walk(folder):
                for filename in filenames:
                    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                        count += 1
        return count

    @pyqtSlot()
    def update_size(self):
        try:
            new_width = int(self.width_entry.text())
            new_height = int(self.height_entry.text())

            if new_width < 500 or new_height < 500:
                reply = QMessageBox.question(self, "警告", "請確認X,Y軸參數是否要低於500", QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    pass
                else:
                    if new_width < 500:
                        new_width = 500
                        self.width_entry.setText(str(new_width))
                    if new_height < 500:
                        new_height = 500
                        self.height_entry.setText(str(new_height))
            self.TARGET_SIZE = [new_width, new_height]
            QMessageBox.information(self, "  ", "尺寸已被更新為 {} x {}".format(new_width, new_height))
        except ValueError:
            QMessageBox.critical(self, " ", "寬度和高度請輸入整數.")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set the font and size
    font = QFont("微軟正黑體", 9)
    app.setFont(font)

    # Set the global stylesheet
    app.setStyleSheet("""
        QLabel { color: #FFFFFF; }
        QLineEdit { color: #FFFFFF; }
        QPushButton { color: #FFFFFF; min-width: 500px; min-height: 100px; }
        QListWidget { color: #FFFFFF; }
    """)
    # Set the style for all QPushButton objects
    app.setStyleSheet("QPushButton { min-width: 500px; min-height: 100px; }")

    # Apply the dark theme
    qtmodern.styles.dark(app)

    window = Application()

    # Wrap the window in a ModernWindow
    mw = qtmodern.windows.ModernWindow(window)
    mw.setGeometry(350, 150, 1100, 800)

    mw.show()
    sys.exit(app.exec_())
