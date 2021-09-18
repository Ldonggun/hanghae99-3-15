import json
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import math
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import jwt
import hashlib
# MongoDB에 insert 하기
from pymongo import MongoClient  # pymongo를 임포트 하기
# 정렬
from operator import itemgetter

client = MongoClient('localhost', 27017)  # mongoDB는 27017 포트로 돌아갑니다.
db = client.dbweek1  # 'dbweek1'라는 이름의 db를 만듭니다.

# JWT 토큰을 만들 때 필요한 비밀문자열입니다. 아무거나 입력해도 괜찮습니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'hh99-15'

# flask 시작!
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

####################### 메인페이지 #######################

# 크롤링해온 데이터로 만든 딕셔너리를 담는 용도
# ex: [{"volunteer_no": 1234567, "subject":"아이들 가르칠 선생님 구합니다"}, {}, ...]
# 전역변수
volunteers_list = []
# 마이페이지에서 마감된 봉사카드를 지우기 위해 크롤링한 봉사번호를 전달하는 용도
# 전역변수
only_volunteer_no_list_crawling = []



@app.route('/')
def main():
    return render_template("login.html")


@app.route('/mainpage')
def home():
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    print(f"현재 로그인한 사용자 아이디: {user_id}")
    # 인천광역시(searchHopeArea1=6280000) 연수구(searchHopeArea2=3520000) 선택 / 1페이지 선택(cPage=1)
    url = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?searchHopeArea1=6280000&searchHopeArea2=3520000&cPage=1"
    data = requests.get(url)
    soup = BeautifulSoup(data.text, 'html.parser')

    # 봉사활동 정보 개수
    page_count = int(soup.select_one("#content > div.content_view > div.search_form > div > p > em:nth-child(1)").text)
    # 페이지 개수(크롤링한 페이지에서 한 페이지 당 10개씩 출력중)
    page_count = math.ceil(page_count / 10)

    # 페이지에서 가져온 데이터가 담긴 리스트를 담는 용도
    lis_temp_list = []
    for i in range(1, page_count + 1):
        # 인천광역시(searchHopeArea1=6280000) 연수구(searchHopeArea2=3520000) 선택 / 1페이지 선택(cPage=1)
        url = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?searchHopeArea1=6280000&searchHopeArea2=3520000&cPage="

        # str(i) : 페이지를 하나하나 넘겨줘야함(cPage=1, cPage=2, ...)
        data = requests.get(url + str(i))
        soup = BeautifulSoup(data.text, 'html.parser')

        # 현재 페이지에 있는 봉사활동 리스트 모두 가져오기
        li_tag = "#content > div.content_view > div.board_list.board_list2.non_sub > ul > li"
        lis = soup.select(li_tag)  # lis: li 태그들
        lis_temp_list.append(lis)

    # 2차원 리스트를 1차원 리스트로 바꾸기
    lis_list = sum(lis_temp_list, [])

    # 크롤링 속도 개선: 20명이 일을 나눠가져서 크롤링해옴
    # get_crawling_data 함수에서 봉사 데이터들이 정렬되서 나옴!
    with ThreadPoolExecutor(20) as executor:
        executor.map(get_crawling_data, lis_list)

    ''' 시작) 마이페이지에서 메인페이지로 이동할 때 크롤링 결과가 중복되는 현상 해결 '''
    # 중복된 데이터를 제거: 최종 페이지에 전달할 리스트
    remove_duplicated_volunteers_list = list({volunteer["volunteer_no"]: volunteer for volunteer in volunteers_list}.values())
    ''' 끝) 마이페이지에서 메인페이지로 이동할 때 크롤링 결과가 중복되는 현상 해결 '''


    # DB에 저장되어있는 데이터 중에서 volunteer_no만 가져오기
    volunteer_no_list_in_db = list(db.volunteer.find({'user_id': user_id}, {'_id': False, "volunteer_no": True}))

    print(f"사이트에서 가져온 데이터 개수: {len(remove_duplicated_volunteers_list)}")
    # 딕셔너리 여러개가 담겨있는 리스트를 키값을 제외한 volunteer_no 값만 가져와 리스트로 변환하기
    global only_volunteer_no_list_crawling
    only_volunteer_no_list_crawling = get_volunteer_no_list(remove_duplicated_volunteers_list)
    only_volunteer_no_list_in_db = get_volunteer_no_list(volunteer_no_list_in_db)

    # 조회해온 리스트 중에서 좋아요를 누른 volunteer_no 값이 담겨있는 리스트
    like_in_mainpage_list = list(set(only_volunteer_no_list_crawling).intersection(only_volunteer_no_list_in_db))

    return render_template('mainpage.html', user_id=user_id, volunteers=remove_duplicated_volunteers_list,
                                                                                            nos=like_in_mainpage_list)


# 사이트에서 데이터를 크롤링해오는 함수
def get_crawling_data(li):
    # 봉사번호
    volunteer_no = li.select("li > input")[0]["value"]
    # 상세 내용 페이지
    href = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?type=show&progrmRegistNo=" + volunteer_no
    # 제목
    subject = li.select_one("a > dl > dt").text.strip()

    # 모집기간 값을 가져와서 앞 뒤 공백 제거
    recruit_period = li.select_one("a > dl > dd > dl:nth-child(2) > dd").text.strip()
    # 값 사이의 공백을 모두 제거한 뒤 리스트(ex: [시작일,마감일])로 만들기
    recruit_period_list = recruit_period.replace("\r\n", "").replace("\t", "").replace(" ", "").split("~")
    # 모집기간(ex: 시작일 ~ 마감일)
    recruit_period = recruit_period_list[0] + " ~ " + recruit_period_list[1]

    # 마감일로부터 남은 날
    before_deadline = li.select_one("a > div.close_dDay > div > span").text

    # 상세페이지에서 봉사시간 가져오기
    # href: 상세페이지 링크
    data1 = requests.get(href)
    soup1 = BeautifulSoup(data1.text, 'html.parser')
    # 1365 페이지에 있는 봉사시간 태그
    time_tag = "#content > div.content_view > div > div.board_view.type2 > div.board_data.type2 > div:nth-child(1) > dl:nth-child(2) > dd"
    # 태그에 있는 값을 가져와 "~" 기준으로 값을 자른 뒤 리스트로 만들기(ex: [0시0분, 0시0분])
    time = soup1.select_one(time_tag).text.replace(" ", "").split("~")
    # 봉사 시작 시간
    start_time = dt.datetime.strptime(time[0], "%H시%M분")
    # 봉사 끝나는 시간
    end_time = dt.datetime.strptime(time[1], "%H시%M분")
    # 봉사시간
    hour = str(end_time - start_time)

    # 지금까지 크롤링해온 데이터를 딕셔너리로 만들기
    volunteer_dict = {"volunteer_no": volunteer_no, "href": href, "subject": subject, "hour": hour,
                      "recruit_period": recruit_period, "before_deadline": before_deadline, "completion": "false"}
    global volunteers_list  # 전역변수로 사용
    # 리스트에 데이터가 담긴 딕셔너리를 저장
    volunteers_list.append(volunteer_dict)

    # 마감일이 임박한 순으로 정렬
    volunteers_list = sorted(volunteers_list, key=(lambda x: int(x['before_deadline'])))


# 딕셔너리 여러개가 담겨있는 리스트에서 키값을 제외한 volunteer_no 값만 가져와 리스트로 변환하는 함수
def get_volunteer_no_list(list):
    no_list = []
    # 리스트에 담겨있는 딕셔너리 하나하나 꺼내욤
    for dict in list:
        # 딕셔너리에 담겨있는 volunteer_no의 value만 꺼내와 리스트에 담음
        no_list.append(dict['volunteer_no'])
    return no_list


# 토큰에서 사용자 아이디값을 가져오는 함수
def get_user_id():
    try:
        # mytoken이라고 저장한 쿠키를 가져옴
        token_receive = request.cookies.get('mytoken')
        # 암호화되어있는 토큰을 복호화
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 복호화한 데이터에서 id값을 가져옴
        user_id = payload["id"]
    # 토큰이 없어서 에러가 날 때 실행
    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        # 토큰이 없을 경우 "" 을 변수에 저장
        user_id = ""
    return user_id

# 좋아요 누르기
@app.route('/mainpage/like', methods=['POST'])
def like():
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    print("user_id: ")
    print(user_id)
    # 봉사번호
    volunteer_no = request.form["volunteer_no"]
    # 제목
    subject = request.form["subject"]
    # 모집기간
    recruit_period = request.form["recruit_period"]
    # 봉사시간
    hour = request.form["hour"]
    # 상세페이지 링크
    href = request.form["href"]
    # DB에 insert할 데이터
    doc = {
        "volunteer_no": volunteer_no,
        "subject": subject,
        "recruit_period": recruit_period,
        "hour": hour,
        "href": href,
        "completion": 'false',
        "user_id": user_id
    }
    # DB에 insert
    db.volunteer.insert_one(doc)
    return jsonify({'msg': "좋아요를 눌렀습니다!"})


# 좋아요 취소
@app.route('/mainpage/cancel', methods=['POST'])
def cancel_like():
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    print("user_id: ")
    print(user_id)
    # 봉사번호
    volunteer_no = request.form["volunteer_no"]
    # 봉사번호를 가진 데이터를 DB에서 삭제
    db.volunteer.delete_one({'volunteer_no': volunteer_no, 'user_id': user_id})
    return jsonify({'msg': "좋아요를 취소했습니다!"})

####################### 마이페이지 #######################

@app.route('/mypage')
def mypage():
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()

    # DB에서 현재 사용자가 좋아요 누른 봉사 정보 가져오기
    rows = list(db.volunteer.find({'user_id': user_id}, {'_id': False}))

    # DB에서 가져온 데이터 중 봉사번호만 저장
    only_volunteer_no_list_in_db_mypage = get_volunteer_no_list(rows)

    # DB에는 있지만 1365페이지에 없는 봉사번호 추출(마감되서 글을 내린 경우 DB에서 삭제)
    # DB에서 삭제해야할 봉사번호
    must_be_delete_volunteer_no_in_db = []
    # DB에서 가져온 volunteer_no가 담겨있는 리스트에서 봉사번호를 하나하나 꺼냄
    for volunteer_no in only_volunteer_no_list_in_db_mypage:
        global only_volunteer_no_list_crawling  # 전역변수로 사용
        # 만약 크롤링해온 봉사번호 리스트에서 DB에서 가져온 봉사번호가 들어있지 않으면
        if volunteer_no not in only_volunteer_no_list_crawling:
            # DB에서 삭제해야 할 리스트에 추가
            must_be_delete_volunteer_no_in_db.append(volunteer_no)

    # 크롤링해온 데이터가 없으면
    if len(only_volunteer_no_list_crawling) <= 0:
        print("크롤링해온 데이터가 없음! 메인페이지를 꼭 거쳐와야함!!")
    else:
        # DB에는 있지만 1365페이지에 없는 봉사번호를 가지고 데이터 삭제
        if len(must_be_delete_volunteer_no_in_db) <= 0:
            print("DB에는 있지만 1365페이지에 없는 봉사번호 없음! 삭제 안해도 됨!")
        else:
            print("DB에는 있지만 1365페이지에 없는 봉사번호 삭제 시작!")
            # DB에서 삭제해야할 봉사번호를 가지고 있는 리스트에서 봉사번호를 하나하나 꺼내옴
            for v_no in must_be_delete_volunteer_no_in_db:
                # DB에서 데이터 삭제
                db.volunteer.delete_many({'volunteer_no': v_no, 'user_id': user_id})
                print(f"{v_no} 봉사 정보 삭제")
            print("DB에는 있지만 1365페이지에 없는 봉사번호 삭제 끝!")
            # 삭제 후 데이터를 다시 가져오기
            rows = list(db.volunteer.find({'user_id': user_id}, {'_id': False}))
        # 마감일이 오늘인 봉사활동들을 담는 리스트
        deadlines = []
        # 총 봉사 시간의 '시간'
        hour = 0
        # 총 봉사 시간의 '분'
        min = 0
        for row in rows:
            # 모집기간의 마지막날을 추출하고 마감일을 '년', '월', '일'로 나눔
            day = row['recruit_period'].split()[2].split('-')
            # 모집기간을 현재 날짜에서 계산하기 위해서 datetime함수를 사용해서 날짜형태로 변경
            recruit_day = datetime(int(day[0]), int(day[1]), int(day[2]))
            # 현재 날짜에서 모집기간을 빼서 마감일을 구함
            deadline = recruit_day - datetime.now()

            # 마감일이 오늘이면 deadline 변수에 'days'문자열이 포함이 되지 않기 때문에
            # 포함되어 있는지 확인하고
            # 마감일이 오늘인 봉사활동들을 따로 dealines 리스트에 추가
            if str(deadline).find('days', 0) == -1:
                row['deadline'] = 0
                deadlines.append(row['volunteer_no'])
            else:
                # 마감일이 오늘이 아닌 봉사활동일 경우
                # 마감일로 부터 남은 날을 row['deadline']에 저장
                row['deadline'] = int(str(deadline).split(':')[0].split()[0])

            # 시간문자열은 ':' 기준으로 짤은 것 중에서 시간 데이터를 저장
            row_hour = row['hour'].split(':')[0]
            # 시간문자열은 ':' 기준으로 짤은 것 중에서 분 데이터를 저장
            row_min = row['hour'].split(':')[1]
            # 완료된 봉사정보일 경우 총 시간을 계산
            if row['completion'] == 'true':
                hour += int(row_hour)
                min += int(row_min)
            # 시간문자열을 ':' 기준으로 짤은 것 중에서
            # 분 데이터가 문자열 '00'일 경우
            if row_min == '00':
                # '시간' 문자열을 붙여서 저장
                row['hour'] = row_hour + '시간'
            else:
                # '시간' 문자열과 '분' 문자열을 붙여서 저장
                row['hour'] = row_hour + '시간 ' + row_min + '분'

        # 총 시간과 분 계산
        mintohour = min // 60
        hour += mintohour
        min = min % 60

        # 마감일로 부터 남은 날 기준으로 봉사정보를 정렬
        rows = sorted(rows, key=(lambda x: x['deadline']))
        return render_template('mypage.html', rows=rows, hour=hour, min=min, deadlines=deadlines)


@app.route('/mypage', methods=['GET'])
def data_get():
    # 계정에 따른 좋아요를 누른 봉사정보를 DB에서 가져옴
    volunteer = list(db.volunteer.find({}, {'_id': False}))
    return jsonify({'volunteers': volunteer})


@app.route('/mypage/delete', methods=['POST'])
def delete_post():
    # 마이페이지에서 가져온 봉사번호
    id_receive = request.form['id_give']
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    # 좋아요 취소를 누른 봉사카드를 DB에서 삭제
    db.volunteer.delete_one({'volunteer_no': id_receive, 'user_id':user_id})
    return jsonify({'msg': '봉사활동 삭제됨!'})


@app.route('/mypage/done', methods=['POST'])
def done_post():
    # 마이페이지에서 가져온 봉사번호
    id_receive = request.form['id_give']
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    # 완료하기 버튼을 누른 봉사카드를 화면의 봉사완료 부분으로 이동시키기 위해 completion 데이터를 'true'로 update
    db.volunteer.update_one({'volunteer_no': id_receive, 'user_id':user_id}, {'$set': {'completion': 'true'}})
    return jsonify({'msg': '봉사활동 완료됨!'})


# [회원가입 API]
# id, pw, 받아서, mongoDB에 저장합니다.
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    #클랑이언트로 받은 username, password
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    # 받은 PW 를 암호화
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    # db저장
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
    }
    db.login_info.insert_one(doc)
    return jsonify({'result': 'success'})


# [아이디 중복확인 API]
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    #클라이언트로 받은 username을 db에서 확인 후 메시지 전달
    username_receive = request.form['username_give']
    exists = bool(db.login_info.find_one({"username": username_receive})) # db에 username 이 없다면
    return jsonify({'result': 'success', 'exists': exists})


# [로그인 API]
# url이 sign_in으로 요청받은 post요청 수행
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # username_give, password_give를 각각 받아줌
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    # 받은 password를 hash 함수 값으로 만들어줌
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    # login_info에 저장된 db에서 유저 이름과 password값이 매칭된다면 result값으로 받아줌
    result = db.login_info.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        # 제대로 매칭되었다면 해당 id에 로그인 유지 시간과 함께 jwt토큰을 발행해줌
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        # 받은 token을 secret 키로 암호화
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        # 암호화 한 token을 success값과 함게 json형식으로 클라이언트에 전송
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    return jsonify({'result': 'success', 'msg': '연결됨.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
