import time
import datetime
import modbus_tk.defines as cst
import config as cfg
from threads.notifier import send_telegram_alert

def thread_measure(state, lock, b_queue, g_queue):
    print("[스레드 1] Measure start")
    
    elapsed_time = 0
    MEASURE_INTERVAL = 5 # (second)
    
    std_minutes = 5
    last_settle_time = time.time()
    
    # 센서 레지스터 energy 값 초기화
    start_energy_val = None

    while True:
        try:
            cfg.ser.reset_input_buffer()
            data = cfg.master.execute(cfg.SLAVE_ID, cst.READ_INPUT_REGISTERS, 0, 10)
            
            if data and len(data) >= 10:
                v_val = data[0] * 0.1
                c_val = ((data[2] << 16) | data[1]) * 0.001
                p_val = ((data[4] << 16) | data[3]) * 0.1
                e_val = (data[6] << 16) | data[5] 
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with lock:
                    state['current_voltage'] = v_val; state['current_current'] = c_val
                    state['current_power'] = p_val;   state['current_energy'] = e_val
                    g_queue.append(p_val)
                    
                    if p_val > state['day_max_power']:
                        state['day_max_power'] = p_val
                    
                    if state['last_energy_val'] is None:
                        state['last_energy_val'] = e_val
                
                if start_energy_val is None:
                    start_energy_val = e_val

                if p_val > cfg.OVER_POWER_THRESHOLD:
                    print(f"[과전력] 전력 수치 초과: {p_val} W")
                    send_telegram_alert(
                        f"[과전력 위험 경고]\n"
                        f"계측된 전력이 설정된 임계값을 초과했습니다.\n"
                        f"부하 확인 필요\n"
                        f"실시간 사용 전력: {p_val:.1f} W"
                    )
            
            # 3분 차분 및 분할 큐 적재
            if time.time() - last_settle_time >= std_minutes * 60:
                
                # 레지스터 값의 차분값 계산
                diff_energy_wh = e_val - start_energy_val
                
                # mWh 정수형으로 단위 변환
                delta_energy_mwh = int(round(diff_energy_wh * 1000))
                
                payload = {
                    "timestamp": now_str,
                    "delta_energy": delta_energy_mwh,
                    "total_energy": e_val,
                    "duration_min": std_minutes # 3분 분할 고정
                }
                
                # (2시간 = 120분 / 3분 = 최대 40개)
                if b_queue.full():
                    print("[큐 가득 참] 2시간 단선 초과")
                    try:
                        # 가장 오래된 데이터부터 제거
                        b_queue.get_nowait()
                    except Exception:
                        pass
                
                b_queue.put(payload)
                print(f"[큐 저장] 레지스터 차분 값 저장: {delta_energy_mwh} mWh")
                
                # 타이머를 현재 시점으로 최신화
                start_energy_val = e_val;   last_settle_time = time.time()
                        
        except Exception as e:
            print(f"[센서 에러 발생]: {e}")
            
        time.sleep(MEASURE_INTERVAL)