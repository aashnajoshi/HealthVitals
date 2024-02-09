import serial
import time
import RPi.GPIO as GPIO
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from max30100 import MAX30100 as mx30

I2C_ADDR = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16
TRIG_PIN = 23
ECHO_PIN = 24

LM35_PIN = 18
BUZZER_PIN = 8

lcd = I2cLcd(1, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)
ser_gsm = serial.Serial(
    "/dev/serial0", 9600, timeout=1
)  # GSM module (replace correct port)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)


def beep():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)


def measure_height():
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    pulse_start = time.time()
    pulse_end = time.time()
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
    pulse_duration = pulse_end - pulse_start

    # height = pulse_duration * 0.343  # Speed of sound in cm/s
    height = pulse_duration * (34300 / 2)
    print(height)
    beep()
    return height


def measure_weight():
    beep()
    return 0


def read_pulse_oximeter():
    mx30.enable_spo2()
    mx30.enable_leds()

    pulse_threshold = 80  # bpm
    o2_threshold = 95  # %

    while True:
        mx30.read_sensor()
        stress_level(pulse_threshold, o2_threshold)
        print("Pulse Rate: {} bpm".format(mx30.ir))
        print("Oxygen Saturation: {}%".format(mx30.red))
        print("Stress Level: {}".format(stress_level))
        time.sleep(1)


def stress_level(pulse_threshold, o2_threshold):
    if mx30.ir <= pulse_threshold and mx30.red >= o2_threshold:
        stress_level = "Normal"
    elif mx30.ir > pulse_threshold and mx30.red < o2_threshold:
        stress_level = "High"
    else:
        stress_level = "Moderate"


def measure_temperature():
    # LM35 sensor returns analog voltage proportional to temperature
    GPIO.setup(LM35_PIN, GPIO.IN)
    analog_value = GPIO.input(LM35_PIN)
    temperature = (analog_value / 1024.0) * 3300 / 10  # LM35 scaling formula
    beep()
    return temperature


def send_sms(phone_number, message):
    ser = ser_gsm
    ser.write(b'AT+CPIN="YOUR_PIN"\r\n')
    ser.write(b"AT+CMGF=1\r\n")
    time.sleep(1)
    ser.write(b'AT+CMGS="' + phone_number.encode() + b'"\r\n')
    time.sleep(1)
    ser.write(message.encode() + b"\x1A")
    time.sleep(1)
    ser.close()


def collect_api(phone_number, height, weight, pulse, o2, temperature):
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    SERVICE_ACCOUNT_FILE = "keyams.json"
    creds = None
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    # The ID and range of a sample spreadsheet.
    SAMPLE_SPREADSHEET_ID = "1BUcmZ3LW3yrNbD0ooPvdXrh0FFD7nu6gFjp1OQ_RPqU"
    SAMPLE_RANGE_NAME = "smsapi!A2:E"
    service = build("sheets", "v4", credentials=creds)
    # Call for Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])
    phone_number = "{0}".format(phone_number)
    height = "{0}".format(height)
    temperature = "{0}".format(temperature)

    api_sms = [phone_number, height, weight, pulse, o2, temperature]
    print(api_sms)
    sms_values = []
    sms_values.append(api_sms)
    print(sms_values)

    request = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=SAMPLE_SPREADSHEET_ID,
            range="Sheet2!A3",
            valueInputOption="USER_ENTERED",
            body={"values": sms_values},
        )
        .execute()
    )


def collect_and_send_sms(phone_number):
    phone_number = phone_number
    height = measure_height()
    weight = measure_weight()
    bmi = weight / ((height / 100) ** 2)
    temperature = measure_temperature()
    pulse = read_pulse_oximeter()
    time.sleep(1)
    height = 200 - height
    print(height)
    print(temperature)

    sms_message = f"We appreciate you taking the time to consider your health. Your report:\n Height: {height} cm\nWeight: {weight} kg\nBMI: {bmi:.2f}\nPulse: {pulse.heart_rate} bpm\nOxygen Level: {pulse.spo2}%cm\nTemperature: {temperature:.2f} °C"

    send_sms(phone_number, sms_message)
    beep()
    collect_api(phone_number, height, weight, pulse.heart_rate, pulse.spo2, temperature)
    beep()
    lcd.clear()


while True:
    lcd.putstr("Enter Number: ")
    phone_number = input("Enter your 10-digit mobile number (or 'exit' to end):")
    lcd.clear()

    if phone_number.lower() == "exit":
        break
    if len(phone_number) == 10 and phone_number.isdigit():
        print("Thank you! You can now proceed inside.")
        lcd.putstr(phone_number + "      You May Proceed")
        collect_and_send_sms(phone_number)
        print("Thank you! Your report is ready and is sent to your phone number.")

    else:
        lcd.clear()
        lcd.putstr("Invalid Number")
        print("Invalid phone number. Please enter a 10-digit numeric phone number.")
        time.sleep(1.5)
        lcd.clear()

GPIO.cleanup()
