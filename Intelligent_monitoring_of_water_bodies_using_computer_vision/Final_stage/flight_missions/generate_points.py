def generate_pool_centers_meters(num_cells_x, num_cells_y):
    # Размеры бассейна в см
    pool_width_cm = 200
    pool_height_cm = 300
    
    # Глобальное смещение точки (0:0) в см
    global_origin_x_cm = -325  # -343.33  - поправка
    global_origin_y_cm = 90
    
    # Размер одного квадрата в см
    cell_width_cm = pool_width_cm / num_cells_x
    cell_height_cm = pool_height_cm / num_cells_y
    
    centers_meters = []
    
    # Движение змейкой по колонкам X
    for i in range(num_cells_x):
        center_x_cm = global_origin_x_cm + (i + 0.5) * cell_width_cm
        
        column_y_indices = list(range(num_cells_y))
        
        # Инвертируем Y для нечетных колонок (летим сверху вниз)
        if i % 2 != 0:
            column_y_indices.reverse()
            
        for j in column_y_indices:
            center_y_cm = global_origin_y_cm + (j + 0.5) * cell_height_cm
            
            # Переводим см в метры
            center_x_m = center_x_cm / 100.0
            center_y_m = center_y_cm / 100.0
            
            # Округляем строго до сотых (до см)
            centers_meters.append((round(center_x_m, 1), round(center_y_m, 1)))
            
    return centers_meters

# Пример: сетка 2 на 2
coordinates_in_meters = generate_pool_centers_meters(num_cells_x=3, num_cells_y=4)
print("Координаты центров в метрах (до сотых):")
for c in coordinates_in_meters:
    print(c)
