import os.path
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from ui.ansys_ui import Ui_AnsysWindow
from numpy import array

class AnsysWindow(QDialog, Ui_AnsysWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.browseNodesButton.clicked.connect(self.browseNodes)
        self.browseElemsButton.clicked.connect(self.browseElems)
        self.uploadButton.clicked.connect(self.uploadFiles)

    def browseNodes(self):self.nodesPathEdit.setText(self.getAnsysFile("Выберите файл узлов Ansys", "Text Files (*.txt)"))
    def browseElems(self):self.elemsPathEdit.setText(self.getAnsysFile("Выберите файл элементов Ansys", "Text Files (*.txt)"))
    def getAnsysFile(self, title, file_filter):return QFileDialog.getOpenFileName(self, title, "", file_filter, options=QFileDialog.ReadOnly)[0]
    
    def checkAnsysFiles(self, nodes_path, elems_path):
        try:
            not_found_files = [path for path in (nodes_path, elems_path) if not os.path.isfile(path)]
            if not_found_files:
                raise FileNotFoundError(f"Файлы не найдены: {', '.join(not_found_files)}")

            with open(nodes_path) as nodes_file, open(elems_path) as elems_file:
                next(nodes_file), next(elems_file)

                self.ansys_nodes = []
                for line in nodes_file:
                    values = line.split()
                    if len(values) != 4:
                        raise ValueError("Неверный формат файла узлов!")
                    self.ansys_nodes.append([float(v.replace(",", ".")) * 100.0 for v in values[1:3]])

                self.ansys_elems = []
                for line in elems_file:
                    values = line.split()
                    if len(values) != 5:
                        raise ValueError("Неверный формат файла элементов!")
                    self.ansys_elems.append([int(node) - 1 for node in values[2:5]])

                self.ansys_nodes = array(self.ansys_nodes)
                self.ansys_elems = array(self.ansys_elems)

            return True
        except (FileNotFoundError, ValueError, IndexError) as e:
            QMessageBox.critical(self, "ОШИБКА", f"{str(e)}")
            return False

    def uploadFiles(self):
        nodes_path, elems_path = self.nodesPathEdit.text(), self.elemsPathEdit.text()
        if nodes_path and elems_path:
            if self.checkAnsysFiles(nodes_path, elems_path):
                self.parent.ansys_nodes, self.parent.ansys_elems = self.ansys_nodes, self.ansys_elems
                self.parent.ansysDataLoaded = True
                QMessageBox.information(self, "СООБЩЕНИЕ", "Файлы успешно загружены!")
                self.accept()
        else:
            QMessageBox.warning(self, "ПРЕДУПРЕЖДЕНИЕ", "Необходимо выбрать два файла!")