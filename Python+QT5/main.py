import rapidjson
from sys import argv, exit
from math import radians
from numpy import array
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from ui.main_ui import Ui_MainWindow
from materials import MaterialsWindow
from ansys import AnsysWindow
from calculations import *
from graphics import *

# Размеры
a, b, c, d, e, f, g = 10.0, 8.0, 6.0, 5.5, 1.0, 1.5, 1.5
h = b + c
i = b - 2 * f
j = a - 2 * g
      
edge_nodes = array([[0, 0],[0, a],[h, a],[h, a - d],[b, 0]]) # Длины рёбер фигуры
circle_centers = array([[f, a - g],[b - f, a - g],[f, g],[b - f, g]]) # Центры окружностей
figure_edges = get_figure_edges(edge_nodes) # Рёбра фигуры
circles = get_circles(circle_centers, e) # Окружности

# Класс основного окна приложения
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        with open('materials.json', 'rb') as f: self.MATERIALS = rapidjson.load(f)
        self.STEPS = [0.25,0.5,1]
        self.ansys_nodes = None
        self.ansys_elems = None
        self.ansysDataLoaded = False
        self.widgets_adjust()
        self.setupUiValues()
        self.execute()

    # Настройка виджетов и инициализация значений полей ввода
    def widgets_adjust(self):
        self.canvas1 = self.canvas2 = self.canvas3 = None
        self.materialsButton.clicked.connect(self.openMaterialWindow)
        self.execButton.clicked.connect(self.execute)
        self.ansysButton.clicked.connect(self.openAnsysWindow)
        self.materialSelect.currentIndexChanged.connect(self.setMaterial)
        self.updateDropDownList()
        self.meshStepSelect.valueChanged.connect(self.stepSelected)
        self.ansysCheck.clicked.connect(self.useAnsys)

    def setupUiValues(self):
        self.ANSYS = False
        self.thicknessInput.setText('1')
        self.forceInput.setText('1e10')
        self.angleInput.setText('45')
        self.meshStepSelect.setRange(0, len(self.STEPS) - 1)
        self.meshStepSelect.setSingleStep(1)
        self.meshStepSelect.setSliderPosition(round((len(self.STEPS) - 1) / 2))
    
    # Методы для работы c модальными окнами
    def openAnsysWindow(self): AnsysWindow(self).exec_()
    def useAnsys(self, state):
        if self.ansysDataLoaded: self.ANSYS = bool(state)
        else:
            QMessageBox.warning(self, "ПРЕДУПРЕЖДЕНИЕ", "Необходимо сначала загрузить файлы Ansys!")
            self.ansysCheck.setChecked(False)

    def openMaterialWindow(self): MaterialsWindow(self).exec_()
    def updateDropDownList(self):
        self.materialSelect.clear()
        self.materialSelect.addItems([material["name"] for _, material in self.MATERIALS.items()])
    def setMaterial(self):
        material_id = list(self.MATERIALS.keys())[self.materialSelect.currentIndex()]
        if material_id is not None:
            material = self.MATERIALS[material_id]
            self.mu = material["poisson"] # коэффициент Пуассона
            self._E = material["young"] # модуль Юнга
    
    # Метод для получения заклёпок и точек приложения сил
    def get_rivets_and_force_nodes(self,circles,nodes,x,y,size):
        return getRivets(circles,nodes),getForceNodes((x, y), nodes, size)

    # Отслеживание выбранных материала и шага сетки, получение вектора сил
    def stepSelected(self,value): 
        self.STEP = float(self.STEPS[value]) # Шаг сетки
        self.step_box.setText(str(self.STEP))

    def setForces(self,f_value,f_angle,f_nodes,nodes): # Вектор сил
        return array([[f_value, radians(f_angle)] if index in f_nodes else [0, 0] for index in range(len(nodes))])
    
    # Валидация данных
    def validate(self, value, name, min_value=None, max_value=None):
        try:
            float_value = float(value.replace(',', '.'))
        except ValueError:
            return False, f'значение в поле "{name}" должно быть числом'
        if min_value is not None and float_value < min_value:
            return False, f'значение в поле "{name}" не может быть меньше {min_value}'
        if max_value is not None and float_value > max_value:
            return False, f'значение в поле "{name}" не может быть больше {max_value}'
        return True, float_value
        
    # Метод для выполнения необходимых расчётов
    def calculate(self,_E,mu,elems,nodes,t,F,r_nodes):
        E = (_E / (1 - mu**2)) * array([[1, mu, 0], [mu, 1, 0], [0, 0, (1 - mu) / 2]]) # Матрица упругости
        global_matrix, Bs = calc_global_matrix(elems, nodes, E, t) # Расчёт глобальной матрицы жёсткости
        global_matrix, self.F = add_supports(global_matrix, F, r_nodes)  # Добавляем шарнирно-неподвижные опоры
        displaced_nodes, displacements = calc_displacements(global_matrix, F, nodes) # Расчёт смещений
        stresses, strains, stresses_eq, strains_eq = calc_stresses_and_strains(elems, E, Bs, displacements) # Расчет напряжений и деформаций
        return displaced_nodes, stresses, strains, stresses_eq, strains_eq
    
    # Основной метод
    def execute(self):
        fields = [self.thicknessInput.text(), self.forceInput.text(), self.angleInput.text()]

        if any(input_value == '' for input_value in fields):
            QMessageBox.warning(self, 'ОШИБКА', 'Заполните все поля!')
            return

        validation_results = [self.validate(field, name, *limits) for field, name, limits in
            zip(fields, ['Толщина', 'Сила', 'Угол'], [(0, 1), (0, None), (0, 360)])]

        validation_errors = [message for success, message in validation_results if not success]

        if validation_errors:
            QMessageBox.warning(self, 'ОШИБКА', f'Нарушены следующие условия: {", ".join(validation_errors)}!')
            return

        t, f_value, f_angle = [result[1] for result in validation_results] # Толщина, значение силы, угол приложения

        # Точки и элементы фигуры
        if self.ANSYS == True: nodes, elems = self.ansys_nodes, self.ansys_elems
        else:
            nodes = filter_nodes(*create_mesh(h, a, figure_edges, circles, self.STEP), circle_centers, figure_edges, circles)
            elems = triangulate(nodes,circles)

        r_nodes,f_nodes = self.get_rivets_and_force_nodes(circles,nodes,h,a,self.STEP/2) # Точки заклёпок и приложения сил
        Forces = self.setForces(f_value,f_angle,f_nodes,nodes) # Вектор сил
        # Точки после деформации фигуры, напряжения и деформации + эквивалентные значения
        displaced_nodes, stresses, strains, stresses_eq, strains_eq = self.calculate(self._E,self.mu,elems,nodes,t,Forces,r_nodes)
        
        # Инициализация графиков
        fig1, axes1 = initGraph(rows=1,cols=2,top=0.94,bottom=0.094,left=0.052,right=0.988,hspace=0.2,wspace=0.142)
        fig2, axes2 = initGraph(rows=2,cols=3,top=0.908,bottom=0.094,left=0.033,right=0.972,hspace=0.494,wspace=0.178)
        fig3, axes3 = initGraph(rows=1,cols=2,top=0.908,bottom=0.094,left=0.057,right=0.965,hspace=0.2,wspace=0.212)
        # Графики модели, напряжений и деформаций
        drawModel(axes1, elems, nodes, displaced_nodes, Forces, f_nodes, r_nodes)
        drawStrainsStresses(axes2, axes3 ,elems,displaced_nodes,stresses,strains,stresses_eq,strains_eq)
        updateGraphs(fig1, fig2, fig3, self) # Обновление холстов

if __name__ == '__main__':
    app = QApplication(argv)
    main = MainWindow()
    main.show()
    exit(app.exec_())