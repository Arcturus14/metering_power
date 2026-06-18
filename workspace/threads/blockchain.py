import time
import queue
import config as cfg
import threads.notifier as nt
import pandas as pd
from datetime import datetime
import os

def thread_blockchain(state, lock, b_queue):
    print("[스레드 3] 블록체인 mWh 온체인 연동 전송 모듈 가동")
    
    while True:
        try:
            # 큐에서 3분 주기 선입선출
            payload = b_queue.get(timeout=5)
            
            if payload['delta_energy'] <= 0 or not cfg.private_key:
                with lock:
                    state['last_energy_val'] = payload['total_energy']
                    state['offline_start_time'] = None
                b_queue.task_done()
                continue
                
            # CSV 백업 업로드 전 먼저 기록해서 로컬 데이터 보존
            date_suffix = datetime.now().strftime('%y%m%d')
            csv_file_path = f"./data/history_{date_suffix}.csv"
            current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
           
            row = {
                'timestamp': [current_time_str],
                'delta_energy': [payload['delta_energy']]
            }

            df = pd.DataFrame(row)
            file_exists = os.path.exists(csv_file_path)
            df.to_csv(
                csv_file_path, 
                mode='a', 
                index=False, 
                header=not file_exists, 
                encoding='utf-8-sig'
            )

            # 릴레이 온체인 전송: 성공할 때까지 재시도
            success = False
            while not success:
                try:
                    nonce = cfg.w3.eth.get_transaction_count(cfg.my_address)
                    
                    tx = cfg.contract.functions.recordEnergy(int(payload['delta_energy'])).build_transaction({
                        'chainId': 421614, 
                        'gas': 2000000,
                        'gasPrice': int(cfg.w3.eth.gas_price * 1.5),
                        'nonce': nonce,
                    })
                    # 개인키 서명 ,트랜잭션 전송
                    signed_tx = cfg.w3.eth.account.sign_transaction(tx, private_key=cfg.private_key)
                    tx_hash = cfg.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    
                    # 블록에 박힐 때까지 대기
                    cfg.w3.eth.wait_for_transaction_receipt(tx_hash)
                    
                    with lock:
                        state['last_energy_val'] = payload['total_energy']
                        state['offline_start_time'] = None
                    
                    nt.tx_count += 1
                    success = True # 무한 루프 탈출
                    
                    time.sleep(5)
                    
                except Exception as tx_error:
                    time.sleep(10) 
            
            # 최종 완료 처리
            b_queue.task_done()
                    
        except queue.Empty:
            continue
        except Exception as global_error:
            time.sleep(5)