import datetime
import os
import re
import time

import assemblyai as aai
import pyodbc
import pyttsx3
import scipy.io.wavfile as wav
import sounddevice as sd
import speech_recognition as sr

engine = pyttsx3.init()


# Функция для приемки заказов на ПВЗ
def receive_order_at_pvz():
    # Подключение к базе данных
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=DESKTOP-NOO2N4A;DATABASE=PVZ_CHEMP')

    # Создание курсора
    cursor = conn.cursor()

    # Запрос таблицы Orders для получения ожидающих заказов
    query = "SELECT OrderNumber, ClientPhoneNumber FROM Orders WHERE Status = 'Pending'"
    cursor.execute(query)

    # Получение всех ожидающих заказов
    pending_orders = cursor.fetchall()

    if not pending_orders:
        print("Нет ожидающих заказов.")
        return

    # Вывод ожидающих заказов
    print("Ожидающие заказы:")
    for order in pending_orders:
        print(f"Номер заказа: {order.OrderNumber}, Телефон клиента: {order.ClientPhoneNumber}")

    # Получение от пользователя номера заказа для приемки
    order_number_to_receive = input("Пожалуйста, введите номер заказа для приемки: ")

    # Обновление статуса полученного заказа в базе данных
    update_query = f"UPDATE Orders SET Status = 'Received' WHERE OrderNumber = '{order_number_to_receive}'"
    cursor.execute(update_query)
    conn.commit()

    print(f"Заказ {order_number_to_receive} успешно принят.")

    # Закрытие курсора и соединения с базой данных
    cursor.close()
    conn.close()


# Функция для транскрибации аудио с помощью AssemblyAI
def transcribe_audio(audio_file):
    aai.settings.api_key = "d2010a481d314166949f17afb6cd9710"
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    return transcript.text


def find_order_by_phone(phone_number):
    # Подключение к базе данных
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=DESKTOP-NOO2N4A;DATABASE=PVZ_CHEMP')

    # Создание курсора
    cursor = conn.cursor()

    # Запрос таблицы Orders
    query = f"SELECT OrderNumber, RackID, CellID FROM Orders WHERE ClientPhoneNumber = '{phone_number}'"
    cursor.execute(query)

    # Получение результата
    rows = cursor.fetchall()

    if not rows:
        return "Заказы не найдены."

    orders = []
    for row in rows:
        order_number, rack_id, cell_id = row
        orders.append({
            "order_number": order_number,
            "rack_id": rack_id,
            "cell_id": cell_id
        })

    if len(orders) == 1:
        print("Найден 1 заказ.")
        order_data = f"Стеллаж: {orders[0]['rack_id']}, Ячейка: {orders[0]['cell_id']}"
        speak_order_data(order_data)
        # issue_order()
        with open('order_data.txt', 'w') as file:
            file.write(
                f"OrderNumber: {orders[0]['order_number']}, RackID: {orders[0]['rack_id']}, CellID: {orders[0]['cell_id']}")
        return "\n".join(
            [
                f"Номер заказа: {order['order_number']},  № стеллажа: {order['rack_id']}, № ячейки: {order['cell_id']}"
                for
                order in orders])
    else:
        print(f"Найдено {len(orders)} заказов.")
        return "\n".join(
            [
                f"Номер заказа: {order['order_number']},  № стеллажа: {order['rack_id']}, № ячейки: {order['cell_id']}"
                for
                order in orders])

    # Закрытие курсора и соединения с базой данных
    cursor.close()
    conn.close()


def find_order_by_phone_user(phone_number):
    # Подключение к базе данных
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=DESKTOP-NOO2N4A;DATABASE=PVZ_CHEMP')

    # Создание курсора
    cursor = conn.cursor()

    # Запрос таблицы Orders
    query = f"SELECT OrderNumber, ClientPhoneNumber, Status FROM Orders WHERE ClientPhoneNumber = '{phone_number}' AND Status = 'Готов к выдаче'"
    cursor.execute(query)

    # Получение результата
    rows = cursor.fetchall()

    if not rows:
        return "Заказы не найдены."

    orders_info = []
    for row in rows:
        order_number, client_phone_number, status = row
        order_info = {
            "order_number": order_number,
            "client_phone_number": client_phone_number,
            "status": status
        }
        orders_info.append(order_info)

    if len(orders_info) == 1:
        order = orders_info[0]
        order_data = f"Номер заказа: {order['order_number']}, Номер телефона: 8{order['client_phone_number']}, Статус: {order['status']}"
        speak_order_data(order_data)
        # issue_order()
        with open('order_data.txt', 'w') as file:
            file.write(
                f"OrderNumber: {order['order_number']}")
        return order_data
    else:
        result = "\n".join([
            f"Номер заказа: {order['order_number']}, Номер телефона: {order['client_phone_number']}, Статус: {order['status']}"
            for order in orders_info])
        print(f"Найдено {len(orders_info)} заказов.")
        return result

    # Закрытие курсора и соединения с базой данных
    cursor.close()
    conn.close()


# Функция для выдачи заказа
def issue_order():
    recognizer = sr.Recognizer()

    # Получение аудио с микрофона
    duration = 3  # Длительность записи в секундах
    fs = 44100  # Частота дискретизации
    print("Говорите, чтобы подтвердить готовность к выдаче заказа:")
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    for i in range(duration, 0, -1):
        print(f"Запись завершится через {i} секунд(ы)...")
        time.sleep(1)
    sd.wait()  # Ожидание завершения записи
    wav.write('command.wav', fs, myrecording)  # Сохранение записи в файл
    try:
        voice_input = recognizer.recognize_assemblyai('command.wav', api_token="d2010a481d314166949f17afb6cd9710")
        print("Вы сказали:", voice_input)
        if ("да" or "Yes.") in voice_input.lower():
            print("Сотрудник ПВЗ: Да, заказ готов к выдаче.")
            # Добавьте здесь стандартную процедуру выдачи заказа и формирование документов
        else:
            print("Сотрудник ПВЗ: Отмена выдачи заказа.")
    except sr.UnknownValueError:
        print("Сотрудник ПВЗ: Извините, не удалось распознать ваш ответ.")
    except sr.RequestError:
        print("Сотрудник ПВЗ: Не удалось получить ответ от сервиса распознавания речи.")


def speak_order_data(order_data):
    engine = pyttsx3.init()
    engine.say(order_data)
    engine.runAndWait()


# Функция для обработки других функций с голосовым управлением
def other_functions():
    # Реализация других функций по необходимости
    # Замените этот код своей реализацией
    print("Другие функции успешно обработаны.")


def read_text_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        text = file.read()
    return text


def format_phone_number(phone_number):
    # Удаление всех нецифровых символов из строки
    formatted_number = re.sub(r'\D', '', phone_number)

    # Удаление префикса: либо цифра 8 в начале, либо +7
    if formatted_number.startswith('8'):
        formatted_number = formatted_number[1:]
    elif formatted_number.startswith('+7'):
        formatted_number = formatted_number[2:]

    # Проверка, что номер содержит ровно 10 цифр
    if len(formatted_number) != 10:
        print("Некорректный номер телефона. Пожалуйста, введите 10 цифр.")
        return None

    return formatted_number


def get_highest_cell_id(conn):
    cursor = conn.cursor()
    query = "SELECT MAX(CellID) FROM Orders"
    cursor.execute(query)
    highest_cell_id = cursor.fetchone()[0]
    cursor.close()
    return highest_cell_id if highest_cell_id else 0


def add_order(order_number, arrived_date, status, client_phone_number, rack_id, cell_id):
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=DESKTOP-NOO2N4A;DATABASE=PVZ_CHEMP')
    cursor = conn.cursor()

    insert_query = f"""
        INSERT INTO Orders (OrderNumber, ArrivedDate, Status, ClientPhoneNumber, RackID, CellID)
        VALUES ('{order_number}', '{arrived_date}', '{status}', '{client_phone_number}', {rack_id}, {cell_id})
    """
    cursor.execute(insert_query)
    conn.commit()

    cursor.close()
    conn.close()


def find_order_by_order_number(order_number):
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=DESKTOP-NOO2N4A;DATABASE=PVZ_CHEMP')
    cursor = conn.cursor()

    query = (f"SELECT OrderNumber, ArrivedDate, Status, ClientPhoneNumber, RackID, CellID FROM Orders WHERE "
             f"OrderNumber = '{order_number}'")
    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print("Такого номера заказа не найдено.")
        print("Хотите зарегистрировать новый заказ?")
        print("Скажите \"Yes\" если хотите, либо \"No\", если нет.")
        record_txt = recording()
        if "Yes." in record_txt:
            print("Хорошо, начнем процесс регистрации нового заказа.")
            order_number = order_number
            print(f"Номер заказа: {order_number}")
            arrived_date = datetime.date.today().strftime('%Y-%m-%d')
            print(f"Дата: {arrived_date}")
            status = input("Введите статус: ")
            client_phone_number = input("Введите номер телефона клиента: ")
            rack_id = int(input("Введите номер стеллажа: "))

            # Получаем самый высокий номер ячейки в стеллажах
            highest_cell_id = get_highest_cell_id(conn)

            # Предлагаем пользователю ячейку на основе самого высокого номера ячейки
            suggested_cell_id = highest_cell_id + 1
            print(f"Предлагаемая ячейка: {suggested_cell_id}")

            print("Хотите использовать предложенную ячейку?")
            print("Скажите \"Yes\" если да, либо \"No\", если нет.")
            record_txt = recording()

            if "Yes." in record_txt:
                cell_id = suggested_cell_id
            else:
                cell_id = int(input("Введите номер ячейки: "))

            add_order(order_number, arrived_date, status, client_phone_number, rack_id, cell_id)
            print("Заказ успешно зарегистрирован.")
        elif "No." in record_txt:
            print("Понял, как скажешь.")
        return

    orders = []
    for row in rows:
        order_number, date, status, client_phone_number, rack_id, cell_id = row
        orders.append({
            "order_number": order_number,
            "date": date,
            "status": status,
            "client_phone_number": client_phone_number,
            "rack_id": rack_id,
            "cell_id": cell_id
        })

    if len(orders) == 1:
        print("Найден 1 заказ.")
        order_data = f"Номер заказа: {orders[0]['order_number']}, Дата прибытия: {orders[0]['date']}, Статус: {orders[0]['status']}, " \
                     f"Телефон клиента: {orders[0]['client_phone_number']}, " \
                     f"Стеллаж: {orders[0]['rack_id']}, Ячейка: {orders[0]['cell_id']}"
        speak_order_data(order_data)
        with open('order_data.txt', 'w') as file:
            file.write(
                f"OrderNumber: {orders[0]['order_number']}, RackID: {orders[0]['rack_id']}, CellID: {orders[0]['cell_id']}")
        return order_data
    else:
        print(f"Найдено {len(orders)} заказов.")
        return "\n".join(
            [
                f"Номер заказа: {order['order_number']}, Дата прибытия: {order['date']}, "
                f"Статус: {order['status']}, Телефон клиента: {order['client_phone_number']}, "
                f"№ стеллажа: {order['rack_id']}, № ячейки: {order['cell_id']}"
                for
                order in orders])

    cursor.close()
    conn.close()


def recording():
    duration = 5  # Длительность записи в секундах
    fs = 44100  # Частота дискретизации
    print("Произнесите вашу команду...")
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    for i in range(duration, 0, -1):
        print(f"Запись завершится через {i} секунд(ы)...")
        time.sleep(1)
    sd.wait()  # Ожидание завершения записи
    wav.write('command.wav', fs, myrecording)  # Сохранение записи в файл
    return transcribe_audio('command.wav')  # Транскрибация аудио


def format_order_number(order_number):
    # Удаление пробелов и преобразование всех символов в верхний регистр
    formatted_number = order_number.strip().upper().replace(" ", "")
    return formatted_number


# Основная функция для записи аудио, транскрибации и выполнения команд
def main():
    while True:
        print("Ожидание команды...")
        while not os.path.exists('command.txt'):
            time.sleep(1)

        print("Выполнение команды. Подождите...")

        command_text = read_text_from_file('command.txt')
        phone_number = read_text_from_file('phoneNumber.txt')
        order_number = read_text_from_file('OrderNumber.txt')

        # print("Форматированный номер телефона:", formatted_number)

        if "Find order." in command_text:
            formatted_number = format_phone_number(phone_number)
            result = find_order_by_phone(formatted_number)
            if result is not None:
                print(result)
        elif "Find order user." in command_text:
            formatted_number = format_phone_number(phone_number)
            result = find_order_by_phone_user(formatted_number)
            if result is not None:
                print(result)
        elif "Issue order." in command_text:
            issue_order()
        elif "Receive order." in command_text:
            receive_order_at_pvz()
        elif "Search Order Number." in command_text:
            formatted_order_number = format_order_number(order_number)
            print("Форматированный номер заказа:", formatted_order_number)
            result = find_order_by_order_number(formatted_order_number)
            if result is not None:
                print(result)
        else:
            other_functions()

        os.remove('command.txt')  # Удаление файла после выполнения команды


if __name__ == "__main__":
    main()
