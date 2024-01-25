import time
from hx711 import HX711 as wt  # Library for HX711 weight sensor
import RPi.GPIO as sms  # Library for GPIO
from max30102 import heart  # Library for MAX30102 heartbeat sensor

sms.setmode(sms.BCM)


def initialize_sensors():
    hx711 = wt(dout_pin=23, pd_sck_pin=24)
    hx711.set_scale_ratio(-7050)
    hx711.reset()
    max30102 = heart()


def measure_weight():
    weight = wt.get_weight_mean()
    print(f"Weight: {weight} grams")
    return weight


def measure_height():
    trig_pin = 18
    echo_pin = 25


def measure_heartbeat():
    heart.read_sensor()
    heartbeat = heart.get_heart_rate()
    print(f"Heartbeat: {heartbeat} bpm")
    return heartbeat


def all_readings_collected():
    return True


def activate_leave_signal():
    led_pin = 17
    sms.setup(led_pin, sms.OUT)
    sms.output(led_pin, sms.HIGH)
    print("You may leave!")


def send_message(mobile_number, message):
    print(f"Message sent to {mobile_number}: {message}")


def generate_report_message(height, weight, heartbeat):
    return f"Thanks for taking out time for your wellbeing via visiting \n Your Report: Height={height} cm, Weight={weight} grams, Heartbeat={heartbeat} bpm"


def activate_completion_signal():
    pass


def main():
    mobile_number = int(input("Enter your 10-digit mobile number: "))

    initialize_sensors()
    while True:
        height = measure_height()
        weight = measure_weight()
        heartbeat = measure_heartbeat()
        if all_readings_collected():
            activate_leave_signal()
            break

    send_message(mobile_number, generate_report_message(height, weight, heartbeat))
    time.sleep(5)
    activate_completion_signal()


if __name__ == "HM":
    main()
