import rapidjson
from PyQt5.QtWidgets import QMessageBox, QDialog
from ui.materials_ui import Ui_MaterialsWindow

# Класс модального окна для редактирования материалов
class MaterialsWindow(QDialog, Ui_MaterialsWindow):
    def __init__(self, parent=None):
        super(MaterialsWindow, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.selected_material_id = None
        self.updateMaterialList()
        self.saveButton.clicked.connect(self.save_material)
        self.removeButton.clicked.connect(self.remove_material)
        self.closeButton.clicked.connect(self.close)
        self.materialsList.itemClicked.connect(self.display_material_data)

    def close(self):
        with open('materials.json', 'wb') as f: rapidjson.dump(self.parent.MATERIALS, f, ensure_ascii=False, indent=4)
        self.accept()

    def clear_fields(self):
        self.selected_material_id = None
        self.nameEdit.clear()
        self.poissonEdit.clear()
        self.youngEdit.clear()

    def updateMaterialList(self):
        self.materialsList.clear()
        self.materialsList.addItems([material["name"] for material in self.parent.MATERIALS.values()])
        self.clear_fields()

    def display_material_data(self, item):
        self.selected_material_id = list(self.parent.MATERIALS.keys())[self.materialsList.row(item)]
        material = self.parent.MATERIALS[self.selected_material_id]
        self.nameEdit.setText(material["name"])
        self.poissonEdit.setText(str(material["poisson"]))
        self.youngEdit.setText(str(material["young"]))

    def save_material(self):
        name = self.nameEdit.text()
        fields = [self.nameEdit.text(), self.poissonEdit.text(), self.youngEdit.text()]

        if any(input_value == '' for input_value in fields):
            QMessageBox.warning(self, 'ОШИБКА', 'Заполните все поля!')
            return

        validation_results = [self.parent.validate(field, name, *limits) for field, name, limits in
            zip(fields[1:], ['Коэффициент Пуассона', 'Модуль Юнга'], [(0, 0.5), (0, None)])]
        validation_errors = [message for success, message in validation_results if not success]

        if validation_errors:
            QMessageBox.warning(self, 'ОШИБКА', f'Нарушены следующие условия: {", ".join(validation_errors)}!')
            return

        if self.selected_material_id:
            self.parent.MATERIALS[self.selected_material_id]= {"name": name, "poisson": validation_results[0][1], "young": validation_results[1][1]}
            self.materialsList.currentItem().setText(name)
        else:
            new_id = max(map(int, self.parent.MATERIALS.keys())) + 1
            self.parent.MATERIALS[new_id] = {"name": name, "poisson": validation_results[0][1], "young": validation_results[1][1]}
            self.materialsList.addItem(name)
   
        self.updateMaterialList()
        self.parent.updateDropDownList()

    def remove_material(self):
        if len(self.parent.MATERIALS)==1:
            QMessageBox.warning(self, 'ПРЕДУПРЕЖДЕНИЕ', 'Список материалов не может быть пустым!')
            self.updateMaterialList()
            return
        if self.selected_material_id is not None:
            del self.parent.MATERIALS[self.selected_material_id]
            self.updateMaterialList()
            self.parent.updateDropDownList()