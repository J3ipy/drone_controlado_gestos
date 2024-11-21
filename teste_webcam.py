from djitellopy import Tello  # Biblioteca do drone
import cv2  # Biblioteca para processamento de imagem e vídeo
import mediapipe as mp  # Biblioteca para detecção de mãos
import threading  # Biblioteca para executar múltiplas threads simultaneamente
import logging  # Biblioteca para registrar logs
import time  # Biblioteca para manipular tempo e delays

# Criando um objeto Tello
tello = Tello()
tello.LOGGER.setLevel(logging.ERROR)  # Reduz logs de erros do Tello

fly = True  # Controle do modo de voo: True para voar, False para apenas testes
gesture = 'Desconhecido'  # Inicializa o gesto como desconhecido

# Configuração da detecção de mãos com MediaPipe
mpHands = mp.solutions.hands
hands = mpHands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)

# Inicializa a captura da webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Erro: Não foi possível acessar a webcam.")
    exit()

# Conecta ao drone e inicia a transmissão de vídeo
tello.connect()
tello.streamon()
frame_read = tello.get_frame_read()


def hand_detection():
    """
    Função responsável por detectar gestos com base nos frames da webcam.
    """
    global gesture
    frame_counter = 0  # Contador de frames para controle de processamento

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erro ao capturar imagem da webcam")
            break

        frame = cv2.flip(frame, 1)  # Espelha a imagem para parecer um espelho

        if frame_counter % 3 == 0:  # Processa a cada 3 frames para reduzir o lag
            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame_height, frame_width = frame.shape[:2]

            if result.multi_hand_landmarks:
                for hand_lms, hand_side in zip(result.multi_hand_landmarks, result.multi_handedness):
                    if hand_side.classification[0].label == 'Right':  # Ignora a mão direita
                        continue

                    my_hand = [
                        (int(lm.x * frame_width), int(lm.y * frame_height))
                        for lm in hand_lms.landmark
                    ]

                    # Configuração dos dedos levantados
                    finger_on = []
                    if my_hand[4][0] > my_hand[2][0]:  # Polegar
                        finger_on.append(1)
                    else:
                        finger_on.append(0)
                    for i in range(1, 5):  # Outros dedos
                        if my_hand[4 + i * 4][1] < my_hand[2 + i * 4][1]:
                            finger_on.append(1)
                        else:
                            finger_on.append(0)

                    if sum(finger_on) == 5:
                        gesture = 'Pousar'
                    elif sum(finger_on) == 1:
                        if finger_on[0] == 1:
                            gesture = 'Direita'
                        elif finger_on[4] == 1:
                            gesture = 'Esquerda'
                        elif finger_on[1] == 1:
                            gesture = 'Cima'
                    elif sum(finger_on) == 2:
                        if finger_on[0] == finger_on[1] == 1:
                            gesture = 'Baixo'
                        elif finger_on[1] == finger_on[2] == 1:
                            gesture = 'Come'
                    elif sum(finger_on) == 3 and finger_on[1] == finger_on[2] == finger_on[3] == 1:
                        gesture = 'Away'
                    elif sum(finger_on) == 4:
                        gesture = 'Girar'
                    else:
                        gesture = 'Desconhecido'

        cv2.putText(frame, gesture, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 3)
        cv2.imshow('Controle por Gestos (Webcam)', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Sai ao pressionar 'q'
            gesture = 'Pousar'
            break

        frame_counter += 1


def drone_video():
    """
    Função para exibir o feed de vídeo da câmera do drone.
    """
    while True:
        frame = frame_read.frame
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Converte para RGB
            frame = cv2.resize(frame, (640, 480))
            cv2.imshow('Drone', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Sai ao pressionar 'q'
            break


video_thread = threading.Thread(target=hand_detection, daemon=True)
drone_thread = threading.Thread(target=drone_video, daemon=True)
video_thread.start()
drone_thread.start()

if fly:
    tello.takeoff()
    tello.set_speed(10)
    time.sleep(2)
    tello.move_up(80)

while True:
    hV = dV = vV = rV = 0
    if gesture == 'Pousar':
        break
    elif gesture == 'Desconhecido':
        hV = dV = vV = rV = 0
    elif gesture == 'Direita':
        hV = -15
    elif gesture == 'Esquerda':
        hV = 15
    elif gesture == 'Cima':
        vV = 20
    elif gesture == 'Baixo':
        vV = -20
    elif gesture == 'Come':
        dV = 15
    elif gesture == 'Away':
        dV = -30
    elif gesture == 'Girar':
        tello.rotate_clockwise(90)
        time.sleep(0.1) 

    tello.send_rc_control(hV, dV, vV, rV)
    time.sleep(0.2)

if fly:
    tello.land()

gesture = 'Pousado'

tello.streamoff()
cap.release()
cv2.destroyAllWindows()

print("Bateria:", tello.get_battery())
