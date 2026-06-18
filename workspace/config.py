import os
import json
import serial
import socket
from web3 import Web3
from dotenv import load_dotenv

import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

from luma.core.interface.serial import spi
from luma.lcd.device import ili9488
from PIL import ImageFont

import RPi.GPIO as GPIO

load_dotenv()
private_key = os.getenv("PRIVATE_KEY")

# 아비트럼 세폴리아 RPC, 컨트랙트 설정
w3 = Web3(Web3.HTTPProvider("https://sepolia-rollup.arbitrum.io/rpc"))
my_address = w3.eth.account.from_key(private_key).address if private_key else None
contract_address = "0xb551a87e38E7A838d9E8C3ef2CDbD40725Ad6a7B"

# EnergyDataRecorded event log parsing
abi_string = '[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"device","type":"address"},{"indexed":false,"internalType":"uint256","name":"powerValue","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"EnergyDataRecorded","type":"event"},{"inputs":[{"internalType":"uint256","name":"_powerValue","type":"uint256"}],"name":"recordEnergy","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
contract = w3.eth.contract(address=contract_address, abi=json.loads(abi_string))

# 과전력 차단 임계값
OVER_POWER_THRESHOLD = 100.0  

# sensor setting
PORT = '/dev/ttyUSB0'
SLAVE_ID = 20

try:
    ser = serial.Serial(port=PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=2.0)
    master = modbus_rtu.RtuMaster(ser)
    master.set_timeout(2.0)
except Exception as e:
    exit(1)

# TFT LCD setting
serial_spi = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
device = ili9488(serial_spi, width=480, height=320)

try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 16)
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26)
    font_giant = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36) 
    font_medium = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",18)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 12)
except IOError:
    font_title = font_large = font_giant = font_medium = font_small = None

# GPIO setting
BUTTON_PIN = 21
GPIO.setmode(GPIO.BCM)  
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# network 연결 여부 확인 용
def check_network():
    try:
        socket.setdefaulttimeout(3.0)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except socket.error:
        return False
