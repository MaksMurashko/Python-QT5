from numpy import sin,cos,linalg,max
from matplotlib.pyplot import subplots,colorbar,close
from matplotlib.tri import Triangulation
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

# Класс холста Qt для помещения рисунка Matplotlib
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, fig):
        super(MplCanvas, self).__init__(fig)

# Функция для подготовки рисунка с пустыми осями и предварительного их оформления, без задания данных
def initGraph(rows, cols, figSize=None, top=None, bottom=None, left=None, right=None, hspace=None, wspace=None):
    fig, axes = subplots(nrows=rows, ncols=cols, figsize=figSize, facecolor='white',dpi=100)
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right, hspace=hspace, wspace=wspace)
    return fig, axes

# Функция для обновления холстов
def updateGraphs(fig1, fig2 , fig3, self):
    if self.canvas1 and self.canvas2 and self.canvas3:       
            self.companovka_for_mpl1.removeWidget(self.toolbar1)
            self.companovka_for_mpl1.removeWidget(self.canvas1)
            self.toolbar1.deleteLater()
            self.canvas1.deleteLater()
            self.canvas1.hide()
            self.toolbar1.hide()
            self.companovka_for_mpl2.removeWidget(self.toolbar2)
            self.companovka_for_mpl2.removeWidget(self.canvas2)
            self.toolbar2.deleteLater()
            self.canvas2.deleteLater()
            self.canvas2.hide()
            self.toolbar2.hide()
            self.companovka_for_mpl3.removeWidget(self.toolbar3)
            self.companovka_for_mpl3.removeWidget(self.canvas3)
            self.toolbar3.deleteLater()
            self.canvas3.deleteLater()
            self.canvas3.hide()
            self.toolbar3.hide()
            close('all')
        
    self.canvas1 = MplCanvas(fig1)
    self.companovka_for_mpl1.addWidget(self.canvas1)
    self.toolbar1 = NavigationToolbar2QT(self.canvas1, self)
    self.toolbar1.setStyleSheet("background-color: rgb(255,255,255);")
    self.companovka_for_mpl1.addWidget(self.toolbar1)
    self.canvas2 = MplCanvas(fig2)
    self.companovka_for_mpl2.addWidget(self.canvas2)
    self.toolbar2 = NavigationToolbar2QT(self.canvas2, self)
    self.toolbar2.setStyleSheet("background-color: rgb(255,255,255);")
    self.companovka_for_mpl2.addWidget(self.toolbar2)
    self.canvas3 = MplCanvas(fig3)
    self.companovka_for_mpl3.addWidget(self.canvas3)
    self.toolbar3 = NavigationToolbar2QT(self.canvas3, self)
    self.toolbar3.setStyleSheet("background-color: rgb(255,255,255);")
    self.companovka_for_mpl3.addWidget(self.toolbar3)

#Отображение графиков модели
def drawModel(axes, elems, _nodes, displaced_nodes, F, force_points, rivets_nodes):
    titles=['Модель до воздействия сил', 'Модель после воздействия сил']
    max_force = max(linalg.norm(F, axis=1))
    for i, ax in enumerate(axes):
        nodes = _nodes if i == 0 else displaced_nodes

        ax.triplot(nodes[:,0], nodes[:,1], elems, color='#1E90FF')
        ax.scatter(nodes[rivets_nodes, 0], nodes[rivets_nodes, 1], color='#FF4500', marker='o')
        ax.scatter(nodes[force_points, 0], nodes[force_points, 1], color='#8B0000', marker='o')

        for point in force_points:
            magnitude, angle = F[point]
            magnitude = magnitude / max_force
            dx = magnitude * cos(angle)
            dy = magnitude * sin(angle)
            ax.arrow(nodes[point, 0], nodes[point, 1], dx, dy, color='#FF0000', width=0.03)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title(titles[i])
        ax.grid(True)
        ax.axis('equal')

#Оттображение графиков напряжений и деформаций
def drawStrainsStresses(axes, axes_eq, elems, displaced_nodes, stresses, strains, stresses_eq, strains_eq):
    data = {
        "Продольная деформация вдоль оси X": strains[:, 0],
        "Продольная деформация вдоль оси Y": strains[:, 1],
        "Сдвиговая деформация": strains[:, 2],
        "Нормальное напряжение по оси X": stresses[:, 0],
        "Нормальное напряжение по оси Y": stresses[:, 1],
        "Сдвиговое напряжение": stresses[:, 2]
    }
    data_eq = {
        "Эквивалентная деформация": strains_eq,
        "Эквивалентное напряжение": stresses_eq
    }

    colors = ['#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000']
    cmap = LinearSegmentedColormap.from_list('custom_cmap', colors)

    def plot(ax, component_values, component_name):
        triangles = Triangulation(displaced_nodes[:, 0], displaced_nodes[:, 1], triangles=elems)
        mappable = ax.tripcolor(triangles, component_values, cmap=cmap)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title(component_name, pad=20)
        ax.axis('equal')

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="7%", pad=0.2)
        colorbar(mappable, cax=cax)

    for i, (component_name, component_values) in enumerate(data.items()):
        row = i // 3
        col = i % 3
        ax = axes[row, col]
        plot(ax, component_values, component_name)

    for i, (component_name, component_values) in enumerate(data_eq.items()):
        ax_eq = axes_eq[i]
        plot(ax_eq, component_values, component_name)