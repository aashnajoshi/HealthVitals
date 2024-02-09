import RPi.GPIO as GPIO
import time
from RPLCD import CharLCD
from max30100 import MAX30100

# Set up GPIO
ULTRASONIC_TRIGGER_PIN = 23
ULTRASONIC_ECHO_PIN = 24
BUZZER_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(ULTRASONIC_TRIGGER_PIN, GPIO.OUT)
GPIO.setup(ULTRASONIC_ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Initialize LCD
lcd = CharLCD(cols=16, rows=2, pin_rs=37, pin_e=35, pins_data=[33, 31, 29, 23])

# Initialize MAX30100 sensor
mx30 = MAX30100()
mx30.enable_spo2()
mx30.enable_leds()


def measure_distance():
    # Trigger ultrasonic sensor
    GPIO.output(ULTRASONIC_TRIGGER_PIN, True)
    time.sleep(0.00001)
    GPIO.output(ULTRASONIC_TRIGGER_PIN, False)

    # Wait for echo
    pulse_start = time.time()
    pulse_end = time.time()
    while GPIO.input(ULTRASONIC_ECHO_PIN) == 0:
        pulse_start = time.time()
    while GPIO.input(ULTRASONIC_ECHO_PIN) == 1:
        pulse_end = time.time()

    # Calculate distance from time difference
    pulse_duration = pulse_end - pulse_start
    distance_cm = pulse_duration * 17150
    return distance_cm


def read_pulse_oximeter():
    red, ir = mx30.read_sequential()
    heart_rate = mx30.calculate_heart_rate(ir)
    spo2 = mx30.calculate_spo2(ir, red)
    return heart_rate, spo2


def beep():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BUZZER_PIN, GPIO.LOW)


def display_on_lcd(line1, line2):
    lcd.clear()
    lcd.write_string(line1)
    lcd.crlf()
    lcd.write_string(line2)


def calibrate():
    # Measure the initial distance when there's no weight on the springs
    no_weight_distance = measure_distance()
    display_on_lcd("Calibration", "completed")
    time.sleep(2)
    return no_weight_distance


def measure_weight(no_weight_distance):
    # Measure the current distance
    current_distance = measure_distance()

    # Calculate the difference between the current distance and no weight distance
    distance_difference = no_weight_distance - current_distance

    # Assuming a linear relationship between distance and weight, apply calibration factor
    # Adjust the calibration_factor based on your actual measurements and calibration
    reference_weight = 0  # Adjust this based on your setup
    calibration_factor = reference_weight / no_weight_distance
    weight = distance_difference * calibration_factor

    return weight


try:
    # Calibrate the system
    no_weight_distance = calibrate()

    # Main program
    phone_number = input("Enter your phone number: ")
    display_on_lcd("Phone Number:", phone_number)
    beep()
    time.sleep(2)

    # Sanitizing at entry
    display_on_lcd("Sanitizing...", "")
    beep()
    time.sleep(2)

    # Enter the system
    display_on_lcd("Enter the", "system")
    beep()
    time.sleep(2)

    # Measure height
    display_on_lcd("Measuring", "height...")
    height = measure_distance()  # Assuming ultrasonic measures height
    beep()
    time.sleep(2)

    # Measure weight
    display_on_lcd("Measuring", "weight...")
    weight = measure_weight(no_weight_distance)
    beep()
    time.sleep(2)

    # Measure pulse and oxygen level
    display_on_lcd("Measuring", "pulse & oxygen...")
    heart_rate, spo2 = read_pulse_oximeter()
    beep()
    time.sleep(2)

    # Calculate BMI
    bmi = weight / ((height / 100) ** 2)

    # Send message containing all data to the user
    message = f"Height: {height} cm\nWeight: {weight} kg\nBMI: {bmi:.2f}\nPulse: {heart_rate} bpm\nOxygen Level: {spo2}%"
    print("Message sent to user:")
    print(message)

except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()