# -*- coding: utf-8 -*-

"""Файл служит для определения точности вашего алгоритма.
   Не редактируёте его!!!
   Для получения оценки точности, запустите файл на исполнение.
"""

import eval as submission
import cv2
import pandas as pd

def check_answer(expected, user_answer):
    return expected == user_answer


def main():
    csv_file = "annotations.csv"
    data = pd.read_csv(csv_file, sep=';')
    data = data.sample(frac=1)

    correct = 0
    for i, row in enumerate(data.itertuples()):
        _, image_filename, right_answer = row

        right_answer = eval(right_answer)

        image = cv2.imread(image_filename)

        user_answer = submission.find_the_shortest_way(image)

        if check_answer(right_answer, user_answer):
            correct += 1
            print(image_filename, '- верно')
        else:
            print(image_filename, '- неверно')

    total_object = len(data.index)
    print(f"Из {total_object} изображений верный ответ дан для {correct}")

    score = round(correct / total_object, 2)
    print(f"Точность: {score}")


if __name__ == '__main__':
    main()
