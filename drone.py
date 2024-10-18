#libs usadas

from djitellopy import Tello #lib do drone
import cv2 #lib para processamento de imagem e vídeo
import mediapipe as mp #lib para detecção e rastreamento das mãos
import threading #lib que permite executar múltiplas threads simultaneamente
import logging # lib que registra infos e logs de erros
import time # lib para manipular o tempo e delays

# criando um obj tello
tello = Tello()
tello.LOGGER.setLevel(logging.ERROR)  # ignorar algumas infos de ERROR do tello
fly = True  # True: Voa, False: Não voa (Debugar)

# detecção das mãos
mpHands = mp.solutions.hands
hands = mpHands.Hands(min_detection_confidence=0.6, min_tracking_confidence=0.6)  # nível de confiança 

def hand_detection(tello):
    frame_counter = 0  

    while True:
        global gesture
        
        #  Ler o frame capturado pelo drone
        frame = tello.get_frame_read().frame
        frame = cv2.flip(frame, 1)

        # Processa a cada terceiro frame para diminuir o lag
        if frame_counter % 3 == 0:
            
            result = hands.process(frame)
            frame_height, frame_width = frame.shape[:2]
            my_hand = []

            if result.multi_hand_landmarks:
                for handlms, handside in zip(result.multi_hand_landmarks, result.multi_handedness):
                    if handside.classification[0].label == 'Right':  # Ignora a mão direita
                        continue

                    # Converte todas as informações da mão de uma proporção para a posição real de acordo com o tamanho do quadro.
                    for i, landmark in enumerate(handlms.landmark):
                        x = int(landmark.x * frame_width)
                        y = int(landmark.y * frame_height)
                        my_hand.append((x, y))

                    # Config da mão esquerda.
                    # Pare, um punho; Pousar, mão aberta; Direita, apenas o polegar aberto; 
                    # Esquerda, apenas o dedinho aberto; Para cima, apenas o dedo indicador aberto; 
                    # Para baixo, polegar e indicador abertos;
                    finger_on = []
                    if my_hand[4][0] > my_hand[2][0]:
                        finger_on.append(1)
                    else:
                        finger_on.append(0)
                    for i in range(1, 5):
                        if my_hand[4 + i * 4][1] < my_hand[2 + i * 4][1]:
                            finger_on.append(1)
                        else:
                            finger_on.append(0)

                    gesture = 'Desconhecido'
                    if sum(finger_on) == 0:
                        gesture = 'Pare'
                    elif sum(finger_on) == 5:
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

        cv2.putText(frame, gesture, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 0), 3)
        cv2.imshow('drone', frame)
        cv2.waitKey(1)

        if gesture == 'Pousado':
            break

        frame_counter += 1  


#aqui começa o programa do drone


# conecta o drone ao wifi
tello.connect()

# o drone liga o stream da camera 
tello.streamon()

#espera até o primeiro frame for lido
while True:
    frame = tello.get_frame_read().frame
    if frame is not None:
        break

# Começa a detecção da mão quando o drone está voando
gesture = 'Desconhecido'
video_thread = threading.Thread(target=hand_detection, args=(tello,), daemon=True)
video_thread.start()

# Voar o drone
time.sleep(1)
if fly:
    tello.takeoff()
    tello.set_speed(10)
    time.sleep(2)
    tello.move_up(100)

while True:
    hV = dV = vV = rV = 0
    if gesture == 'Pousar':
        break
    elif gesture == 'Pare' or gesture == 'Desconhecido':
        hV = dV = vV = rV = 0
    elif gesture == 'Direita':
        hV = -15
    elif gesture == 'Esquerda':
        hV = 15
    elif gesture == 'Cima':
        vV = 20
    elif gesture == 'Baixo':
        vV = -20

    tello.send_rc_control(hV, dV, vV, rV)

    # Delay de 0,2s para ler os gestos
    time.sleep(0.2)  

# Pousar o drone (interrompe o looping)
if fly:
    tello.land()
gesture = 'Pousado'

# Para o stream do frame
tello.streamoff()

# Mostra a bateria do drone no terminal
print("Bateria:", tello.get_battery())
