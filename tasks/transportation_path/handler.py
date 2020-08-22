# -*- coding:utf-8 -*-
import folium
import json
import requests
import xmltodict
import time

import numpy as np

from folium.features import DivIcon

# local modules
from .config import odsay_api_key, seoul_api_key


seoul_api_url = 'http://ws.bus.go.kr/api/rest/pathinfo'
odsay_api_url = 'https://api.odsay.com/v1/api/'


def get_location_info(desc_location):
    param = {'stSrch': desc_location}
    url = '%s/getLocationInfo?ServiceKey=%s' % (seoul_api_url, seoul_api_key)
    res = requests.get(url, params=param)

    return res


def response_to_dict(res):
    return json.loads(json.dumps(xmltodict.parse(res.text)))


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
        return None

    item_list = res_dict['ServiceResult']['msgBody']['itemList']
    map = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map.save(html_path)

    return html_path, [(item['poiNm'], item['gpsX'], item['gpsY']) for item in item_list]


def ask_destination(output):
    res = get_location_info(output)
    res_dict = response_to_dict(res)

    if res_dict['ServiceResult']['msgHeader']['headerCd'] == '4': # 결과 없음
        return None

    item_list = res_dict['ServiceResult']['msgBody']['itemList']
    map = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map.save(html_path)

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
