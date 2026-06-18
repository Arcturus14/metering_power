import time
from luma.core.render import canvas
import config as cfg

def thread_display(state, lock, g_queue):
    print("[스레드 2] LCD 디스플레이")
    
    info_x_start = 325
    pad_left, pad_right, pad_top, pad_bottom = 50, 10, 45, 40
    graph_width = 310 - pad_left - pad_right
    graph_height = cfg.device.height - pad_top - pad_bottom
    
    while True:
        # 인터넷 상태 먼저 체크
        net_status = cfg.check_network()
        
        # 체크한 결과와 실시간 데이터들을 안전하게 RAM에서 꺼냄
        with lock:
            state['is_online'] = net_status  # 실시간 네트워크 상태
            mode = state.get('display_mode', 0)
            v_now = state.get('current_voltage', 0.0)
            c_now = state.get('current_current', 0.0)
            p_now = state.get('current_power', 0.0)
            current_max_power = state.get('day_max_power', 0.0)
            is_online_now = state['is_online']
            power_values = list(g_queue)
            
        # 캔버스 프레임
        with canvas(cfg.device) as draw:
            draw.rectangle(cfg.device.bounding_box, outline="black", fill="black")
            
            draw.text((15, 12), "Real time Power Graph", fill="orange", font=cfg.font_title)
            draw.line([(315, 0), (315, cfg.device.height)], fill="gray", width=1)
            
            draw.line([(pad_left, pad_top), (pad_left, cfg.device.height - pad_bottom)], fill="white", width=2)
            draw.line([(pad_left, cfg.device.height - pad_bottom), (310 - pad_right, cfg.device.height - pad_bottom)], fill="white", width=2)
            
            if len(power_values) >= 2:
                max_power_graph = max(power_values)
                min_power_graph = 0.0

                if max_power_graph > 0:
                    y_axis_max = max_power_graph * 1.10
                else:
                    y_axis_max = 10.0

                power_range = max_power_graph - min_power_graph if max_power_graph != min_power_graph else 1 
                
                draw.text((10, pad_top + 15), f"{int(max_power_graph)}W", fill="gray", font=cfg.font_small)
                draw.text((10, cfg.device.height - pad_bottom - 10), f"{int(min_power_graph)}W", fill="gray", font=cfg.font_small)
                
                points = []
                for i, val in enumerate(power_values):
                    x = pad_left + int((i / (len(power_values) - 1)) * graph_width)
                    y_ratio = (val - min_power_graph) / power_range
                    y = cfg.device.height - pad_bottom - int(y_ratio * graph_height *0.9)
                    points.append((x, y))
                
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill="yellow", width=3)
            else:
                draw.text((80, 140), "...", fill="orange", font=cfg.font_medium)
            
            # 오른쪽 영역
            draw.text((info_x_start, 15), "NETWORK", fill="lightgray", font=cfg.font_small)
            # is_online_now 데이터로 플래그 판정
            draw.text((info_x_start, 30), "ONLINE" if is_online_now else "OFFLINE", fill="lime" if is_online_now else "red", font=cfg.font_medium)
            draw.text((info_x_start, 75), "NOW", fill="lightgray", font=cfg.font_small)
            draw.text((info_x_start, 93), f"{p_now:.1f} W", fill="orange", font=cfg.font_large)
            draw.text((info_x_start, 155), "MAX (Window)", fill="lightgray", font=cfg.font_small)
            draw.text((info_x_start, 173), f"{max(power_values) if power_values else 0:.1f} W", fill="orange", font=cfg.font_medium)
            draw.text((info_x_start, 235), "DAY MAX", fill="lightgray", font=cfg.font_small)
            draw.text((info_x_start, 253), f"{current_max_power:.1f} W", fill="orange", font=cfg.font_medium)

        time.sleep(5)