import os
import time
import threading
import queue
from collections import deque
import RPi.GPIO as GPIO

import config as cfg
from threads.measure import thread_measure
from threads.display import thread_display
from threads.blockchain import thread_blockchain
from threads.ml_analysis import thread_ml_analysis

# 시스템 전역 메모리 
system_state = {
    'last_energy_val': None,
    'offline_start_time': None,
    'is_online': False,
    'display_mode': 0,
    'current_voltage': 0.0,
    'current_current': 0.0,
    'current_power': 0.0,
    'current_energy': 0.0,
    'day_max_power': 0.0
}

data_lock = threading.Lock()
blockchain_queue = queue.Queue(maxsize=24)
graph_queue = deque(maxlen=25)

if __name__ == "__main__":
    
    # 4개 스레드 객체 mapping 
    t1 = threading.Thread(target=thread_measure, args=(system_state, data_lock, blockchain_queue, graph_queue), daemon=True)
    t2 = threading.Thread(target=thread_display, args=(system_state, data_lock, graph_queue), daemon=True)
    t3 = threading.Thread(target=thread_blockchain, args=(system_state, data_lock, blockchain_queue), daemon=True)
    t4 = threading.Thread(target=thread_ml_analysis, args=(system_state, data_lock), daemon=True)
    
    # 멀티 스레드 동시 시작
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()  
        cfg.ser.close()