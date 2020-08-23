# -*- coding:utf-8 -*-
import datetime
import folium
import itertools
import json
import pickle
import requests
import time
import warnings
import xmltodict

import matplotlib.font_manager as fm
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from folium.features import DivIcon
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# local modules
from .config import odsay_api_key, seoul_api_key


seoul_api_url = 'http://ws.bus.go.kr/api/rest/pathinfo'
odsay_api_url = 'https://api.odsay.com/v1/api/'

BUS_SPEED_MEAN = 18.7 * 1000  # 미터 https://www.index.go.kr/potal/stts/idxMain/selectPoSttsIdxSearch.do?idx_cd=4081&stts_cd=408102

getout_bus_prep_m_df = None
subway_congestion_dict = None
subway_risk_dict = None
bus_risk_dict = None
mask_imgs = None


def init_handler(data_dir='tasks/transportation_path/dataset/'):
    global getout_bus_prep_m_df, subway_congestion_dict, subway_risk_dict, bus_risk_dict, mask_imgs

    plt.rc('font', family='AppleGothic')

    if not getout_bus_prep_m_df:
        # 버스 노선/정류소별 일별/시간대별 데이터 가져오기
        getout_bus_prep_file = data_dir + "getout_bus_prep_m_df(202005)_min.csv"
        getout_bus_prep_m_df = pd.read_csv(getout_bus_prep_file)
        getout_bus_prep_m_df = getout_bus_prep_m_df.astype({'TIME': 'int',
                                                            'BUS_ROUTE_NO': 'str'})

    if not subway_congestion_dict:
        with open(data_dir + 'station_congestion_2015.pkl', 'rb') as file:
            subway_congestion_df = pickle.load(file)

        subway_congestion_dict = subway_congestion_df.set_index(
            ['사용일', '역번', '구분']).to_dict('index')

        with open(data_dir + 'station_congestion_2015_est_5_8.pkl', 'rb') as file:
            subway_congestion_58_df = pickle.load(file)

        subway_congestion_dict.update(subway_congestion_58_df.set_index(
            ['사용일', '역번', '구분']).to_dict('index'))

        df = pd.read_csv(data_dir + '서울특별시 노선별 지하철역 정보(신규)_fix.csv')
        subway_code = {}

        for i, row in df.iterrows():
            subway_code[row['전철역코드']] = row['외부코드']

        subway_congestion_dict = {
            (key[0], subway_code.get(str(key[1]), str(key[1])), key[2]):value
            for key, value in subway_congestion_dict.items()
        }

    if not subway_risk_dict:
        with open(data_dir + 'subway_risk_dict.pkl', 'rb') as file:
            subway_risk_dict = pickle.load(file)

        subway_risk_dict = {key: value/key
                            for key, value in subway_risk_dict.items()}

    if not bus_risk_dict:
        with open(data_dir + 'bus_risk_dict.pkl', 'rb') as file:
            bus_risk_dict = pickle.load(file)

        bus_risk_dict = {key: value/key for key, value in bus_risk_dict.items()}

    if not mask_imgs:
        mask_imgs = {
            'safe': plt.imread('static/img/mask-safe.png'),
            'normal': plt.imread('static/img/mask-normal.png'),
            'unsafe': plt.imread('static/img/mask-unsafe.png'),
            'risky': plt.imread('static/img/mask-risky.png'),
        }

    return None


def get_location_info(desc_location):
    param = {'stSrch': desc_location}
    url = '%s/getLocationInfo?ServiceKey=%s' % (seoul_api_url, seoul_api_key)
    res = requests.get(url, params=param)

    return res


def response_to_dict(res, type='xml'):
    if type == 'xml':
        return json.loads(json.dumps(xmltodict.parse(res.text)))
    elif type == 'json':
        return json.loads(res.text)


def draw_locations_on_map(item_list):
    Xs, Ys = zip(*[(float(item['gpsX']), float(item['gpsY'])) for item in item_list])
    mean_loc = (Ys[0], Xs[0])
    map_osm = folium.Map(location=mean_loc, zoom_start=16)

    for i, item in enumerate(item_list):
        loc = (item['gpsY'], item['gpsX'])

        marker = folium.Marker(loc,
                               popup='%d. %s' % (i+1, item['poiNm']),
                               icon=DivIcon(
                                   icon_size=(50,36),
                                   icon_anchor=(25,18),
                                   html='<div style="font-size: 18pt; color: white; text-align: center;">%d</div>' % (i+1)))
                              #icon=folium.Icon(color='red'))

        marker.add_to(map_osm)
        map_osm.add_child(folium.CircleMarker(loc, fill=True, radius=15, color='crimson', fill_opacity=0.5))

    return map_osm


def ask_origin(output):
    res = get_location_info(output)
    res_dict = response_to_dict(res)

    if res_dict['ServiceResult']['msgHeader']['headerCd'] == '4': # 결과 없음
        return None, 0

    item_list = res_dict['ServiceResult']['msgBody']['itemList']

    if not isinstance(item_list, list):
        item_list = [item_list]

    map_osm = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map_osm.save(html_path)

    return html_path, [(item['poiNm'], item['gpsX'], item['gpsY']) for item in item_list]


def ask_destination(output):
    res = get_location_info(output)
    res_dict = response_to_dict(res)

    if res_dict['ServiceResult']['msgHeader']['headerCd'] == '4': # 결과 없음
        return None, 0

    item_list = res_dict['ServiceResult']['msgBody']['itemList']

    if not isinstance(item_list, list):
        item_list = [item_list]

    map_osm = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map_osm.save(html_path)

    return html_path, [(item['poiNm'], item['gpsX'], item['gpsY']) for item in item_list]


def get_path_info(start_loc, end_loc):
    print(start_loc, end_loc)

    param = {
        'apiKey': odsay_api_key,
        'SX': start_loc[1],
        'SY': start_loc[2],
        'EX': end_loc[1],
        'EY': end_loc[2]
    }
    res = requests.get(odsay_api_url + 'searchPubTransPathR', params=param)

    return res


def search_routes(start_loc, end_loc):
    res = get_path_info(start_loc, end_loc)
    res_dict = json.loads(res.text)
    route_list = res_dict['result']['path']

    compressed_route_list = []

    for route in route_list:
        compressed_route = {
            'origin': route['info']['firstStartStation'],
            'destination': route['info']['lastEndStation'],
            'total_time': route['info']['totalTime'],
            'payment': route['info']['payment'],
            'map_object': route['info']['mapObj'],
        }

        predicted_time = datetime.datetime.strptime('2020-08-24 09:05:00', '%Y-%m-%d %H:%M:%S')
        #datetime.datetime.fromtimestamp(time.time())
        path_list = []

        for path in route['subPath']:
            path, predicted_time = compress_path(path, predicted_time)
            if path:
                path_list.append(path)

        for paths in itertools.product(*path_list):
            compressed_route_list.append(compressed_route.copy())
            compressed_route_list[-1]['path_list'] = paths

    bus_info_cache = {}

    for route in compressed_route_list:
        for path in route['path_list']:
            if path['type'] == '버스':
                attach_congestion_count_at_bus(path, bus_info_cache)
            elif path['type'] == '지하철':
                attach_congestion_count_at_subway(path)

    result = []
    for i, route in enumerate(compressed_route_list):
        count = 0
        for path in route['path_list']:
            if path['type'] == '도보':
                continue

            for station in path['stations']:
                if 'predicted_congestion' not in station:
                    count += 1
        if count == 0:
            result.append(route)
    compressed_route_list = result
    print(result)

    for i, route in enumerate(compressed_route_list):
        route['risk_score'] = check_risk_score_per_route(route)
        route['mean_risk'] = np.mean([station['predicted_risk']
                                       for path in route['path_list']
                                       for station in path.get('stations', [])])

    return compressed_route_list


def visualization_routes(route_list, top_n=3, sort_type='safetest'):
    fig, ax = plt.subplots(top_n, 1, figsize=(10, top_n*3.5+1))

    if sort_type == 'fastest':
        title = '최단 거리 환승 경로'
    elif sort_type == 'safetest':
        title = '안전한 환승 경로'
        route_list = sorted(route_list,
                            key=lambda x:(x['risk_score'], x['mean_risk']))
    elif sort_type == 'riskiest':
        title = '위험한 환승 경로'
        route_list = sorted(route_list,
                            key=lambda x:(x['risk_score'], x['mean_risk']), reverse=True)

    fig.suptitle(title, y=1.03, fontsize=18)

    for i, route in enumerate(route_list[:top_n]):
        congestions = []
        x_names = []
        x_types = []

        for path in route['path_list']:
            # 도보의 경우
            if path['type'] == '도보':
                congestions.append(0)
                x_names.append('도보 %d분' % (path['duration']))
                x_types.append((0, 0))

            # 버스의 경우
            elif path['type'] == '버스':
                x_names.extend([s['station_name'] for s in path['stations']])

                # 역 별 시간 계산
                x_types.append((1, 0, '%s 버스 탑승' % path['bus_no']))
                x_types.extend([(1, station['ongoing_time'].seconds/60) for i, station in enumerate(path['stations'][1:], 1)])

                # 혼잡도
                congestions.extend([s['predicted_congestion'] for s in path['stations']])

            # 지하철의 경우
            elif path['type'] == '지하철':
                x_names.extend([s['station_name'] for s in path['stations']])

                # 역 별 시간 계산
                x_types.append((1, 0, '%s호선 탑승' % (path['subway_id'])))
                x_types.extend([(1, station['ongoing_time'].seconds/60) for i, station in enumerate(path['stations'][1:], 1)])

                # 혼잡도
                congestions.extend([s['predicted_congestion'] for s in path['stations']])

        risk_score = route['risk_score']
        total_time = route['total_time']
        mean_risk = route['mean_risk']

        draw_bar_graph(fig, top_n, i, congestions, x_names, x_types,
                       total_time, mean_risk, risk_score)

    plt.tight_layout()
    img_path = 'static/results/img_%s.png' % (repr(time.time()))
    plt.savefig(img_path, dpi=200)

    return img_path


# 해당 버스에 대한 각종 정보가 담긴 dict 반환
def get_bus_info_dict(result_dict):
    info_str_list = ['busNo',
                 'busStartPoint', 'busEndPoint', 'busFirstTime', 'busLastTime',
                 'busTotalDistance',]

    bus_info_dict = {}

    for info_str in info_str_list:
        bus_info_dict[info_str] = result_dict['result'][info_str]

    bus_info_dict['station_num_total'] = len(result_dict['result']['station'])
    bus_info_dict['total_time'] = round(bus_info_dict['busTotalDistance'] / BUS_SPEED_MEAN , 4)

    # 시간은 시간단위 소수점으로 변환
    busFirstTime_list = [ int(string) for string in bus_info_dict['busFirstTime'].split(':')]
    bus_info_dict['busFirstTime']  = round(busFirstTime_list[0] + busFirstTime_list[1]/60, 4)
    busLastTime_list = [ int(string) for string in bus_info_dict['busLastTime'].split(':')]
    bus_info_dict['busLastTime']  = round(busLastTime_list[0] + busLastTime_list[1]/60, 4)

    # bus 배차간격
    # 'busInterval', 'bus_Interval_Week', 'bus_Interval_Sat', 'bus_Interval_Sun'
    try:
        interval_float = int(result_dict['result']['busInterval']) / 60
    except ValueError:
        interval_float = 1

    # station 간 걸리는 시간
    bus_info_dict['time_per_station'] = bus_info_dict['total_time'] / (bus_info_dict['station_num_total'] - 1)

    # 버스 배차시간
    try:
        if is_weekend == 0:
            interval_float = int(result_dict['result']['bus_Interval_Week']) / 60
        else:
            interval_float = int(result_dict['result']['bus_Interval_Sat']) / 60
    except:
        pass
    bus_info_dict['interval'] = round(interval_float, 4)

    return bus_info_dict


def get_path_localStationID_list(result_dict, first_stationID, last_stationID):
    # first_localStationID, last_localStationID 구하기
    # 승하차 인원 계산을 위해 subpath에서 해당 버스를 내리는 지점가지 local id를 구함
    before_path_localStationID_list = []  # 기점부터 subpath 시작지점 전까지
    riding_path_localStationID_list = []   # subpath 시작부터 도착지점까지

    is_our = False
    for station_data in result_dict['result']['station']:
        local_station_id = station_data['localStationID']

        if station_data['stationID'] == int(first_stationID):
            is_our = True

        if is_our:
            riding_path_localStationID_list.append(local_station_id)
        else:
            before_path_localStationID_list.append(local_station_id)

        if station_data['stationID'] == int(last_stationID):
            break

    return (before_path_localStationID_list, riding_path_localStationID_list)


def get_num_in_bus_at_station_list(busID, first_stationID, last_stationID, now):
    now_time = now.hour + now.minute / 60
    is_weekend = 0 if now.weekday() < 5 else 1
    warning_count = 0

    # busLaneDetail API 콜하기
    url = odsay_api_url + 'busLaneDetail'
    param = {
        'apiKey': odsay_api_key,
        'busID': busID
    }

    res = requests.get(url, params=param)
    result_dict = response_to_dict(res, 'json')

    bus_info_dict = get_bus_info_dict(result_dict)
    before_path_localStationID_list, riding_path_localStationID_list = get_path_localStationID_list(result_dict, first_stationID, last_stationID)

    stat_df = getout_bus_prep_m_df[(getout_bus_prep_m_df['BUS_ROUTE_NO'] == bus_info_dict['busNo']) &
                         (getout_bus_prep_m_df['WEEKEND'] == int(is_weekend))]

    # 버스 시작지점 때 타고 있는 사람 수 구하기
    # 현 버스의 기점 출발시간 구하기
    start_time_at_busStartPoint = round(now_time - bus_info_dict['time_per_station'] * len(before_path_localStationID_list) , 3)

    time_at_station = start_time_at_busStartPoint
    current_num_in_bus = 0

    for idx, station_local_id in enumerate(before_path_localStationID_list):
        temp_df = stat_df[(stat_df['STND_BSST_ID'] == int(station_local_id)) & (stat_df['TIME'] == int(time_at_station))]

        if len(temp_df) == 0:
            warning_message = "No information of %s bus at %s station" % (busID, station_local_id)
            #warnings.warn(warning_message)
            warning_count += 1
            continue
        else:
            current_num_in_bus += temp_df['RIDE_NUM_PRED'].values[0] * bus_info_dict['interval']   # 한 시간에 여러대가 지나갈것을 고려하여 보정
            current_num_in_bus -= temp_df['ALIGHT_NUM_PRED'].values[0]  * bus_info_dict['interval']

        time_at_station += bus_info_dict['time_per_station']

    # 해당 이용자가 버스를 타고가는 중 시점별 버스 안에 있는 사람 수 구하기
    time_at_station = now_time
    num_in_bus_at_station_list = []

    for idx, station_local_id in enumerate(riding_path_localStationID_list):
        temp_df = stat_df[(stat_df['STND_BSST_ID'] == int(station_local_id)) & (stat_df['TIME'] == int(time_at_station))]

        if len(temp_df) == 0:
            warning_message = "No information of %s bus at %s station" % (busID, station_local_id)
            #warnings.warn(warning_message)
            warning_count += 1
            continue

        current_num_in_bus += temp_df['RIDE_NUM_PRED'].values[0] * bus_info_dict['interval']   # 한 시간에 여러대가 지나갈것을 고려하여 보정
        current_num_in_bus -= temp_df['ALIGHT_NUM_PRED'].values[0]  * bus_info_dict['interval']

        num_in_bus_at_station_list.append(current_num_in_bus)
        time_at_station += bus_info_dict['time_per_station']

    return num_in_bus_at_station_list, warning_count


def attach_congestion_count_at_bus(path, cache):
    key = (path['bus_id'],
           path['stations'][0]['station_id'],
           path['stations'][-1]['station_id'],
           path['start_time'])

    if key in cache:
        counts, warning_count = cache[key]
    else:
        counts, warning_count = get_num_in_bus_at_station_list(
            path['bus_id'],
            path['stations'][0]['station_id'],
            path['stations'][-1]['station_id'],
            path['start_time'])
        cache[key] = (counts, warning_count)

    for count, station in zip(counts, path['stations']):
        count = max(count, 0)
        count = min(count, 70)

        station['predicted_count'] = count
        station['predicted_congestion'] = count / 46
        station['predicted_risk'] = bus_risk_dict.get(int(count + 0.5), 0)

    path['warning_count'] = warning_count


def attach_congestion_count_at_subway(path):
    def way_code_to_name(code, subway_id):
        if subway_id == 2:
            return '내선' if code == 2 else '외선'
        return '상선' if code == 1 else '하선'

    def datetime_to_weekday(now):
        if now.weekday() < 5:
            return '평일'
        return '주말'

    subway_id = path['subway_id']

    if isinstance(subway_id, int):
        way_name = way_code_to_name(path['way_code'], subway_id)
        week_day = datetime_to_weekday(path['start_time'])

        for station in path['stations']:
            hour_name = '%02d:00' % station['start_time'].hour
            try:
                val = subway_congestion_dict[week_day,
                                             str(station['station_id']),
                                             way_name][hour_name]
            except KeyError:
                val = subway_congestion_dict[week_day,
                                             'NaN',
                                             way_code_to_name(path['way_code'], 1)][hour_name]

            val = max(val, 0)
            val = min(val, 368)

            count = val * 1.6

            station['predicted_congestion'] = val/100
            station['predicted_count'] = count
            station['predicted_risk'] = subway_risk_dict.get(int(count + 0.5), 0)


def compress_path(path, predicted_time):
    result = [{'start_time': predicted_time}]

    if path['trafficType'] == 3:
        if path['distance'] == 0:
            return None, predicted_time
        else:
            result[0]['type'] = '도보'
            result[0]['distance'] = path['distance']
            result[0]['duration'] = path['sectionTime']

            predicted_time += datetime.timedelta(minutes=path['sectionTime'])

    elif path['trafficType'] == 2:
        result[0]['type'] = '버스'
        result[0]['distance'] = path['distance']
        result[0]['duration'] = path['sectionTime']
        result[0]['start_name'] = path['startName']
        result[0]['end_name'] = path['endName']

        time_per_station = datetime.timedelta(minutes=path['sectionTime']) / (len(path['passStopList']['stations'])-1)

        result[0]['stations'] = [{'station_id': station['stationID'],
                                  'station_name': station['stationName'],
                                  'start_time': predicted_time + time_per_station * i,
                                  'ongoing_time': time_per_station * i}
                                 for i, station in enumerate(path['passStopList']['stations'])]

        predicted_time += datetime.timedelta(minutes=path['sectionTime'])

        for i in range(len(path['lane'])-1):
            result.append(result[0].copy())

        for i, lane in enumerate(path['lane']):
            result[i]['bus_no'] = lane['busNo']
            result[i]['bus_id'] = lane['busID']
            result[i]['bus_type'] = lane['type']

    elif path['trafficType'] == 1:
        result[0]['type'] = '지하철'
        result[0]['distance'] = path['distance']
        result[0]['duration'] = path['sectionTime']
        result[0]['start_name'] = path['startName']
        result[0]['end_name'] = path['endName']
        result[0]['way_code'] = path['wayCode']

        time_per_station = datetime.timedelta(minutes=path['sectionTime']) / (len(path['passStopList']['stations'])-1)

        result[0]['stations'] = [{'station_id': station['stationID'],
                                  'station_name': station['stationName'],
                                  'start_time': predicted_time + time_per_station * i,
                                  'ongoing_time': time_per_station * i}
                                 for i, station in enumerate(path['passStopList']['stations'])]

        predicted_time += datetime.timedelta(minutes=path['sectionTime'])

        for i in range(len(path['lane'])-1):
            result.append(result[0].copy())

        for i, lane in enumerate(path['lane']):
            result[i]['subway_id'] = lane['subwayCode']

    else:
        raise ValueError()

    return result, predicted_time


def check_risk_score_per_route(route):
    def find_consecutives(values, ongoing_times, consecutive_seconds, thresholds):
        score = 0
        i = 0
        threshold_keys = sorted(thresholds.keys(), reverse=True)

        while(i < len(values)):
            idx_end = np.argmax((ongoing_times - ongoing_times[i]) > consecutive_seconds)
            if idx_end == 0:
                break
            min_value = min(values[i:idx_end+1])

            for key in threshold_keys:
                if min_value > key:
                    score += thresholds[key]
                    i = idx_end-1
                    break
            i += 1
        return score

    score = 0

    for path in route['path_list']:
        if path['type'] == '도보':
            continue

        ongoing_times = np.array([station['ongoing_time'].seconds for station in path['stations']])

        try:
            # 10분 연속 혼잡도가 >0.5 면 +1, >0.75 면 +2, >1.0 이면 +3
            congestions = np.array([station['predicted_congestion'] for station in path['stations']])
        except KeyError():
            print(path['stations'])
        score += find_consecutives(congestions, ongoing_times, 600, {0.25:0.5, 0.5:1, 0.75:2, 1.0:3})

        # 10분 연속 감염 위험도가 >10 면 +1, >15 면 +2
        congestions = np.array([station['predicted_risk'] for station in path['stations']])

        score += find_consecutives(congestions, ongoing_times, 600, {0.5:1, 0.75:2, 1.0:3})

        # 15분 연속 타고 있을 때마다 score + 1
        score += find_consecutives(ongoing_times, ongoing_times, 900, {15*60:1})

    return score


def draw_bar_graph(fig, num_rows, i, congestions, station_names, station_types, time, mean_risk, risk_score):
    ax = plt.subplot(num_rows, 1, i+1)

    bar_colors = [
        '#00A2FF' if congestion < 0.25 else
        '#1DB100' if congestion < 0.50 else
        '#FFD932' if congestion < 0.75 else
        '#F27200' if congestion < 1.0 else
        '#EE220C'
        for congestion in congestions
    ]

    # 7글자까지는 그대로 표시, 그 이상은 4글자..2글자로 표기하기 위함
    short_station_names = [name if len(name) < 8 else '%s..%s' % (name[:4], name[-2:]) for name in station_names]

    plt.bar(x=np.arange(len(congestions)), height=congestions, color=bar_colors)
    plt.xticks(np.arange(len(congestions)), short_station_names,
               rotation=-45, ha='left', fontsize=14, color='#5A6773')
    plt.yticks([0, 0.25, 0.5, 0.75, 1.0], fontsize=14)

    for spine in plt.gca().spines.values():
        spine.set_visible(False)

    # X label 에서 "도보"를 색으로 표시
    for ticklabel, s_type in zip(plt.gca().get_xticklabels(), station_types):
        if s_type == (0, 0):
            ticklabel.set_color('#009999')

    # 환승 타이밍 / 탑승한 경로 표시
    for i, typ in enumerate(station_types):
        if len(typ) == 3:
            plt.text(i-0.6, 1.0, typ[2], fontsize=14)
            plt.plot((i-0.5, i-0.5), (0, 0.95), '--', color='#666666', linewidth=0.5)

    # 추가 정보
    plt.text(len(congestions), -0.15, '총 시간: %d분' % (time), fontsize=14)
    plt.text(len(congestions), 0, '감염지수: %.1f' % (mean_risk), fontsize=14)
    #plt.text(len(congestions), 0.15, '점수: %.1f' % (risk_score), fontsize=14)

    # mask icon
    if risk_score <= 3.1:
        im = mask_imgs['safe']
    elif risk_score <= 6.1:
        im = mask_imgs['normal']
    elif risk_score <= 9.1:
        im = mask_imgs['unsafe']
    else:
        im = mask_imgs['risky']

    imagebox = OffsetImage(im, zoom=0.2)
    ab = AnnotationBbox(imagebox, xy=(1.05, 0.5), xycoords="axes fraction", frameon=False)
    ax.add_artist(ab)

    # 경로별 15분 넘는 정류장 표시
    for i, typ in enumerate(station_types):
        if typ == (0, 0):
            continue

        if typ[1] > 15:
            plt.plot((i-0.35, i+0.35), (-0.04, -0.04), color='#FF968D', linewidth=5.0)
        else:
            plt.plot((i-0.35, i+0.35), (-0.04, -0.04), color='#EAE4E0', linewidth=5.0)

    plt.ylim((-0.1, 1.0))
