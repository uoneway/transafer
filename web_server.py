# -*- coding:utf-8 -*-

import logging
import os

from flask import Flask, render_template, request
# from entity.entity import get_entity
from tasks.transportation_path.handler import process_input as transportation_path_process_input

app = Flask(__name__)

# 로그 환경 초기화 daily rolling log
if not os.path.exists("logs"):
    os.makedirs("logs")

# 로그 / 파일로 로그를 남기기 위해서는 추가 작업 필요
logger = logging.getLogger("chatbot")
logger.setLevel(logging.DEBUG)

state = 'waiting'
state_machine = {
    'waiting': {'ask_origin'},
    'ask_origin': {'ask_detail_origin', 'waiting'},
    'ask_detail_origin': {'ask_destination', 'waiting'},
    'ask_destination': {'ask_detail_destination', 'waiting'},
    'ask_detail_destination': {'print_routes', 'waiting'},
    'print_routes': {'route_visualization', 'waiting'},
    'route_visualization': {'print_route', 'waiting'}
}


# 챗봇 화면 출력
@app.route("/", methods=["GET"])
def chat_client():
    # return "나는 챗봇 입니다."
    # templates/chat_client.html 을 읽어서 return 합니다.
    return render_template("chat_client.html")


# 챗봇 메시지 처리
@app.route("/chat_message", methods=["POST"])
def chat_message():
    # 수신 데이터
    recv_value = request.form.to_dict(flat=True)
    logger.warning(f"recv: {recv_value}")

    if recv_value["input"] == "/start":  # html 내 do_chat_start() 에서 처음 시작할 때 /start를 호출하도록 되어있음
        # 최초 인사말
        output = start_message(recv_value)
    else:######################수정필요####################################
        #entity = get_entity(recv_value)
        output = transportation_path_process_input(recv_value)  # , entity

    # 발신 데이터
    send_value = {"client_id": recv_value["client_id"], "message_id": recv_value["message_id"], "output": output}
    logger.warning(f"send: {send_value}")
    return send_value


def start_message(recv_value):
    return "가장 안전한 길을 알려드리는 Safe Transfer입니다. :)<br/>어디서 어디로 가고 싶으신가요?"


if __name__ == "__main__":
    # Flask 서버 시작
    logger.critical("******************** web_server  started ********************")
    # script 변경 자동 감지 reload
    app.jinja_env.auto_reload = True
    # template 변경 자동 감지 reload
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run(debug=True, port=5555)
    # app.run(port=5555)
    logger.critical("******************** web_server finished ********************")