# -*- coding:utf-8 -*-

import logging
import os

from flask import Flask, session, render_template, request
from tasks.transportation_path import handler
# from entity.entity import get_entity


app = Flask(__name__)
app.secret_key = b'Y\x85\x01\ni\x8d\xd4\x10\xd4\xab\x84U\x17~\x16\x89'

# 로그 환경 초기화 daily rolling log
if not os.path.exists("logs"):
    os.makedirs("logs")

# 로그 / 파일로 로그를 남기기 위해서는 추가 작업 필요
logger = logging.getLogger("chatbot")
logger.setLevel(logging.DEBUG)


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

    output = run(recv_value['input'], recv_value['client_id'])

    # 발신 데이터
    send_value = {"client_id": recv_value["client_id"], "message_id": recv_value["message_id"], "output": output}
    logger.warning(f"send: {send_value}")

    return send_value


def run(message, client_id):
    if 'state' not in session:
        session['state'] = 'waiting'

    state = session['state']

    if message == "/start":
        output = "가장 안전한 길을 알려드리는 Safe Transfer입니다. :)<br/>먼저, 출발지를 알려주세요!"
        session['state'] = 'ask_origin'

    elif state == 'ask_origin':
        html_path, item_list = handler.ask_origin(message)

        if html_path is None:
            output = '검색 결과가 없습니다! 이름을 확인해주세요.</br>출발지는 정류장 이름으로 검색됩니다!'
        else:
            output = '원하시는 출발지에 가장 가까운 정류장을 숫자로 말씀해주세요!<br/><iframe src="%s" width="300" height="300"></iframe>' % html_path
            session['state'] = 'ask_detail_origin'
            session['start_locs'] = item_list

    elif state == 'ask_detail_origin':
        item_list = session['start_locs']
        max_station = len(item_list)

        if not message.isnumeric():
            output = '숫자만 입력해주세요!'
        elif int(message) < 1 or max_station < int(message):
            output = '1 ~ %d 사이의 숫자를 입력해주세요!' % max_station
        else:
            output = '이제 목적지를 알려주세요!'
            session['start_idx'] = int(message)
            session['state'] = 'ask_destination'

    elif state == 'ask_destination':
        html_path, item_list = handler.ask_destination(message)

        if html_path is None:
            output = '검색 결과가 없습니다! 이름을 확인해주세요.</br>목적지는 정류장 이름으로 검색됩니다!'
        else:
            output = '원하시는 목적지에 가장 가까운 정류장을 숫자로 말씀해주세요!<br/><iframe src="%s" width="300" height="300"></iframe>' % html_path
            session['state'] = 'ask_detail_destination'
            session['end_locs'] = item_list
    else:
        output = 'test test'

    return output


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
