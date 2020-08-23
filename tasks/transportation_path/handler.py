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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from folium.features import DivIcon

# local modules
from .config import odsay_api_key, seoul_api_key


seoul_api_url = 'http://ws.bus.go.kr/api/rest/pathinfo'
odsay_api_url = 'https://api.odsay.com/v1/api/'

BUS_SPEED_MEAN = 18.7 * 1000  # 미터 https://www.index.go.kr/potal/stts/idxMain/selectPoSttsIdxSearch.do?idx_cd=4081&stts_cd=408102

getout_bus_prob_m_df = None
subway_congestion_dict = None
subway_risk_dict = None
bus_risk_dict = None


def init_handler(data_dir='tasks/transportation_path/dataset/'):
    global getout_bus_prob_m_df, subway_congestion_dict, subway_risk_dict, bus_risk_dict

    if not getout_bus_prob_m_df:
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

    return route_list


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
