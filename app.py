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
    print("------------------------------------- 메인페이지로 이동 -------------------------------------")
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    print(f"현재 로그인한 사용자 아이디: {user_id}")
    # 인천광역시(searchHopeArea1=6280000) 연수구(searchHopeArea2=3520000) 선택 / cPage는 페이지 관련 데이터 (ex: cPage=2는 2페이지)
    url = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?searchHopeArea1=6280000&searchHopeArea2=3520000&cPage=1"
    data = requests.get(url)
    soup = BeautifulSoup(data.text, 'html.parser')

    # 봉사활동 리스트 개수
    page_count = int(soup.select_one("#content > div.content_view > div.search_form > div > p > em:nth-child(1)").text)
    # 페이지 개수(한 페이지 당 10개 출력 시)
    page_count = math.ceil(page_count / 10)

    # 각 페이지에서 가져온 데이터가 담긴 리스트를 담는 용도
    lis_temp_list = []
    for i in range(1, page_count + 1):
        # 인천광역시(searchHopeArea1=6280000) 연수구(searchHopeArea2=3520000) 선택 / cPage는 페이지 관련 데이터 (ex: cPage=2는 2페이지)
        url = "https://www.1365.go.kr/vols/1572247904127/partcptn/timeCptn.do?searchHopeArea1=6280000&searchHopeArea2=3520000&cPage="

        data = requests.get(url + str(i))
        soup = BeautifulSoup(data.text, 'html.parser')

        # 현재 페이지에 있는 봉사활동 리스트 모두 가져오기
        li_tag = "#content > div.content_view > div.board_list.board_list2.non_sub > ul > li"
        lis = soup.select(li_tag)  # lis: li 태그들
        lis_temp_list.append(lis)

    # 2차원 리스트를 1차원 리스트로 바꾸기
    lis_list = sum(lis_temp_list, [])

    # 크롤링 속도 개선: CPU 20개가 일을 나눠가져서 크롤링해옴
    # get_crawling_data 함수에서 봉사 데이터들이 정렬되서 나옴
    with ThreadPoolExecutor(20) as executor:
        executor.map(get_crawling_data, lis_list)

    ''' 시작) 마이페이지에서 메인페이지로 이동할 때 크롤링 결과가 중복되는 현상 해결 '''
    # 중복된 데이터를 제거: 최종 페이지에 전달할 리스트
    remove_duplicated_volunteers_list = list({volunteer["volunteer_no"]: volunteer for volunteer in volunteers_list}.values())
    ''' 끝) 마이페이지에서 메인페이지로 이동할 때 크롤링 결과가 중복되는 현상 해결 '''


    # DB에 저장되어있는 데이터 중에서 volunteer_no만 가져오기
    volunteer_no_list_in_db = list(db.volunteer.find({'user_id': user_id}, {'_id': False, "volunteer_no": True}))

    print("사이트에서 가져온 데이터: ")
    print(remove_duplicated_volunteers_list)
    print(f"사이트에서 가져온 데이터 개수: {len(remove_duplicated_volunteers_list)}")
    print("DB에 저장되어있는 데이터 중 봉사번호만 출력: ")
    print(volunteer_no_list_in_db)
    # 딕셔너리 여러개가 담겨있는 리스트를 키값을 제외한 volunteer_no 값만 가져와 리스트로 변환하기
    global only_volunteer_no_list_crawling
    only_volunteer_no_list_crawling = get_volunteer_no_list(remove_duplicated_volunteers_list)
    only_volunteer_no_list_in_db = get_volunteer_no_list(volunteer_no_list_in_db)

    # 조회해온 리스트 중에서 좋아요를 누른 volunteer_no 값이 담겨있는 리스트
    like_in_mainpage_list = list(set(only_volunteer_no_list_crawling).intersection(only_volunteer_no_list_in_db))
    print("메인페이지에 있는 리스트 중에서 좋아요가 눌려있는 봉사번호: ")
    print(like_in_mainpage_list)

    return render_template('mainpage.html', user_id=user_id, volunteers=remove_duplicated_volunteers_list,
                                                                                            nos=like_in_mainpage_list)


# 사이트에서 데이터 크롤링해오기
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

    # 마감일로부터 남은 기간
    before_deadline = li.select_one("a > div.close_dDay > div > span").text
    print("before_deadline: ")
    print(before_deadline)

    # 상세페이지에서 봉사시간 가져오기
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
    volunteers_list.append(volunteer_dict)
    volunteers_list = sorted(volunteers_list, key=(lambda x: int(x['before_deadline'])))

    # 마감일이 임박한 순으로 정렬
    volunteers_list = sorted(volunteers_list, key=(lambda x: int(x['before_deadline'])))


# 딕셔너리 여러개가 담겨있는 리스트를 키값을 제외한 volunteer_no 값만 가져와 리스트로 변환하는 함수
def get_volunteer_no_list(list):
    no_list = []
    for dict in list:
        no_list.append(dict['volunteer_no'])
    return no_list


# 토큰에서 사용자 아이디값을 가져오는 함수
def get_user_id():
    try:
        token_receive = request.cookies.get('mytoken')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_id = payload["id"]
    # 토큰이 없어서 에러가 날 때 실행
    except(jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        user_id = ""
    return user_id


# 좋아요 누르기
@app.route('/mainpage/like', methods=['POST'])
def like():
    #################################
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()
    print("user_id: ")
    print(user_id)
    #################################
    volunteer_no = request.form["volunteer_no"]
    subject = request.form["subject"]
    recruit_period = request.form["recruit_period"]
    hour = request.form["hour"]
    href = request.form["href"]
    doc = {
        "volunteer_no": volunteer_no,
        "subject": subject,
        "recruit_period": recruit_period,
        "hour": hour,
        "href": href,
        "completion": 'false',
        #################################
        "user_id": user_id
        #################################
    }
    db.volunteer.insert_one(doc)
    return jsonify({'msg': "좋아요를 눌렀습니다!"})


# 좋아요 취소
@app.route('/mainpage/cancel', methods=['POST'])
def cancel_like():
    volunteer_no = request.form["volunteer_no"]
    db.volunteer.delete_one({'volunteer_no': volunteer_no})
    return jsonify({'msg': "좋아요를 취소했습니다!"})


####################### 마이페이지 #######################

@app.route('/mypage')
def mypage():
    #######################################################################
    print("------------------------------------- 마이페이지로 이동 -------------------------------------")
    # 현재 로그인한 사용자 아이디
    user_id = get_user_id()

    # DB에서 현재 사용자가 좋아요 누른 봉사 정보 가져오기
    rows = list(db.volunteer.find({'user_id': user_id}, {'_id': False}))

    # DB에서 가져온 데이터 중 봉사번호만 저장
    only_volunteer_no_list_in_db_mypage = get_volunteer_no_list(rows)

    # DB에는 있지만 1365페이지에 없는 봉사번호 추출(마감되서 글을 내린 경우 DB에서 삭제)
    # DB에서 삭제해야할 봉사번호
    must_be_delete_volunteer_no_in_db = []
    for volunteer_no in only_volunteer_no_list_in_db_mypage:
        global only_volunteer_no_list_crawling
        if volunteer_no not in only_volunteer_no_list_crawling:
            must_be_delete_volunteer_no_in_db.append(volunteer_no)
    print("DB에는 있지만 1365페이지에 없는 봉사번호: ")
    print(must_be_delete_volunteer_no_in_db)

    # 크롤링해온 데이터가 없으면
    if len(only_volunteer_no_list_crawling) <= 0:
        print("크롤링해온 데이터가 없음! 메인페이지를 꼭 거쳐와야함!!")
    else:
        # DB에는 있지만 1365페이지에 없는 봉사번호를 가지고 데이터 삭제
        if len(must_be_delete_volunteer_no_in_db) <= 0:
            print("DB에는 있지만 1365페이지에 없는 봉사번호 없음! 삭제 안해도 됨!")
        else:
            print("DB에는 있지만 1365페이지에 없는 봉사번호 삭제 시작!")
            for v_no in must_be_delete_volunteer_no_in_db:
                db.volunteer.delete_many({'volunteer_no': v_no})
                print(f"{v_no} 봉사 정보 삭제")
            print("DB에는 있지만 1365페이지에 없는 봉사번호 삭제 끝!")
            # 삭제 후 다시 가져오기
            rows = list(db.volunteer.find({'user_id': user_id}, {'_id': False}))
    #######################################################################
    hour = 0
    min = 0
    for row in rows:
        day = row['recruit_period'].split()[2].split('-')
        recruit_day = datetime(int(day[0]), int(day[1]), int(day[2]))
        deadline = datetime.now() - recruit_day
        row['deadline'] = -(int(str(deadline).split(':')[0].split()[0]))
        if row['completion'] == 'true':
            hour += int(row['hour'].split(':')[0])
            min += int(row['hour'].split(':')[1])
    mintohour = min // 60
    hour += mintohour
    min = min % 60

    rows = sorted(rows, key=(lambda x: x['deadline']))
    return render_template('mypage.html', rows=rows, hour=hour, min=min)


@app.route('/mypage', methods=['GET'])
def data_get():
    volunteer = list(db.volunteer.find({}, {'_id': False}))
    return jsonify({'volunteers': volunteer})


@app.route('/mypage/delete', methods=['POST'])
def delete_post():
    id_receive = request.form['id_give']
    db.volunteer.delete_one({'volunteer_no': id_receive})
    return jsonify({'msg': '봉사활동 삭제됨!'})


@app.route('/mypage/done', methods=['POST'])
def done_post():
    id_receive = request.form['id_give']
    db.volunteer.update_one({'volunteer_no': id_receive}, {'$set': {'completion': 'true'}})
    return jsonify({'msg': '봉사활동 완료됨!'})


# [회원가입 API]
# id, pw, 받아서, mongoDB에 저장합니다.
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    # 받은 PW 를 암호화
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
    }
    db.login_info.insert_one(doc)
    return jsonify({'result': 'success'})


# [아이디 중복확인 API]
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.login_info.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# [로그인 API]
@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.login_info.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})
    return jsonify({'result': 'success', 'msg': '연결됨.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
