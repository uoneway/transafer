# -*- coding:utf-8 -*-

import logging
import os

from flask import Flask, session, render_template, request
from tasks.transportation_path import handler
# from entity.entity import get_entity

from config import secret_key

app = Flask(__name__)
app.secret_key = secret_key

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
        output = "가장 안전한 길을 알려드리는 TranSafer 입니다. :)<br/>먼저, 출발지를 알려주세요!"
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
            session['start_loc'] = item_list[int(message)-1]
            session['start_locs'] = None
            session['state'] = 'ask_destination'

    elif state == 'ask_destination':
        html_path, item_list = handler.ask_destination(message)

        if html_path is None:
            output = '검색 결과가 없습니다! 이름을 확인해주세요.</br>목적지는 정류장 이름으로 검색됩니다.</br>서울시 이외의 정류장은 검색되지 않습니다.'
        else:
            output = '원하시는 목적지에 가장 가까운 정류장을 숫자로 말씀해주세요!<br/><iframe src="%s" width="300" height="300"></iframe>' % html_path
            session['state'] = 'ask_detail_destination'
            session['end_locs'] = item_list

    elif state == 'ask_detail_destination':
        item_list = session['end_locs']
        max_station = len(item_list)

        if not message.isnumeric():
            output = '숫자만 입력해주세요!'
        elif int(message) < 1 or max_station < int(message):
            output = '1 ~ %d 사이의 숫자를 입력해주세요!' % max_station
        else:
            session['end_loc'] = item_list[int(message)-1]
            session['end_locs'] = None
            session['state'] = 'print_routes'

            start_loc = session['start_loc']
            end_loc = session['end_loc']

            route_list = handler.search_routes(start_loc, end_loc)
            #session['routes'] = route_list
            #route_list = session['routes']

            if not route_list:
                output = '아쉽지만 혼잡도 정보가 존재하는 환승경로를 찾지 못했어요... </br>다른 경로를 시도해보고 싶으시다면, /start 를 적어주세요!'
            else:
                safest_route_img = handler.visualization_routes(route_list, sort_type='safetest')
                fastest_route_img = handler.visualization_routes(route_list, sort_type='fastest')
                riskiest_route_img = handler.visualization_routes(route_list, sort_type='riskiest')

                output = ('<%s> 부터 <%s> 까지 가는 여러 경로들 중에서, 가장 빠른 환승 경로는 다음과 같아요!</br><img src="%s" width="300" height="345"></br>이 경로들은 상대적으로 이용 시민들이 적어 안전한 경로예요!</br><img src="%s" width="300" height="345"></br>한편, 아래 경로들은 이용 시민들이 많으니 가능하면 피하는 게 좋을 것 같아요!<img src="%s" width="300" height="345">' % (start_loc[0], end_loc[0], fastest_route_img, safest_route_img, riskiest_route_img))

            state = 'waiting'
    else:
        output = '다시 시작하고 싶으시면 /start 를 입력해주세요!'

    return output


def print_routes(route_list):
    traffic_type = ['지하철', '버스', '도보']
    lines = []

    for i, route in enumerate(route_list):
        distance = route['info']['totalDistance']
        time = route['info']['totalTime']
        path_list = route['subPath']

        lines.append('%d. 거리: %.1fkm, 시간: %d분' % (i+1, int(distance)/1000, int(time)))

        for path in path_list:
            lines.append('  [%s] 거리: %dm, 시간: %d분' % (traffic_type[path['trafficType']-1],
                                                         path['distance'],
                                                         path['sectionTime']))

            if path['trafficType'] == 1: # 지하철
                lines.append('    - (%s %s) %s -> %d 역 -> %s (%s m, %s min)'
                    % (','.join([lane['name'] for lane in path['lane']]),
                       path['way'],
                       path['startName'],
                       len(path['passStopList']['stations'][1:-1]),
                       path['endName'],
                       path['distance'],
                       path['sectionTime']))
            elif path['trafficType'] == 2: # 버스
                lines.append('    - (%s 버스) %s -> %s 정류장 -> %s (%s m, %s min)'
                    % (','.join([lane['busNo'] for lane in path['lane']]),
                       path['startName'],
                       len(path['passStopList']['stations'][1:-1]),
                       path['endName'],
                       path['distance'],
                       path['sectionTime']))

        lines.append('')
    return lines


if __name__ == "__main__":
    # Flask 서버 시작
    logger.critical("******************** web_server  started ********************")
    # script 변경 자동 감지 reload
    app.jinja_env.auto_reload = True
    # template 변경 자동 감지 reload
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    handler.init_handler()

    app.run(host='0.0.0.0', debug=True, port=5555)
    # app.run(port=5555)
    logger.critical("******************** web_server finished ********************")
