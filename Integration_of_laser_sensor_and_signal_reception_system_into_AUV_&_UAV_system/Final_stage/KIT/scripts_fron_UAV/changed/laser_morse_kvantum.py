#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
import time
from user.library import DroneLibrary


MORSE_CODE_CYRILLIC = {
    'а': '.-',    'б': '-...',  'в': '.--',   'г': '--.',   'д': '-..',
    'е': '.',     'ж': '...-',  'з': '--..',  'и': '..',    'й': '.---',
    'к': '-.-',   'л': '.-..',  'м': '--',    'н': '-.',    'о': '---',
    'п': '.--.',  'р': '.-.',   'с': '...',   'т': '-',     'у': '..-',
    'ф': '..-.',  'х': '....',  'ц': '-.-.',  'ч': '---.',  'ш': '----',
    'щ': '--.-',  'ъ': '--.--', 'ы': '-.--',  'ь': '-..-',  'э': '..-..',
    'ю': '..--',  'я': '.-.-',  ' ': '/'
}

WORD = 'квантум'
DOT_DURATION = 0.2
DASH_DURATION = 0.6
SYMBOL_GAP = 0.2
LETTER_GAP = 0.6
WORD_GAP = 1.4


def encode_to_morse(text):
    morse = []
    for char in text.lower():
        if char in MORSE_CODE_CYRILLIC:
            morse.append(MORSE_CODE_CYRILLIC[char])
        else:
            rospy.logwarn(f'Unknown character: {char}')
    return ' '.join(morse)


def send_morse(drone, morse_string):
    for symbol in morse_string:
        if symbol == '.':
            drone.set_laser(1)
            time.sleep(DOT_DURATION)
            drone.set_laser(0)
            time.sleep(SYMBOL_GAP)
        elif symbol == '-':
            drone.set_laser(1)
            time.sleep(DASH_DURATION)
            drone.set_laser(0)
            time.sleep(SYMBOL_GAP)
        elif symbol == ' ':
            time.sleep(LETTER_GAP - SYMBOL_GAP)
        elif symbol == '/':
            time.sleep(WORD_GAP - LETTER_GAP)


def main():
    drone = DroneLibrary()
    drone.start()

    try:
        rospy.loginfo('Turning laser off')
        drone.set_laser(0)
        time.sleep(0.5)

        morse = encode_to_morse(WORD)
        rospy.loginfo(f'Transmitting "{WORD}" in Morse: {morse}')

        send_morse(drone, morse)

        rospy.loginfo('Transmission complete')

        drone.set_offline_mode()
        drone.stop()

    except Exception as e:
        rospy.logerr(f'Error: {e}')
        drone.stop()
        raise


if __name__ == '__main__':
    main()