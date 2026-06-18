import os
import time
import datetime
import pandas as pd
from sklearn.ensemble import IsolationForest
from dotenv import load_dotenv

load_dotenv()

import config as cfg
from threads.notifier import send_telegram_alert

def thread_ml_analysis(state, lock):
    env_private_key = os.environ.get("PRIVATE_KEY")
    print("[스레드 5] Isolation Forest 기반 분석")
    
    model = None

    while True:
        if model is None:
            time.sleep(20)

            try:
                start_block = 278109688 # 지갑 주소의 정상 데이터 시작 블럭
                if env_private_key:
                    wallet_address = cfg.w3.eth.account.from_key(env_private_key).address

                    logs = cfg.contract.events.EnergyDataRecorded().get_logs(
                        argument_filters={'device': wallet_address}, 
                        from_block=start_block,
                        to_block='latest'
                     )
                else: 
                    logs = cfg.contract.events.EnergyDataRecorded().get_logs(
                        from_block=start_block,
                        to_block='latest'
                     )

                if len(logs) < 3:
                    history_data = [15.0, 16.2, 14.8, 15.5, 17.1, 13.9] 
                else:
                    history_data = []
                    for log in logs:
                        try:
                            raw_data = log['args']['powerValue']
                            raw_energy_wh = raw_data / 1000 # 단위 보정
                            restored_power_w = raw_energy_wh * 12;   history_data.append(restored_power_w)
                        except KeyError:
                            raw_data = list(log['args'].values())[1];     raw_energy_wh = raw_data / 1000
                            history_data.append(raw_energy_wh * 12)
                
                # Isolation Forest 모델 학습
                df_train = pd.DataFrame(history_data, columns=['delta_energy'])
                
                model = IsolationForest(contamination=0.05, random_state=42)
                model.fit(df_train[['delta_energy']])
                print(f"ML 학습 완료\n")
                
            except Exception as init_err:
                print(f"ML 학습 실패")
                time.sleep(5)
                model = None
                continue

        # 30초마다 실시간 센서 값 감시
        try:
            with lock:
                current_power_w = state.get('current_power', 0.0)
            
            current_df = pd.DataFrame([current_power_w], columns=['delta_energy'])
            realtime_result = model.predict(current_df[['delta_energy']])[0]
            
            if realtime_result == -1 and current_power_w > 10.0:
                print(f"ML 이상 탐지")
                
                send_telegram_alert(
                    f"[실시간 이상 추이 경고]\n"
                    f"Isolation Forest 분석, 실시간 전력 추이 이탈"
                    f"실시간 감지 전력량: {current_power_w:.1f} W"
                )
                time.sleep(10)
                
        except Exception as run_err:
            print(f"[ML 실시간 예측 루프 에러]: {run_err}")
            
        time.sleep(30) # 감시 주기
