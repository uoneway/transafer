# TranSafer

New normal 시대를 맞이하여 *안정성*이라는 새로운 대중교통 경로 선택 기준을 제공하고자 시작한 프로젝트로,  
출발지와 목적지를 입력하면 위험지수 및 혼잡도를 고려한 대중교통 추천 경로를 안내해주는 챗봇입니다.
![transafer_eg](https://drive.google.com/uc?id=1tS-FDkgEp3Vypa4tTBMOMMLEyqs_oBN9)

[TranSafer 프로젝트 세부 설명 자료](https://www.slideshare.net/hangilkim75/transafer-entrophy) 

## 구현

- 위험지수 도출 알고리즘
    1. 사용자 선택 경로를 기준으로 대중교통 경로 및 현 상태 정보 도출
    2. 교통수단(버스/지하철)별 / 역별 / 시간대별 예상 혼잡도 산출
    3. 혼잡도 기반 위험지수 산출
        - 감염병 시뮬레이션 모델인 extended SEIRS model에 교통수단별 내부 공간정보를 반영하기 위해 network model을 접목하여 감염병 시뮬레이션 모델 구축
- 사용 API 및 데이터
    - 서울 열린데이터 광장
        - [서울시 버스노선별 정류장별 시간대별 승하차 인원 정보](http://data.seoul.go.kr/dataList/OA-12913/S/1/datasetView.do)
        - [서울시 버스노선별 정류장별 승하차 인원 정보](http://data.seoul.go.kr/dataList/OA-12912/S/1/datasetView.do)
        - [서울시 대중교통 환승 출발지 목적지 검색 정보](http://data.seoul.go.kr/dataList/OA-15349/L/1/datasetView.do)
    - [ODsey 경로검색 API](https://lab.odsay.com/introduce/intro)
- 개발 환경
    - Flask

## 기타 관련 정보

- 개발 참여자: @uoneway, @yerachoi, @eyshin05
- 추가 코드 repository
    - [버스와 지하철 승객 네트워크 생성, 혼잡도 기반 위험도 측정 코드](https://github.com/yerachoi/2020ICTcoc/tree/master/notebooks)
- 2020 ICT coc AI 공모전 수상작
    - [공모전 개요](http://ictcoc.kr/01_ict/ict06_view.asp?idx=262)
    - 공모전 기간: 2020.08.15 ~ 2020.08.23
