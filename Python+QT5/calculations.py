from numpy import sqrt,array,arange,unique,concatenate,zeros,linalg,column_stack,ones,abs,cos,sin
from scipy.spatial import Delaunay
from scipy.sparse.linalg import cg

# Получение массива рёбер фигуры
def get_figure_edges(nodes):
    edges = []
    num_nodes = len(nodes)
    for i in range(num_nodes - 1):
        edges.append([nodes[i], nodes[i+1]])
    edges.append([nodes[num_nodes-1], nodes[0]])
    return edges

# Получение кругов представляющих собой заклёпки
def get_circles(circle_centers, radius):
    circles = []
    num_centers = len(circle_centers)
    for i in range(num_centers):
        center = circle_centers[i]
        circles.append((center, radius))
    return circles

# Нахождение пересечений сетки с рёбрами
def line_intersection(line1, line2):
    x1, y1, x2, y2 = line1[0][0], line1[0][1], line1[1][0], line1[1][1]
    x3, y3, x4, y4 = line2[0][0], line2[0][1], line2[1][0], line2[1][1]

    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if den == 0:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den

    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return array([x, y])
    else:
        return None

# Нахождение пересечений сетки с кругами
def line_circle_intersection(line, circle_center, circle_radius):
    x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
    x3, y3 = circle_center

    dx = x2 - x1
    dy = y2 - y1
    a = dx ** 2 + dy ** 2
    b = 2 * (dx * (x1 - x3) + dy * (y1 - y3))
    c = (x1 - x3) ** 2 + (y1 - y3) ** 2 - circle_radius ** 2

    discriminant = b ** 2 - 4 * a * c
    if discriminant < 0:
        return None

    discriminant = sqrt(discriminant)
    t1 = (-b + discriminant) / (2 * a)
    t2 = (-b - discriminant) / (2 * a)

    if 0 <= t1 <= 1:
        x = x1 + t1 * dx
        y = y1 + t1 * dy
        return array([x, y])
    elif 0 <= t2 <= 1:
        x = x1 + t2 * dx
        y = y1 + t2 * dy
        return array([x, y])
    else:
        return None

# Создание сетки    
def create_mesh(X_SIZE, Y_SIZE, figure_edges, circles, SPLIT):
   
    x = arange(0, X_SIZE + SPLIT, SPLIT)
    y = arange(0, Y_SIZE + SPLIT, SPLIT)
    mesh = array([[i, j] for j in y for i in x])

    intersection_nodes = []
    for edge in figure_edges:
        for i in range(len(x) - 1):
            for j in range(len(y) - 1):
                line1 = edge
                line2 = [array([x[i], y[j]]), array([x[i + 1], y[j]])]
                intersection = line_intersection(line1, line2)
                if intersection is not None:
                    intersection_nodes.append(intersection)

                line2 = [array([x[i], y[j]]), array([x[i], y[j + 1]])]
                intersection = line_intersection(line1, line2)
                if intersection is not None:
                    intersection_nodes.append(intersection)

    for circle in circles:
        center, radius = circle
        for i in range(len(x) - 1):
            for j in range(len(y) - 1):
                line1 = [array([x[i], y[j]]), array([x[i + 1], y[j]])]
                intersection1 = line_circle_intersection(line1, center, radius)
                if intersection1 is not None:
                    intersection_nodes.append(intersection1)

                line2 = [array([x[i], y[j]]), array([x[i], y[j + 1]])]
                intersection2 = line_circle_intersection(line2, center, radius)
                if intersection2 is not None:
                    intersection_nodes.append(intersection2)

    intersection_nodes = unique(intersection_nodes, axis=0)
    return array(intersection_nodes), mesh

# Алгоритм проверки принадлежности точки многоугольнику
def point_in_polygon(point, polygon_edges):
    x, y = point
    is_inside = False
    for i in range(len(polygon_edges)):
        edge = polygon_edges[i]
        x1, y1 = edge[0]
        x2, y2 = edge[1]
        if ((y1 < y <= y2) or (y2 < y <= y1)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            is_inside = not is_inside
    return is_inside

# Фильтрация узлов
def filter_nodes(intersection_nodes, mesh, circle_centers, figure_edges, circles):
    edge_points = []
    for edge in figure_edges:
        edge_points.extend(list(edge))
    edge_points = unique(edge_points, axis=0)

    all_nodes = concatenate((intersection_nodes, edge_points))
    all_nodes = unique(all_nodes, axis=0)

    inside_mesh_nodes = []
    for node in mesh:
        if point_in_polygon(node, figure_edges):
            is_inside_circle = False
            for circle in circles:
                center, radius = circle
                if sqrt((node[0] - center[0])**2 + (node[1] - center[1])**2) <= radius:
                    is_inside_circle = True
                    break
            if not is_inside_circle:
                inside_mesh_nodes.append(node)

    circle_boundary_nodes = []
    for circle in circles:
        center, radius = circle
        for node in all_nodes:
            if abs(sqrt((node[0] - center[0])**2 + (node[1] - center[1])**2) - radius) < 1e-5:
                circle_boundary_nodes.append(node)

    all_nodes = concatenate((all_nodes, inside_mesh_nodes, circle_boundary_nodes))
    all_nodes = unique(all_nodes, axis=0)

    # Исключение центров кругов из списка узлов
    all_nodes = array([node for node in all_nodes if not any((node == center).all() for center in circle_centers)])

    return all_nodes

def triangulate(nodes, circles):
    triangles = Delaunay(array(nodes)).simplices

    # Проверка и исключение треугольников, все точки которых находятся на границе одного круга
    valid_triangles = []
    for triangle in triangles:
        points = nodes[triangle]
        is_same_circle_boundary = False
        for circle in circles:
            center, radius = circle
            distances = [sqrt((point[0] - center[0])**2 + (point[1] - center[1])**2) for point in points]
            if all(abs(distance - radius) < 1e-5 for distance in distances):
                is_same_circle_boundary = True
                break
        if not is_same_circle_boundary:
            valid_triangles.append(triangle)

    return array(valid_triangles)

# Определение точек в заклёпках
def getRivets(circles, nodes):
    epsilon = 1e-3
    circles_indices = []

    for circle in circles:
        center, radius = circle
        for i, node in enumerate(nodes):
            x, y = node
            if sqrt((x - center[0])**2 + (y - center[1])**2) <= radius + epsilon:
                circles_indices.append(i)

    return array(circles_indices)

# Определение точек силы
def getForceNodes(point, nodes, side_length):
    x, y = point
    half_side_length = side_length / 2

    points = array([[x + half_side_length, y + half_side_length],
                       [x - half_side_length, y + half_side_length],
                       [x - half_side_length, y - half_side_length],
                       [x + half_side_length, y - half_side_length]])

    edges = get_figure_edges(points)

    area_points_indices = []

    for i, node in enumerate(nodes):
        if point_in_polygon(node, edges):
            area_points_indices.append(i)

    return array(area_points_indices).astype(int)

#Расчёт локальных матриц жёсткости для всех элементов
def calc_local_stiffness_matrices(elems, nodes, E, t):
    Bs = []
    local_stiffness_matrices = []
    num_nodes = len(elems[0])
    for elem in elems:
        k = zeros((2*num_nodes, 2*num_nodes))
        nodes_elem = nodes[list(elem)]
        x, y = nodes_elem[:, 0], nodes_elem[:, 1]

        A = 0.5 * abs(linalg.det(column_stack((ones(num_nodes), x, y))))

        B = zeros((3, 2 * num_nodes))
        for i in range(num_nodes):
            i_plus_1 = (i + 1) % num_nodes
            i_plus_2 = (i + 2) % num_nodes

            B[0, 2 * i] = y[i_plus_1] - y[i_plus_2]
            B[0, 2 * i + 1] = 0
            B[1, 2 * i] = 0
            B[1, 2 * i + 1] = x[i_plus_2] - x[i_plus_1]
            B[2, 2 * i] = x[i_plus_2] - x[i_plus_1]
            B[2, 2 * i + 1] = y[i_plus_1] - y[i_plus_2]

        Bs.append(B)

        k = t * A * B.T @ E @ B
        local_stiffness_matrices.append(k)

    return local_stiffness_matrices, Bs

#Нахождение глобальной матрицы жёсткости
def calc_global_matrix(elems, nodes, E, t):

    local_stiffness_matrices, Bs = calc_local_stiffness_matrices(elems, nodes, E, t)
    num_nodes = len(nodes)
    Global = zeros((num_nodes*2,num_nodes*2))

    for index, elem in enumerate(elems):

        loc = local_stiffness_matrices[index]

        for i in range(3):
            for j in range(3):
                igl = elem[i]
                jgl = elem[j]
                Global[igl*2][jgl*2]     += loc[i*2][j*2] 
                Global[igl*2+1][jgl*2]   += loc[i*2+1][j*2] 
                Global[igl*2][jgl*2+1]   += loc[i*2][j*2+1] 
                Global[igl*2+1][jgl*2+1] += loc[i*2+1][j*2+1]

    return Global, Bs

#Рассчёт смещений
def calc_displacements(global_matrix, F, nodes):
    
    transformed_forces = array([[f[0] * cos(f[1]), f[0] * sin(f[1])] for f in F]).flatten()
    x, info = cg(global_matrix, transformed_forces)
    if info != 0: raise ValueError("Метод сопряженных градиентов не сошелся")
    displacements = x.reshape(len(nodes), 2)

    return nodes + displacements, displacements

# Добавление шарнирно-неподвижных опор
def add_supports(global_matrix, F, node_indices):
    for node_index in node_indices:
        global_matrix[node_index*2, :] = 0
        global_matrix[:, node_index*2] = 0
        global_matrix[node_index*2+1, :] = 0
        global_matrix[:, node_index*2+1] = 0
        global_matrix[node_index*2, node_index*2] = 1
        global_matrix[node_index*2+1, node_index*2+1] = 1
        F[node_index] = [0,0]
            
    return global_matrix, F

# Рассчет напряжений и деформаций для каждого элемента
def calc_stresses_and_strains(elems, E, Bs, displacements):
    stresses = []
    strains = []
    equivalent_stresses = []
    equivalent_strains = []

    for i, elem in enumerate(elems):
        epsilon = Bs[i] @ displacements[elem].flatten()
        sigma = E @ epsilon

        epsilon_eq = (sqrt(2) / 3) * sqrt(epsilon[0] ** 2 + epsilon[1] ** 2 + 1.5 * epsilon[2] ** 2)
        sigma_eq = (1 / sqrt(2)) * sqrt(sigma[0] ** 2 + sigma[1] ** 2 + 6 * sigma[2] ** 2)

        strains.append(epsilon)
        stresses.append(sigma)
        equivalent_strains.append(epsilon_eq)
        equivalent_stresses.append(sigma_eq)

    return array(stresses), array(strains), array(equivalent_stresses), array(equivalent_strains)