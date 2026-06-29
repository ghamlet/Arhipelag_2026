from datetime import datetime, timedelta
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# Полный набор данных с возрастами и количеством человек из вашего файла
raw_data = [
    {
        "name": "Воздушное противостояние",
        "dates": ["24.07.26", "25.07.26", "26.07.26"],
        "age": "14+", "team": "2-4 чел"
    },
    {
        "name": "Взаимное позиционирование в рое: «Змейка»",
        "dates": ["24.07.26", "25.07.26", "26.07.26"],
        "age": "16+", "team": "4-6 чел"
    },
    {
        "name": "Инспекция солнечной фермы",
        "dates": ["24.07.26", "25.07.26", "26.07.26"],
        "age": "14+", "team": "3-4 чел"
    },
    {
        "name": "Интеллектуальный мониторинг водных объектов",
        "dates": ["24.07.26", "25.07.26", "26.07.26", "27.07.26"],
        "age": "14+", "team": "2-4 чел"
    },
    {
        "name": "Аддитивная фабрика",
        "dates": ["24.07.26", "25.07.26", "26.07.26", "27.07.26", "28.07.26", "29.07.26", "30.07.26"],
        "age": "14+", "team": "2-4 чел"
    },
    {
        "name": "Кибериммунная автономность",
        "dates": ["24.07.26", "25.07.26", "26.07.26", "27.07.26", "28.07.26", "29.07.26", "30.07.26"],
        "age": "18+", "team": "2-5 чел"
    },
    {
        "name": "Мультисредное взаимодействие: «Дрон-дартс»",
        "dates": ["27.07.26", "28.07.26", "29.07.26"],
        "age": "14+", "team": "3-4 чел"
    },
    {
        "name": "Пожарная безопасность в лесных зонах",
        "dates": ["27.07.26", "28.07.26", "29.07.26"],
        "age": "14+", "team": "1-4 чел"
    },
    {
        "name": "Рой дронов-художников: ИИ агент",
        "dates": ["27.07.26", "28.07.26", "29.07.26"],
        "age": "14+", "team": "3-6 чел"
    },
    {
        "name": "Город дронов: социум ИИ агентов",
        "dates": ["27.07.26", "28.07.26", "29.07.26", "30.07.26"],
        "age": "14+", "team": "4-6 чел"
    },
    {
        "name": "Интеграция лазерного датчика: АНПА + БПЛА",
        "dates": ["28.07.26", "29.07.26", "30.07.26"],
        "age": "14+", "team": "4-6 чел"
    },
    {
        "name": "Ход дрона: шахматные сражения роёв",
        "dates": ["30.07.26", "31.07.26", "01.08.26", "02.08.26"],
        "age": "14+", "team": "4-10 чел"
    },
    {
        "name": "Бенчмарк. Роевой полёт в лесу",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "16+", "team": "3-6 чел"
    },
    {
        "name": "II Конкурс 'Технологии потока'",
        "dates": ["31.07.26", "01.08.26"],
        "age": "14+", "team": "1-3 чел"
    },
    {
        "name": "Компьютерное зрение в навигации БРС",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "14+", "team": "2-4 чел"
    },
    {
        "name": "Лазер-дрон: Битва интеллектов",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "14+", "team": "3-4 чел"
    },
    {
        "name": "Воздушный дозор",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "н/д", "team": "н/д"
    },
    {
        "name": "Энергоэстафета",
        "dates": ["30.07.26", "31.07.26", "01.08.26", "02.08.26"],
        "age": "н/д", "team": "н/д"
    },
    {
        "name": "Аэродуэль",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "н/д", "team": "н/д"
    },
    {
        "name": "3D-реинжиниринг беспилотных систем",
        "dates": ["31.07.26", "01.08.26", "02.08.26"],
        "age": "18+", "team": "1-2 чел"
    },
]

# Цветовая схема в зависимости от возраста участников
COLOR_MAP = {
    "14+": "#5bc0de",  # Голубой
    "16+": "#5cb85c",  # Зеленый
    "18+": "#f0ad4e",  # Оранжевый
    "н/д": "#777777"   # Серый (если нет данных)
}

parsed_events = []
for item in raw_data:
    start = datetime.strptime(item["dates"][0], "%d.%m.%y")
    end = datetime.strptime(item["dates"][-1], "%d.%m.%y") + timedelta(days=1)
    
    # Формируем красивое название оси Y, куда склеиваем имя, возраст и команду
    display_name = f"{item['name']}   [{item['age']}]  ({item['team']})"
    
    parsed_events.append({
        "Task": display_name,
        "Start": start,
        "End": end,
        "Age": item["age"]
    })

df = pd.DataFrame(parsed_events)
# Сортируем по дате старта, чтобы график шел красивой лесенкой во времени
df = df.sort_values(by="Start", ascending=False).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(15, 10))

min_date = df["Start"].min()
max_date = df["End"].max()

total_days = (max_date - min_date).days
date_range = [min_date + timedelta(days=x) for x in range(total_days + 1)]

for i, row in df.iterrows():
    duration = (row["End"] - row["Start"]).days
    bar_color = COLOR_MAP.get(row["Age"], "#777777")

    # Рисуем бары с цветом возрастной категории
    ax.barh(
        row["Task"],
        duration,
        left=row["Start"],
        align="center",
        color=bar_color,
        edgecolor="black",
        linewidth=0.6,
        alpha=0.85,
    )

# Настройка осей и сетки календаря
ax.xaxis_date()
ax.set_xticks(date_range)
ax.grid(axis="x", linestyle="--", alpha=0.5, color="gray")

# Сдвигаем подписи дат на середину ячеек
midday_ticks = [d + timedelta(hours=12) for d in date_range[:-1]]
ax.set_xticks(midday_ticks, minor=True)

ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d.%m"))
ax.xaxis.set_major_formatter(mticker.NullFormatter())

ax.tick_params(axis="x", which="major", bottom=False)
ax.tick_params(axis="x", which="minor", labelsize=10)
plt.yticks(fontsize=10, fontname="DejaVu Sans") # Используем стандартный шрифт для поддержки спецсимволов

# Добавляем кастомную легенду цветов
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=COLOR_MAP["14+"], edgecolor="black", label="Категория 14+"),
    Patch(facecolor=COLOR_MAP["16+"], edgecolor="black", label="Категория 16+"),
    Patch(facecolor=COLOR_MAP["18+"], edgecolor="black", label="Категория 18+"),
    Patch(facecolor=COLOR_MAP["н/д"], edgecolor="black", label="Возраст не указан")
]
ax.legend(handles=legend_elements, loc="upper right", fontsize=10, framealpha=0.9)

plt.title(
    "Диаграмма Ганта: Сроки соревнований Архипелаг 2026\n[Возраст] и (Размер команды)",
    fontsize=14,
    pad=20,
    fontweight="bold",
)
plt.xlabel("Дни проведения (Июль - Август 2026)", fontsize=12, labelpad=10)

plt.xlim(min_date, max_date)
plt.tight_layout()

plt.savefig("gantt_archipelag_advanced.png", dpi=300)
print("✨ Расширенная диаграмма сохранена в 'gantt_archipelag_advanced.png'")
plt.show()
